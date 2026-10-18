import { createHash } from "node:crypto";
import type pg from "pg";
import {
  assignAnswerKeys,
  contestKey,
  displaySlots,
  isEstimate,
  methodRank,
  normalizeParty,
  officeLabel,
  officeParts,
  PARTY_SEEDS,
  partyColor,
  shortLabel,
  canonicalUnitType,
} from "@usd/core";
import { insertJsonChunks } from "./batch.ts";
import {
  countRejectRules,
  markDuplicates,
  negativeVoteExamples,
  validateRow,
  type RawResult,
  type Reject,
} from "./validate.ts";

export type ApplyMeta = {
  fileName: string;
  sha256: string;
  gitCommit?: string | null;
};

export type ApplyReport = {
  fileName: string;
  status: "skipped" | "applied" | "rejected";
  rows: number;
  rejected: number;
  changed: number;
  rejects: Reject[];
  /** Every rule on this file, not only the first one in the sample. */
  rejectRules: Record<string, number>;
  examples: { lineNo: number; detail: string }[];
};

type Fact = {
  contest_key: string;
  office_key: string;
  office_label: string;
  year: number;
  stage: string;
  state_abbr: string;
  boundary_set: string;
  unit_type: string;
  unit_key: string;
  answer_key: string;
  label: string;
  candidate_key: string;
  candidate_name: string;
  short_name: string;
  party_key: string;
  color: string;
  votes: number;
  weight: number;
  is_estimate: boolean;
  method: string;
  is_aggregate: boolean;
  source_id: string;
  source_url: string;
  source_notes: string | null;
  source_record_id: string;
  retrieved_at: string;
};

const HARD_REJECT_RATE = 0.005;

export type ApplyOptions = {
  /** When false, the caller refreshes unit_contest_agg and answer_share once after the batch. */
  refreshAggregates?: boolean;
};

export async function refreshAggregates(db: pg.Pool | pg.PoolClient): Promise<void> {
  await db.query("refresh materialized view unit_contest_agg");
  await db.query("refresh materialized view answer_share");
}

export function sha256Hex(body: Buffer | string): string {
  return createHash("sha256").update(body).digest("hex");
}

export function splitSource(raw: string): { url: string; notes: string | null } {
  const trimmed = raw.trim();
  const match = /^(https?:\/\/\S+)\s*([\s\S]*)$/i.exec(trimmed);
  if (!match) return { url: trimmed, notes: null };
  const notes = match[2]?.trim();
  return { url: match[1]!, notes: notes ? notes : null };
}

function sourceId(url: string, retrievedAt: string): string {
  let host = "src";
  try {
    host = new URL(url).hostname.replace(/^www\./, "").split(".")[0] || "src";
  } catch {
    host = "src";
  }
  const slug = host.toLowerCase().replace(/[^a-z0-9]+/g, "").slice(0, 24) || "src";
  const sha = createHash("sha256").update(`${url}|${retrievedAt}`).digest("hex").slice(0, 8);
  return `${slug}-${sha}`;
}

async function unitIndex(client: pg.PoolClient): Promise<Set<string>> {
  const r = await client.query<{ slug: string; unit_type: string; unit_key: string }>(
    `select b.slug, u.unit_type, u.unit_key
     from unit u join boundary_set b on b.id = u.boundary_set_id`,
  );
  const set = new Set<string>();
  for (const row of r.rows) set.add(`${row.slug}|${row.unit_type}|${row.unit_key}`);
  return set;
}

function toFacts(rows: RawResult[]): { facts: Fact[]; rejects: Reject[] } {
  const keyedGroups = new Map<string, RawResult[]>();
  for (const row of rows) {
    const key = contestKey({ year: row.year, office: row.office, state: row.state, district: row.district });
    const list = keyedGroups.get(key);
    if (list) list.push(row);
    else keyedGroups.set(key, [row]);
  }
  const facts: Fact[] = [];
  const rejects: Reject[] = [];
  for (const [key, group] of keyedGroups) {
    const assigned = assignAnswerKeys(group.map((row) => ({ ...row, candidateId: row.candidateId, party: row.party })));
    const seen = new Map<string, Fact>();
    for (let i = 0; i < group.length; i++) {
      const row = group[i]!;
      const got = assigned[i]!;
      const parts = officeParts(row.office);
      const src = splitSource(row.sourceUrl);
      const party = normalizeParty(row.party);
      const weight = row.weight.trim() ? Number(row.weight) : 1;
      const method = row.method.trim() || (weight < 1 ? "area_weighted" : "official");
      const fact: Fact = {
        contest_key: key,
        office_key: parts.officeKey,
        office_label: officeLabel(parts.officeKey),
        year: Number(row.year),
        stage: parts.stage,
        state_abbr: parts.officeKey === "president" ? "US" : row.state.trim().toUpperCase(),
        boundary_set: row.boundarySet.trim() || "v2-2024",
        unit_type: canonicalUnitType(row.unitType),
        unit_key: row.unitId.trim(),
        answer_key: got.answerKey,
        label: shortLabel(row.candidateId.trim(), row.answer.trim() || row.candidateId.trim()),
        candidate_key: row.candidateId.trim(),
        candidate_name: row.answer.trim() || row.candidateId.trim(),
        short_name: shortLabel(row.candidateId.trim(), row.answer.trim() || row.candidateId.trim()),
        party_key: party.key,
        color: partyColor(party.key),
        votes: Number(row.votes),
        weight,
        is_estimate: isEstimate(method, weight, row.estimate),
        method,
        is_aggregate: got.aggregate,
        source_id: sourceId(src.url, row.retrievedAt.trim()),
        source_url: src.url,
        source_notes: src.notes,
        source_record_id: String(row.lineNo),
        retrieved_at: new Date(row.retrievedAt.trim()).toISOString(),
      };
      const dedupeKey = `${fact.boundary_set}|${fact.unit_type}|${fact.unit_key}|${fact.answer_key}`;
      const prev = seen.get(dedupeKey);
      if (!prev) {
        seen.set(dedupeKey, fact);
        continue;
      }
      if (prev.candidate_key !== fact.candidate_key) {
        rejects.push({ lineNo: row.lineNo, rule: "R10_answer", detail: dedupeKey });
        continue;
      }
      if (methodRank(fact.method) > methodRank(prev.method) || fact.retrieved_at >= prev.retrieved_at) {
        seen.set(dedupeKey, fact);
      }
    }
    facts.push(...seen.values());
  }
  return { facts, rejects };
}

async function seedParties(client: pg.PoolClient): Promise<void> {
  for (const party of PARTY_SEEDS) {
    await client.query(
      `insert into party (party_key, name, color, aliases)
       values ($1, $2, $3, $4)
       on conflict (party_key) do nothing`,
      [party.key, party.name, party.color, party.aliases],
    );
  }
}

async function writeFacts(client: pg.PoolClient, facts: Fact[], batchId: string): Promise<number> {
  await client.query(
    `create temp table incoming (
      contest_key text, office_key text, office_label text, year int, stage text, state_abbr text,
      boundary_set text, unit_type text, unit_key text, answer_key text, label text,
      candidate_key text, candidate_name text, short_name text, party_key text, color text,
      votes numeric, weight numeric, is_estimate boolean, method text, is_aggregate boolean,
      source_id text, source_url text, source_notes text, source_record_id text, retrieved_at timestamptz
    ) on commit drop`,
  );
  await insertJsonChunks(
    client,
    `insert into incoming
     select * from jsonb_to_recordset($1::jsonb) as x(
       contest_key text, office_key text, office_label text, year int, stage text, state_abbr text,
       boundary_set text, unit_type text, unit_key text, answer_key text, label text,
       candidate_key text, candidate_name text, short_name text, party_key text, color text,
       votes numeric, weight numeric, is_estimate boolean, method text, is_aggregate boolean,
       source_id text, source_url text, source_notes text, source_record_id text, retrieved_at timestamptz
     )`,
    facts,
  );

  await client.query(
    `insert into source (source_id, url, retrieved_at, notes)
     select distinct on (source_id) source_id, source_url, retrieved_at, source_notes
     from incoming order by source_id
     on conflict (source_id) do nothing`,
  );
  await client.query(
    `insert into party (party_key, name, color)
     select distinct on (party_key) party_key, party_key, color
     from incoming order by party_key
     on conflict (party_key) do nothing`,
  );
  await client.query(
    `insert into candidate (candidate_key, full_name, short_name)
     select distinct on (candidate_key) candidate_key, candidate_name, short_name
     from incoming
     order by candidate_key, length(candidate_name) desc
     on conflict (candidate_key) do update
       set full_name = excluded.full_name, short_name = excluded.short_name`,
  );
  await client.query(
    `insert into office (office_key, label)
     select distinct on (office_key) office_key, office_label
     from incoming order by office_key
     on conflict (office_key) do nothing`,
  );
  await client.query(
    `insert into contest (contest_key, office_id, year, stage, kind, state_abbr, is_static)
     select distinct on (i.contest_key) i.contest_key, o.id, i.year, i.stage, 'candidate', i.state_abbr, true
     from incoming i join office o on o.office_key = i.office_key
     order by i.contest_key
     on conflict (contest_key) do update set stage = excluded.stage`,
  );
  await client.query(
    `insert into answer (contest_id, answer_key, label, candidate_id, party_id, color, is_aggregate)
     select distinct on (c.id, i.answer_key) c.id, i.answer_key, i.label, cand.id, p.id, i.color, i.is_aggregate
     from incoming i
     join contest c on c.contest_key = i.contest_key
     join candidate cand on cand.candidate_key = i.candidate_key
     join party p on p.party_key = i.party_key
     order by c.id, i.answer_key
     on conflict (contest_id, answer_key) do update
       set label = excluded.label, candidate_id = excluded.candidate_id,
           party_id = excluded.party_id, color = excluded.color, is_aggregate = excluded.is_aggregate`,
  );

  const archived = await client.query(
    `insert into result_history (contest_id, unit_id, answer_id, votes, weight, source_id, retrieved_at)
     select r.contest_id, r.unit_id, r.answer_id, r.votes, r.weight, r.source_id, r.retrieved_at
     from result r
     join contest c on c.id = r.contest_id
     join unit u on u.id = r.unit_id
     join boundary_set b on b.id = u.boundary_set_id
     join incoming i on i.contest_key = c.contest_key and i.boundary_set = b.slug
       and i.unit_type = u.unit_type and i.unit_key = u.unit_key
     where r.method = 'v2_import'
       and (case i.method when 'official' then 3 when 'v2_import' then 1 else 2 end) > 1`,
  );
  const removed = await client.query(
    `delete from result r
     using contest c, unit u, boundary_set b, incoming i
     where r.contest_id = c.id and r.unit_id = u.id and u.boundary_set_id = b.id
       and i.contest_key = c.contest_key and i.boundary_set = b.slug
       and i.unit_type = u.unit_type and i.unit_key = u.unit_key
       and r.method = 'v2_import'
       and (case i.method when 'official' then 3 when 'v2_import' then 1 else 2 end) > 1`,
  );

  await client.query(
    `insert into result_history (contest_id, unit_id, answer_id, votes, weight, source_id, retrieved_at)
     select r.contest_id, r.unit_id, r.answer_id, r.votes, r.weight, r.source_id, r.retrieved_at
     from result r
     join contest c on c.id = r.contest_id
     join unit u on u.id = r.unit_id
     join boundary_set b on b.id = u.boundary_set_id
     join answer a on a.id = r.answer_id
     join incoming i on i.contest_key = c.contest_key and i.boundary_set = b.slug
       and i.unit_type = u.unit_type and i.unit_key = u.unit_key and i.answer_key = a.answer_key
     where (
       (case i.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
         > (case r.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
       or (
         (case i.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
           = (case r.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
         and i.retrieved_at >= r.retrieved_at
       )
     )
     and (r.votes, r.weight, r.source_id, r.method) is distinct from (i.votes, i.weight, i.source_id, i.method)`,
  );

  const upserted = await client.query(
    `insert into result (
       contest_id, unit_id, answer_id, votes, weight, is_estimate, method, source_id, source_record_id,
       retrieved_at, load_batch_id
     )
     select distinct on (c.id, u.id, a.id)
            c.id, u.id, a.id, i.votes, i.weight, i.is_estimate, i.method, i.source_id, i.source_record_id,
            i.retrieved_at, $1::bigint
     from incoming i
     join contest c on c.contest_key = i.contest_key
     join boundary_set b on b.slug = i.boundary_set and b.unit_type = i.unit_type
     join unit u on u.boundary_set_id = b.id and u.unit_key = i.unit_key
     join answer a on a.contest_id = c.id and a.answer_key = i.answer_key
     order by c.id, u.id, a.id, i.votes desc
     on conflict (contest_id, unit_id, answer_id) do update
       set votes = excluded.votes, weight = excluded.weight, is_estimate = excluded.is_estimate,
           method = excluded.method, source_id = excluded.source_id,
           source_record_id = excluded.source_record_id, retrieved_at = excluded.retrieved_at,
           load_batch_id = excluded.load_batch_id, updated_at = now()
       where (
         (case excluded.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
           > (case result.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
         or (
           (case excluded.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
             = (case result.method when 'official' then 3 when 'v2_import' then 1 else 2 end)
           and excluded.retrieved_at >= result.retrieved_at
         )
       )
       and (result.votes, result.weight, result.source_id, result.method)
           is distinct from (excluded.votes, excluded.weight, excluded.source_id, excluded.method)`,
    [batchId],
  );

  await client.query(
    `insert into result_total (contest_id, unit_id, total_votes, is_estimate, source_id)
     select r.contest_id, r.unit_id, sum(r.votes), bool_or(r.is_estimate), min(r.source_id)
     from result r
     where r.contest_id in (select c.id from contest c join incoming i on i.contest_key = c.contest_key)
     group by r.contest_id, r.unit_id
     on conflict (contest_id, unit_id) do update
       set total_votes = excluded.total_votes, is_estimate = excluded.is_estimate, source_id = excluded.source_id`,
  );

  await fillSlots(client);
  const changed = (archived.rowCount ?? 0) + (removed.rowCount ?? 0) + (upserted.rowCount ?? 0);
  return changed;
}

async function fillSlots(client: pg.PoolClient): Promise<void> {
  const contests = await client.query<{ contest_key: string }>(
    `select distinct contest_key from incoming`,
  );
  for (const contest of contests.rows) {
    let rows: { answer_key: string; party: string; votes: string; is_aggregate: boolean }[] = [];
    for (const unitType of ["state", "county", "ushouse"]) {
      const found = await client.query<{ answer_key: string; party: string; votes: string; is_aggregate: boolean }>(
        `select a.answer_key, coalesce(p.party_key, 'oth') as party,
                sum(r.votes)::text as votes, a.is_aggregate
         from result r
         join contest c on c.id = r.contest_id
         join answer a on a.id = r.answer_id
         join unit u on u.id = r.unit_id
         left join party p on p.id = a.party_id
         where c.contest_key = $1 and u.unit_type = $2
         group by a.answer_key, p.party_key, a.is_aggregate`,
        [contest.contest_key, unitType],
      );
      if (found.rows.length > 0) {
        rows = found.rows;
        break;
      }
    }
    const slots = displaySlots(
      rows.map((row) => ({
        answerKey: row.answer_key,
        party: row.party,
        votes: Number(row.votes),
        aggregate: row.is_aggregate,
      })),
    );
    for (const slot of ["d", "r"] as const) {
      const picked = slots[slot];
      if (!picked) continue;
      await client.query(
        `insert into contest_display_slot (contest_id, slot, answer_id, rule)
         select c.id, $2, a.id, $4
         from contest c
         join answer a on a.contest_id = c.id and a.answer_key = $3
         where c.contest_key = $1
         on conflict (contest_id, slot) do update
           set answer_id = excluded.answer_id, rule = excluded.rule`,
        [contest.contest_key, slot, picked.answerKey, picked.rule],
      );
    }
  }
}

/** Older rejected batches of the same file, once a later batch has applied. */
export async function markSuperseded(
  db: pg.Pool | pg.PoolClient,
  fileName: string,
  appliedBatchId: string,
): Promise<number> {
  const updated = await db.query(
    `update load_batch set status = 'superseded'
     where file_name = $1 and id <> $2 and status = 'rejected'`,
    [fileName, appliedBatchId],
  );
  return updated.rowCount ?? 0;
}

export async function applyResults(
  pool: pg.Pool,
  meta: ApplyMeta,
  rows: RawResult[],
  options: ApplyOptions = {},
): Promise<ApplyReport> {
  const existing = await pool.query<{ status: string }>(
    `select status from load_batch where file_sha256 = $1`,
    [meta.sha256],
  );
  // Same bytes are terminal: applied stays applied, rejected stays rejected. A changed file is a new sha.
  if (existing.rows[0]?.status === "applied" || existing.rows[0]?.status === "rejected") {
    return {
      fileName: meta.fileName,
      status: "skipped",
      rows: rows.length,
      rejected: 0,
      changed: 0,
      rejects: [],
      rejectRules: {},
      examples: [],
    };
  }

  const client = await pool.connect();
  try {
    await client.query("begin");
    await seedParties(client);
    const known = await unitIndex(client);
    const rejects: Reject[] = [];
    const survivors: RawResult[] = [];
    for (const row of rows) {
      const bad = validateRow(row);
      if (bad) {
        rejects.push(bad);
        continue;
      }
      const slug = row.boundarySet.trim() || "v2-2024";
      const unitType = canonicalUnitType(row.unitType);
      if (!known.has(`${slug}|${unitType}|${row.unitId.trim()}`)) {
        rejects.push({ lineNo: row.lineNo, rule: "R07_unit", detail: `${slug} ${unitType} ${row.unitId}` });
        continue;
      }
      survivors.push(row);
    }
    rejects.push(...markDuplicates(survivors));
    const dupLines = new Set(rejects.filter((r) => r.rule === "R09_duplicate").map((r) => r.lineNo));
    const clean = survivors.filter((row) => !dupLines.has(row.lineNo));
    const built = toFacts(clean);
    rejects.push(...built.rejects);
    const blocked = new Set(built.rejects.map((r) => r.lineNo));
    const facts = built.facts.filter(() => true);
    void blocked;

    const rate = rows.length === 0 ? 0 : rejects.length / rows.length;
    const batch = await client.query<{ id: string }>(
      `insert into load_batch (file_name, file_sha256, git_commit, row_count, status, report)
       values ($1, $2, $3, $4, 'staged', $5::jsonb)
       on conflict (file_sha256) do update set status = 'staged', report = excluded.report,
         git_commit = coalesce(excluded.git_commit, load_batch.git_commit)
       returning id`,
      [
        meta.fileName,
        meta.sha256,
        meta.gitCommit ?? null,
        rows.length,
        JSON.stringify({ rules: countRejectRules(rejects), rejects: rejects.slice(0, 50) }),
      ],
    );
    const batchId = batch.rows[0]!.id;
    await client.query(`delete from stg_reject where load_batch_id = $1`, [batchId]);
    await client.query(`delete from stg_result_row where load_batch_id = $1`, [batchId]);
    if (rows.length > 0) {
      await insertJsonChunks(
        client,
        `insert into stg_result_row (
           load_batch_id, line_no, state, year, office, district, unit_id, unit_type,
           candidate_id, answer, party, votes, weight, source_url, retrieved_at, method, boundary_set
         )
         select $1, line_no, state, year, office, district, unit_id, unit_type,
                candidate_id, answer, party, votes, weight, source_url, retrieved_at, method, boundary_set
         from jsonb_to_recordset($2::jsonb) as x(
           line_no int, state text, year text, office text, district text, unit_id text, unit_type text,
           candidate_id text, answer text, party text, votes text, weight text, source_url text,
           retrieved_at text, method text, boundary_set text
         )`,
        rows.map((row) => ({
          line_no: row.lineNo,
          state: row.state,
          year: row.year,
          office: row.office,
          district: row.district,
          unit_id: row.unitId,
          unit_type: row.unitType,
          candidate_id: row.candidateId,
          answer: row.answer,
          party: row.party,
          votes: row.votes,
          weight: row.weight,
          source_url: row.sourceUrl,
          retrieved_at: row.retrievedAt,
          method: row.method,
          boundary_set: row.boundarySet,
        })),
        [batchId],
      );
    }
    if (rejects.length > 0) {
      await insertJsonChunks(
        client,
        `insert into stg_reject (load_batch_id, line_no, rule, detail)
         select $1, line_no, rule, detail
         from jsonb_to_recordset($2::jsonb) as x(line_no int, rule text, detail text)
         on conflict do nothing`,
        rejects.map((r) => ({ line_no: r.lineNo, rule: r.rule, detail: r.detail })),
        [batchId],
      );
    }
    const rejectRules = countRejectRules(rejects);
    const examples = negativeVoteExamples(rejects);
    if (rate > HARD_REJECT_RATE) {
      await client.query(
        `update load_batch set status = 'rejected', finished_at = now(), report = $2::jsonb where id = $1`,
        [batchId, JSON.stringify({ rejected: rejects.length, rules: rejectRules, sample: rejects.slice(0, 20) })],
      );
      await client.query(`delete from stg_result_row where load_batch_id = $1`, [batchId]);
      await client.query("commit");
      return {
        fileName: meta.fileName,
        status: "rejected",
        rows: rows.length,
        rejected: rejects.length,
        changed: 0,
        rejects: rejects.slice(0, 20),
        rejectRules,
        examples,
      };
    }

    const changed = facts.length === 0 ? 0 : await writeFacts(client, facts, batchId);
    if (changed > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
      await client.query(
        `update contest set data_version = data_version + 1
         where contest_key in (select distinct contest_key from incoming)`,
      );
      if (options.refreshAggregates !== false) await refreshAggregates(client);
    }
    await client.query(
      `update load_batch set status = 'applied', finished_at = now(), report = $2::jsonb where id = $1`,
      [batchId, JSON.stringify({ rows: rows.length, rejected: rejects.length, rules: rejectRules, changed, facts: facts.length })],
    );
    await markSuperseded(client, meta.fileName, batchId);
    await client.query(`delete from stg_result_row where load_batch_id = $1`, [batchId]);
    await client.query("commit");
    return {
      fileName: meta.fileName,
      status: "applied",
      rows: rows.length,
      rejected: rejects.length,
      changed,
      rejects: rejects.slice(0, 20),
      rejectRules,
      examples,
    };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}
