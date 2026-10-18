import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import type pg from "pg";
import { markSuperseded, sha256Hex } from "./apply.ts";
import { insertJsonChunks } from "./batch.ts";
import { fetchOrigin, needsRefresh, originCommit, stampCommit } from "./branch-cache.ts";
import { BUDGET_BYTES, formatMb, overMeasuredBudget } from "./budget.ts";
import { parseCsv, readFileText } from "./csv.ts";

const WIKIDATA = /^wikidata:Q[0-9]+$/;
const BARE_Q = /^Q[0-9]+$/;
const ROLES = new Set(["seal", "flag", "logo"]);

/**
 * entities.csv `wikidata` at data/inst-entities 1fde48d is already `wikidata:Q…`.
 * entity_images.csv `wikidata_qid` is still a bare `Q…` in that commit. A bare id
 * is prefixed once. A value that already has the prefix is kept as-is.
 */
export function wikidataId(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  if (!text) return null;
  if (WIKIDATA.test(text)) return text;
  if (BARE_Q.test(text)) return `wikidata:${text}`;
  return null;
}

export type InstRelationRow = {
  entity_id: string;
  relation: string;
  related_entity_id: string;
  method?: string;
  source_id?: string;
};

const RELATION_METHODS = new Set(["sourced", "overlay", "point_in_polygon", "manual"]);

export type RelationMethod = "sourced" | "overlay" | "point_in_polygon" | "manual";

/**
 * The file's method is empty, one of the schema values, or a source token such as
 * `tceq_wdd_primary_county`. A token is stored as `sourced`, and the raw text is
 * kept on source_record_id. An empty method stays null.
 */
export function mapRelationMethod(raw: string | undefined): { method: RelationMethod | null; token: string | null } {
  const text = (raw ?? "").trim();
  if (!text) return { method: null, token: null };
  if (RELATION_METHODS.has(text)) return { method: text as RelationMethod, token: null };
  return { method: "sourced", token: text };
}

export type MappedRelation = {
  parent_id: string;
  child_id: string;
  relation: "parent" | "consolidated_with" | "in_county";
  method: RelationMethod | null;
  source_id: string | null;
  source_record_id: string;
};

function firstSource(raw: string | undefined): string | null {
  const id = (raw ?? "").split(";")[0]?.trim() ?? "";
  return id || null;
}

function sourceList(raw: string | undefined): string[] {
  const ids = (raw ?? "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
  return [...new Set(ids)];
}

/**
 * `entity_relations.csv`: `parent` means entity_id is the child and related_entity_id
 * is the parent. That parent is written to `entity.parent_id` and to `entity_relation`.
 * `consolidated_with` keeps entity_id as the parent (the county) and does not set parent_id.
 * `in_county` means entity_id is the special district and related_entity_id is the county.
 * It does not change `entity.parent_id` (the district's parent is still the state).
 */
export function mapInstRelations(rows: InstRelationRow[]): {
  relations: MappedRelation[];
  parents: { entity_id: string; parent_id: string }[];
  skipped: number;
} {
  const relations: MappedRelation[] = [];
  const parents: { entity_id: string; parent_id: string }[] = [];
  let skipped = 0;
  const seenParent = new Set<string>();
  for (const row of rows) {
    const child = row.entity_id.trim();
    const related = row.related_entity_id.trim();
    const relation = row.relation.trim();
    if (!child || !related || child === related) {
      skipped++;
      continue;
    }
    const sourceId = firstSource(row.source_id);
    const mappedMethod = mapRelationMethod(row.method);
    const record = (parentId: string, childId: string, name: MappedRelation["relation"]) => {
      const token = mappedMethod.token ? `|method:${mappedMethod.token}` : "";
      relations.push({
        parent_id: parentId,
        child_id: childId,
        relation: name,
        method: mappedMethod.method,
        source_id: sourceId,
        source_record_id: `${childId}|${name}|${parentId}${token}`,
      });
    };
    if (relation === "parent") {
      record(related, child, "parent");
      if (!seenParent.has(child)) {
        seenParent.add(child);
        parents.push({ entity_id: child, parent_id: related });
      }
      continue;
    }
    if (relation === "consolidated_with") {
      record(child, related, "consolidated_with");
      continue;
    }
    if (relation === "in_county") {
      record(related, child, "in_county");
      continue;
    }
    skipped++;
  }
  return { relations, parents, skipped };
}

export type MappedImage = {
  entity_id: string | null;
  feed_entity_id: string | null;
  role: "seal" | "flag" | "logo";
  file: string | null;
  file_url: string | null;
  license: string;
  fair_use: boolean;
  public: boolean;
  icon: boolean;
  usage_basis: string | null;
  attribution: string | null;
  source_url: string | null;
  wikidata: string | null;
  retrieved_at: string | null;
  source_ids: string[];
};

function yes(raw: string | undefined): boolean {
  const text = (raw ?? "").trim().toLowerCase();
  return text === "yes" || text === "true" || text === "1";
}

function orNull(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return text || null;
}

/**
 * entity_images.csv: `role`, `file`, `feed_id`, plus `public` and `icon`.
 * Older names (`image_kind`, `commons_file`, `feed_entity_id`) still map.
 * A public row needs a free licence and attribution. A hidden row needs
 * attribution and a source URL. Rows that cannot satisfy either check are
 * skipped. No image bytes are downloaded. An icon has to be public.
 */
export function mapInstImage(row: Record<string, string>): MappedImage | null {
  const role = (row.role ?? row.image_kind ?? "").trim();
  if (!ROLES.has(role)) return null;
  const entityId = orNull(row.entity_id);
  const feedId = orNull(row.feed_id ?? row.feed_entity_id);
  if (!entityId && !feedId) return null;
  const fairUse = yes(row.fair_use);
  const attribution = orNull(row.attribution);
  const sourceUrl = orNull(row.source_url);
  const licenseRaw = (row.license ?? "").trim();
  const license = licenseRaw || (fairUse ? "fair-use" : "unknown");
  const askedPublic = row.public != null && row.public.trim() !== "" ? yes(row.public) : !fairUse;
  const isPublic =
    askedPublic && !fairUse && attribution != null && licenseRaw !== "" && licenseRaw.toLowerCase() !== "fair-use";
  if (!isPublic && (attribution == null || sourceUrl == null)) return null;
  const icon = yes(row.icon) && isPublic;
  return {
    entity_id: entityId,
    feed_entity_id: feedId,
    role: role as MappedImage["role"],
    file: orNull(row.file ?? row.commons_file),
    file_url: orNull(row.commons_url ?? row.file_url),
    license,
    fair_use: fairUse,
    public: isPublic,
    icon,
    usage_basis: orNull(row.usage_basis),
    attribution,
    source_url: sourceUrl,
    wikidata: wikidataId(row.wikidata ?? row.wikidata_qid),
    retrieved_at: orNull(row.retrieved_at),
    source_ids: sourceList(row.source_id),
  };
}

/** At most one icon per entity. Extra icons stay as ordinary images. */
export function dedupeIcons(images: MappedImage[]): MappedImage[] {
  const seen = new Set<string>();
  return images.map((row) => {
    if (!row.icon) return row;
    const key = row.entity_id ?? row.feed_entity_id ?? "";
    if (seen.has(key)) return { ...row, icon: false };
    seen.add(key);
    return row;
  });
}

async function ensureSources(db: pg.PoolClient, ids: string[]): Promise<void> {
  const unique = [...new Set(ids.filter(Boolean))];
  if (unique.length === 0) return;
  await insertJsonChunks(
    db,
    `insert into source (source_id, title)
     select source_id, 'inst-entities'
     from jsonb_to_recordset($1::jsonb) as x(source_id text)
     on conflict (source_id) do nothing`,
    unique.map((source_id) => ({ source_id })),
  );
}

export async function applyInstRelations(
  db: pg.Pool,
  rows: InstRelationRow[],
): Promise<{ relations: number; parents: number; skipped: number }> {
  const mapped = mapInstRelations(rows);
  if (mapped.relations.length === 0) return { relations: 0, parents: 0, skipped: mapped.skipped };
  const client = await db.connect();
  try {
    await client.query("begin");
    await ensureSources(
      client,
      mapped.relations.map((row) => row.source_id ?? ""),
    );
    const written = await insertJsonChunks(
      client,
      `insert into entity_relation (parent_id, child_id, relation, method, source_id, source_record_id)
       select parent_id, child_id, relation, method, source_id, source_record_id
       from jsonb_to_recordset($1::jsonb) as x(
         parent_id text, child_id text, relation text, method text, source_id text, source_record_id text
       )
       on conflict (parent_id, child_id, relation, valid_from) do update
         set method = excluded.method, source_record_id = excluded.source_record_id
         where entity_relation.method is distinct from excluded.method
            or entity_relation.source_record_id is distinct from excluded.source_record_id`,
      mapped.relations,
    );
    if (mapped.parents.length > 0) {
      await client.query(
        `update entity e set parent_id = x.parent_id
         from jsonb_to_recordset($1::jsonb) as x(entity_id text, parent_id text)
         where e.entity_id = x.entity_id and e.parent_id is distinct from x.parent_id`,
        [JSON.stringify(mapped.parents)],
      );
    }
    await client.query("commit");
    return { relations: written, parents: mapped.parents.length, skipped: mapped.skipped };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

export async function applyInstImages(
  db: pg.Pool,
  rows: Record<string, string>[],
): Promise<{ images: number; skipped: number }> {
  const images: MappedImage[] = [];
  let skipped = 0;
  for (const row of rows) {
    const mapped = mapInstImage(row);
    if (!mapped) {
      skipped++;
      continue;
    }
    images.push(mapped);
  }
  const ready = dedupeIcons(images);
  if (ready.length === 0) return { images: 0, skipped };
  const client = await db.connect();
  try {
    await client.query("begin");
    await ensureSources(
      client,
      ready.flatMap((row) => row.source_ids),
    );
    const written = await insertJsonChunks(
      client,
      `insert into entity_image (
         entity_id, feed_entity_id, role, file, file_url, license, fair_use, public, icon,
         usage_basis, attribution, source_url, wikidata, retrieved_at
       )
       select nullif(entity_id, ''), nullif(feed_entity_id, ''), role, file, file_url, license,
              fair_use, public, icon, usage_basis, attribution, source_url, wikidata, retrieved_at
       from jsonb_to_recordset($1::jsonb) as x(
         entity_id text, feed_entity_id text, role text, file text, file_url text, license text,
         fair_use boolean, public boolean, icon boolean, usage_basis text, attribution text,
         source_url text, wikidata text, retrieved_at timestamptz
       )
       on conflict (entity_id, feed_entity_id, role) do update
         set file = excluded.file, file_url = excluded.file_url, license = excluded.license,
             fair_use = excluded.fair_use, public = excluded.public, icon = excluded.icon,
             usage_basis = excluded.usage_basis, source_url = excluded.source_url,
             wikidata = excluded.wikidata, attribution = excluded.attribution`,
      ready.map((row) => ({
        entity_id: row.entity_id ?? "",
        feed_entity_id: row.feed_entity_id ?? "",
        role: row.role,
        file: row.file,
        file_url: row.file_url,
        license: row.license,
        fair_use: row.fair_use,
        public: row.public,
        icon: row.icon,
        usage_basis: row.usage_basis,
        attribution: row.attribution,
        source_url: row.source_url,
        wikidata: row.wikidata,
        retrieved_at: row.retrieved_at,
      })),
    );
    const links = ready.flatMap((row) =>
      row.source_ids.map((source_id, ord) => ({
        entity_id: row.entity_id ?? "",
        feed_entity_id: row.feed_entity_id ?? "",
        role: row.role,
        source_id,
        ord: ord + 1,
      })),
    );
    if (links.length > 0) {
      await insertJsonChunks(
        client,
        `insert into entity_image_source (image_id, source_id, ord)
         select i.id, x.source_id, x.ord
         from jsonb_to_recordset($1::jsonb) as x(
           entity_id text, feed_entity_id text, role text, source_id text, ord int
         )
         join entity_image i
           on i.role = x.role
          and i.entity_id is not distinct from nullif(x.entity_id, '')
          and i.feed_entity_id is not distinct from nullif(x.feed_entity_id, '')
         on conflict (image_id, source_id) do nothing`,
        links,
      );
    }
    await client.query("commit");
    return { images: written, skipped };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

const INST_FILES = [
  "data-v3/inst/entities.csv",
  "data-v3/inst/entity_relations.csv",
  "data-v3/inst/entity_images.csv",
  "data-v3/inst/body_entity.csv",
] as const;

const ENTITY_KINDS = new Set([
  "nation", "territory", "province", "state", "county", "municipality", "township",
  "school_unified", "school_elementary", "school_secondary",
  "chamber", "dc_council", "subdivision", "court", "special_district", "indigenous_government",
  "government_other", "brand", "organization", "company", "nonprofit", "fund", "other",
]);

const BODY_ROLES = new Set(["council", "mayor", "chamber", "court", "board"]);
const PRECISIONS = new Set(["day", "month", "year"]);

export type InstitutionEstimate = {
  entities: number;
  relations: number;
  images: number;
  bodies: number;
  fileBytes: number;
  databaseBytes: number;
  projectedBytes: number | null;
  parts: { table: string; rows: number; bytesPerRow: number | null; bytes: number | null }[];
  note: string;
};

export type InstitutionLoadReport = {
  status: "applied" | "refused";
  entities: number;
  relations: number;
  images: number;
  imagesSkipped: number;
  bodies: number;
  parents: number;
  estimate: InstitutionEstimate;
  gap: string | null;
  gitCommit: string | null;
};

type InstInputs = {
  entities: Record<string, string>[];
  relations: Record<string, string>[];
  images: Record<string, string>[];
  bodies: Record<string, string>[];
  files: { fileName: string; sha256: string; rows: number }[];
  fileBytes: number;
  gitCommit: string | null;
};

function blank(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return text || null;
}

function day(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : null;
}

function textList(raw: string | undefined): string[] | null {
  const items = (raw ?? "").split(";").map((part) => part.trim()).filter(Boolean);
  return items.length ? items : null;
}

export async function measureInstitutionGrowth(
  db: pg.Pool,
  counts: { entities: number; relations: number; images: number; bodies: number; fileBytes: number },
  databaseBytes: number,
): Promise<InstitutionEstimate> {
  const sized = await db.query<{
    entity_bytes: string;
    entity_rows: string;
    relation_bytes: string;
    relation_rows: string;
    image_bytes: string;
    image_rows: string;
    body_bytes: string;
    body_rows: string;
  }>(`
    select pg_total_relation_size('usd.entity')::text entity_bytes,
           (select count(*)::text from entity) entity_rows,
           pg_total_relation_size('usd.entity_relation')::text relation_bytes,
           (select count(*)::text from entity_relation) relation_rows,
           pg_total_relation_size('usd.entity_image')::text image_bytes,
           (select count(*)::text from entity_image) image_rows,
           pg_total_relation_size('usd.body_entity')::text body_bytes,
           (select count(*)::text from body_entity) body_rows
  `);
  const size = sized.rows[0];
  const part = (table: string, addRows: number, relBytes: string | undefined, relRows: string | undefined) => {
    const rows = Number(relRows ?? 0);
    const bytesPerRow = rows > 0 ? Number(relBytes ?? 0) / rows : null;
    return {
      table,
      rows: addRows,
      bytesPerRow,
      bytes: bytesPerRow == null ? null : Math.round(addRows * bytesPerRow),
    };
  };
  const parts = [
    part("entity", counts.entities, size?.entity_bytes, size?.entity_rows),
    part("entity_relation", counts.relations, size?.relation_bytes, size?.relation_rows),
    part("entity_image", counts.images, size?.image_bytes, size?.image_rows),
    part("body_entity", counts.bodies, size?.body_bytes, size?.body_rows),
  ];
  const unmeasured = parts.filter((row) => row.rows > 0 && row.bytes == null).map((row) => row.table);
  const projectedBytes = unmeasured.length
    ? null
    : databaseBytes + parts.reduce((sum, row) => sum + (row.bytes ?? 0), 0);
  const note = [
    `Source files are ${counts.fileBytes} bytes on disk. That number is the CSV size, not a Postgres estimate.`,
    unmeasured.length
      ? `Unmeasured (that table has no rows yet, so there is no bytes-per-row): ${unmeasured.join(", ")}.`
      : "Projected growth is pg_total_relation_size divided by the live row count, times the rows in these files.",
    "Image binaries are not loaded.",
  ].join(" ");
  return {
    entities: counts.entities,
    relations: counts.relations,
    images: counts.images,
    bodies: counts.bodies,
    fileBytes: counts.fileBytes,
    databaseBytes,
    projectedBytes,
    parts,
    note,
  };
}

export function ensureInstCache(root: string): { dir: string; commit: string } {
  const dest = join(root, "v3/.cache/inst-entities");
  fetchOrigin(root, ["data/inst-entities"]);
  const head = originCommit(root, "data/inst-entities");
  if (!needsRefresh(dest, head, [...INST_FILES])) return { dir: dest, commit: head };
  mkdirSync(dest, { recursive: true });
  const tar = execFileSync("git", ["archive", "origin/data/inst-entities", ...INST_FILES], {
    cwd: root,
    encoding: "buffer",
    maxBuffer: 80 * 1024 * 1024,
  });
  execFileSync("tar", ["-x", "-C", dest], { input: tar });
  stampCommit(dest, head);
  return { dir: dest, commit: head };
}

function readInst(root: string): InstInputs {
  const { dir, commit } = ensureInstCache(root);
  const files = INST_FILES.map((rel) => {
    const loaded = readFileText(join(dir, rel));
    const parsed = parseCsv(loaded.text);
    return { rel, buffer: loaded.bytes, rows: parsed.rows };
  });
  return {
    entities: files[0]!.rows,
    relations: files[1]!.rows,
    images: files[2]!.rows,
    bodies: files[3]!.rows,
    files: files.map((file) => ({
      fileName: file.rel,
      sha256: sha256Hex(file.buffer),
      rows: file.rows.length,
    })),
    fileBytes: files.reduce((sum, file) => sum + file.buffer.byteLength, 0),
    gitCommit: commit || null,
  };
}

export async function loadInstitutionTables(
  db: pg.Pool,
  input: InstInputs,
): Promise<Omit<InstitutionLoadReport, "estimate" | "gap"> & { imagesSkipped: number }> {
  const entityIds = new Set(input.entities.map((row) => row.entity_id.trim()).filter(Boolean));
  const entities: Record<string, unknown>[] = [];
  const parents: { entity_id: string; parent_id: string }[] = [];
  const succession: { predecessor_id: string; successor_id: string }[] = [];
  const sourceIds: string[] = [];
  for (const row of input.entities) {
    const entityId = (row.entity_id ?? "").trim();
    const kind = (row.kind ?? "").trim();
    const name = (row.name ?? "").trim();
    if (!entityId || !name || !ENTITY_KINDS.has(kind)) continue;
    sourceIds.push(...(textList(row.source_id) ?? []));
    entities.push({
      entity_id: entityId,
      kind,
      state_fips: /^\d{2}$/.test((row.state_fips ?? "").trim()) ? row.state_fips.trim() : null,
      state: blank(row.state),
      name,
      label: blank(row.label),
      gov_status: blank(row.gov_status),
      valid_from: day(row.valid_from),
      valid_to: day(row.valid_to),
      v2_layer: textList(row.v2_layer),
      v2_key: textList(row.v2_key),
      v2_row: textList(row.v2_row),
      feed: blank(row.feed),
      level: blank(row.level),
      type: blank(row.type),
      cog_pid6: blank(row.cog_pid6),
      flags: textList(row.flags),
      source_record_id: blank(row.source_record_id),
      wikidata: wikidataId(row.wikidata),
      iso_3166_2: blank(row.iso_3166_2),
      constituent_qid: /^Q[0-9]+$/.test((row.constituent_qid ?? "").trim()) ? row.constituent_qid.trim() : null,
      inception: day(row.inception),
      inception_precision: PRECISIONS.has((row.inception_precision ?? "").trim()) ? row.inception_precision.trim() : null,
      inception_source: blank(row.inception_source),
    });
    const parentId = (row.parent_id ?? "").trim();
    if (parentId && parentId !== entityId) parents.push({ entity_id: entityId, parent_id: parentId });
    for (const predecessor of textList(row.predecessor_id) ?? []) {
      if (predecessor !== entityId && entityIds.has(predecessor)) {
        succession.push({ predecessor_id: predecessor, successor_id: entityId });
      }
    }
    for (const successor of textList(row.successor_id) ?? []) {
      if (successor !== entityId && entityIds.has(successor)) {
        succession.push({ predecessor_id: entityId, successor_id: successor });
      }
    }
  }
  const mappedRelations = mapInstRelations(
    input.relations.map((row) => ({
      entity_id: row.entity_id ?? "",
      relation: row.relation ?? "",
      related_entity_id: row.related_entity_id ?? "",
      method: row.method,
      source_id: row.source_id,
    })),
  );
  sourceIds.push(...mappedRelations.relations.map((row) => row.source_id ?? ""));
  const images: MappedImage[] = [];
  let imagesSkipped = 0;
  for (const row of input.images) {
    const mapped = mapInstImage(row);
    if (!mapped) {
      imagesSkipped++;
      continue;
    }
    images.push(mapped);
  }
  const readyImages = dedupeIcons(images);
  sourceIds.push(...readyImages.flatMap((row) => row.source_ids));
  const bodies = input.bodies.flatMap((row) => {
    const role = (row.role ?? "").trim();
    const entityId = (row.entity_id ?? "").trim();
    const bodyKey = (row.body_key ?? "").trim();
    if (!bodyKey || !entityId || !BODY_ROLES.has(role)) return [];
    sourceIds.push(...(textList(row.source_id) ?? []));
    return [{ body_key: bodyKey, entity_id: entityId, role, source_record_id: blank(row.source_record_id) }];
  });

  const client = await db.connect();
  try {
    await client.query("begin");
    await client.query("set local statement_timeout = '10min'");
    await ensureSources(client, sourceIds);
    const entityWrites = await insertJsonChunks(
      client,
      `insert into entity (
         entity_id, kind, state_fips, state, name, label, gov_status, valid_from, valid_to,
         v2_layer, v2_key, v2_row, feed, level, type, cog_pid6, flags, origin,
         source_record_id, wikidata, iso_3166_2, constituent_qid,
         inception, inception_precision, inception_source
       )
       select entity_id, kind, state_fips, state, name, label, gov_status, valid_from, valid_to,
              v2_layer, v2_key, v2_row, feed, level, type, cog_pid6, flags, 'inst',
              source_record_id, wikidata, iso_3166_2, constituent_qid,
              inception, inception_precision, inception_source
       from jsonb_to_recordset($1::jsonb) as x(
         entity_id text, kind text, state_fips text, state text, name text, label text, gov_status text,
         valid_from date, valid_to date, v2_layer text[], v2_key text[], v2_row text[],
         feed text, level text, type text, cog_pid6 text, flags text[], source_record_id text,
         wikidata text, iso_3166_2 text, constituent_qid text, inception date,
         inception_precision text, inception_source text
       )
       on conflict (entity_id) do update
         set kind = excluded.kind, state_fips = excluded.state_fips, state = excluded.state,
             name = excluded.name, label = excluded.label, gov_status = excluded.gov_status,
             valid_from = excluded.valid_from, valid_to = excluded.valid_to,
             v2_layer = excluded.v2_layer, v2_key = excluded.v2_key, v2_row = excluded.v2_row,
             feed = excluded.feed, level = excluded.level, type = excluded.type, cog_pid6 = excluded.cog_pid6,
             flags = excluded.flags, source_record_id = excluded.source_record_id,
             wikidata = excluded.wikidata, iso_3166_2 = excluded.iso_3166_2,
             constituent_qid = excluded.constituent_qid, inception = excluded.inception,
             inception_precision = excluded.inception_precision, inception_source = excluded.inception_source
         where entity.origin = 'inst'`,
      entities,
    );
    if (parents.length > 0) {
      await insertJsonChunks(
        client,
        `update entity e set parent_id = x.parent_id
         from jsonb_to_recordset($1::jsonb) as x(entity_id text, parent_id text)
         where e.entity_id = x.entity_id and e.origin = 'inst' and e.parent_id is distinct from x.parent_id`,
        parents,
      );
    }
    if (mappedRelations.parents.length > 0) {
      await insertJsonChunks(
        client,
        `update entity e set parent_id = x.parent_id
         from jsonb_to_recordset($1::jsonb) as x(entity_id text, parent_id text)
         where e.entity_id = x.entity_id and e.origin = 'inst' and e.parent_id is distinct from x.parent_id`,
        mappedRelations.parents,
      );
    }
    if (succession.length > 0) {
      await insertJsonChunks(
        client,
        `insert into entity_succession (predecessor_id, successor_id)
         select predecessor_id, successor_id
         from jsonb_to_recordset($1::jsonb) as x(predecessor_id text, successor_id text)
         on conflict (predecessor_id, successor_id) do nothing`,
        succession,
      );
    }
    const relationWrites = mappedRelations.relations.length
      ? await insertJsonChunks(
          client,
          `insert into entity_relation (parent_id, child_id, relation, method, source_id, source_record_id)
           select parent_id, child_id, relation, method, source_id, source_record_id
           from jsonb_to_recordset($1::jsonb) as x(
             parent_id text, child_id text, relation text, method text, source_id text, source_record_id text
           )
           on conflict (parent_id, child_id, relation, valid_from) do update
             set method = excluded.method, source_record_id = excluded.source_record_id
             where entity_relation.method is distinct from excluded.method
                or entity_relation.source_record_id is distinct from excluded.source_record_id`,
          mappedRelations.relations,
        )
      : 0;
    const imageWrites = readyImages.length
      ? await insertJsonChunks(
          client,
          `insert into entity_image (
             entity_id, feed_entity_id, role, file, file_url, license, fair_use, public, icon,
             usage_basis, attribution, source_url, wikidata, retrieved_at
           )
           select nullif(entity_id, ''), nullif(feed_entity_id, ''), role, file, file_url, license,
                  fair_use, public, icon, usage_basis, attribution, source_url, wikidata, retrieved_at
           from jsonb_to_recordset($1::jsonb) as x(
             entity_id text, feed_entity_id text, role text, file text, file_url text, license text,
             fair_use boolean, public boolean, icon boolean, usage_basis text, attribution text,
             source_url text, wikidata text, retrieved_at timestamptz
           )
           on conflict (entity_id, feed_entity_id, role) do update
             set file = excluded.file, file_url = excluded.file_url, license = excluded.license,
                 fair_use = excluded.fair_use, public = excluded.public, icon = excluded.icon,
                 usage_basis = excluded.usage_basis, source_url = excluded.source_url,
                 wikidata = excluded.wikidata, attribution = excluded.attribution`,
          readyImages.map((row) => ({
            entity_id: row.entity_id ?? "",
            feed_entity_id: row.feed_entity_id ?? "",
            role: row.role,
            file: row.file,
            file_url: row.file_url,
            license: row.license,
            fair_use: row.fair_use,
            public: row.public,
            icon: row.icon,
            usage_basis: row.usage_basis,
            attribution: row.attribution,
            source_url: row.source_url,
            wikidata: row.wikidata,
            retrieved_at: row.retrieved_at,
          })),
        )
      : 0;
    if (readyImages.some((row) => row.source_ids.length > 0)) {
      await insertJsonChunks(
        client,
        `insert into entity_image_source (image_id, source_id, ord)
         select i.id, x.source_id, x.ord
         from jsonb_to_recordset($1::jsonb) as x(
           entity_id text, feed_entity_id text, role text, source_id text, ord int
         )
         join entity_image i
           on i.role = x.role
          and i.entity_id is not distinct from nullif(x.entity_id, '')
          and i.feed_entity_id is not distinct from nullif(x.feed_entity_id, '')
         on conflict (image_id, source_id) do nothing`,
        readyImages.flatMap((row) =>
          row.source_ids.map((source_id, ord) => ({
            entity_id: row.entity_id ?? "",
            feed_entity_id: row.feed_entity_id ?? "",
            role: row.role,
            source_id,
            ord: ord + 1,
          })),
        ),
      );
    }
    const bodyWrites = bodies.length
      ? await insertJsonChunks(
          client,
          `insert into body_entity (body_key, entity_id, role, source_record_id)
           select body_key, entity_id, role, source_record_id
           from jsonb_to_recordset($1::jsonb) as x(body_key text, entity_id text, role text, source_record_id text)
           on conflict (body_key) do update
             set entity_id = excluded.entity_id, role = excluded.role, source_record_id = excluded.source_record_id
             where body_entity.entity_id is distinct from excluded.entity_id
                or body_entity.role is distinct from excluded.role
                or body_entity.source_record_id is distinct from excluded.source_record_id`,
          bodies,
        )
      : 0;
    for (const file of input.files) {
      const batch = await client.query<{ id: string }>(
        `insert into load_batch (file_name, file_sha256, git_commit, row_count, status, finished_at)
         values ($1, $2, $3, $4, 'applied', now())
         on conflict (file_sha256) do update
           set status = 'applied', finished_at = now(), row_count = excluded.row_count,
               git_commit = coalesce(excluded.git_commit, load_batch.git_commit)
         returning id`,
        [file.fileName, file.sha256, input.gitCommit, file.rows],
      );
      if (batch.rows[0]) await markSuperseded(client, file.fileName, batch.rows[0].id);
    }
    if (entityWrites + relationWrites + imageWrites + bodyWrites > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query("commit");
    return {
      status: "applied",
      entities: entities.length,
      relations: mappedRelations.relations.length,
      images: readyImages.length,
      imagesSkipped,
      bodies: bodies.length,
      parents: parents.length,
      gitCommit: input.gitCommit,
    };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

export async function loadInstitutions(
  db: pg.Pool,
  opts: { root: string; currentBytes: number; allow: boolean },
): Promise<InstitutionLoadReport> {
  const input = readInst(opts.root);
  const estimate = await measureInstitutionGrowth(
    db,
    {
      entities: input.entities.length,
      relations: input.relations.length,
      images: input.images.length,
      bodies: input.bodies.length,
      fileBytes: input.fileBytes,
    },
    opts.currentBytes,
  );
  if (overMeasuredBudget(opts.currentBytes) && !opts.allow) {
    return {
      status: "refused",
      entities: 0,
      relations: 0,
      images: 0,
      imagesSkipped: 0,
      bodies: 0,
      parents: 0,
      estimate,
      gitCommit: input.gitCommit,
      gap: `institutions: database is ${formatMb(opts.currentBytes)} (pg_database_size), over ${formatMb(BUDGET_BYTES)}. ${estimate.note} Rows were not inserted.`,
    };
  }
  const loaded = await loadInstitutionTables(db, input);
  return { ...loaded, estimate, gap: null };
}
