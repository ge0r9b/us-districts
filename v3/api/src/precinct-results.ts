import { readFileSync } from "node:fs";
import { isGray, shares, sortRows, type SortBy, type SortDir, type ValueFormat, applyFormat } from "@usd/core";
import { estAt, locatePack, type PrecinctPack } from "../../ingest/precincts.ts";

export function contestParts(key: string): { year: number; office: string } | null {
  const [year, , office] = key.split("|");
  const parsed = Number(year);
  if (!office || !Number.isFinite(parsed)) return null;
  return { year: parsed, office };
}

export function precinctResults(opts: {
  packsDir: string;
  contests: string[];
  state: string;
  fmt: ValueFormat | null;
  by: SortBy;
  dir: SortDir;
  sortAnswer: string | null;
  dv: number;
  boundary: string;
}): { status: number; body: unknown } {
  const parts = opts.contests.map(contestParts);
  if (parts.some((part) => !part)) {
    return { status: 404, body: { error: { code: "contest_not_found", message: "Unknown contest" }, dv: opts.dv } };
  }
  const packs = parts.map((part) => locatePack(opts.packsDir, opts.state.toUpperCase(), part!.year, part!.office));
  if (packs.some((pack) => !pack)) {
    return {
      status: 404,
      body: { error: { code: "pack_not_found", message: "No precinct pack for that state and contest" }, dv: opts.dv },
    };
  }
  const decoded = packs.map((pack) => JSON.parse(readFileSync(pack!.file, "utf8")) as PrecinctPack);
  const primary = decoded[0]!;
  const answers: string[] = [...primary.answers];
  const sortKey = opts.sortAnswer && answers.includes(opts.sortAnswer) ? opts.sortAnswer : answers[0]!;
  const sortIndex = Math.max(0, answers.indexOf(sortKey));
  const rows = primary.ids.map((id, index) => {
    const cells = decoded.map((pack) => cellOf(pack, index, answers.length));
    const lead = cells[0]!;
    return {
      unit: id,
      legacy: primary.names[index] ?? id,
      name: primary.names[index] ?? id,
      state: primary.state,
      cells,
      votes: lead.votes?.[sortIndex] ?? null,
      share: lead.share?.[sortIndex] ?? null,
      gray: lead.gray,
    };
  });
  const sorted = sortRows(rows, opts.by, opts.dir).map((row, index) => ({ ...row, rank: row.gray ? null : index + 1 }));
  const display = { d: "dem_nominee", r: "rep_nominee" };
  if (opts.contests.length === 1) {
    return {
      status: 200,
      body: {
        dv: opts.dv,
        contest: opts.contests,
        unit_type: "precinct",
        boundary_set: opts.boundary,
        answers,
        display_slots: display,
        rows: sorted.map((row) => {
          const cell = row.cells[0]!;
          const payload = {
            unit: row.unit,
            legacy: row.legacy,
            name: row.name,
            votes: cell.votes,
            total: cell.total,
            share: cell.share,
            est: cell.est,
            gray: cell.gray,
            rank: row.rank,
          };
          return opts.fmt ? { ...payload, text: applyFormat(payload, opts.fmt) } : payload;
        }),
      },
    };
  }
  return {
    status: 200,
    body: {
      dv: opts.dv,
      contest: opts.contests,
      unit_type: "precinct",
      boundary_set: opts.boundary,
      answers,
      display_slots: Object.fromEntries(opts.contests.map((key) => [key, display])),
      rows: sorted.map((row) => ({
        unit: row.unit,
        legacy: row.legacy,
        name: row.name,
        series: Object.fromEntries(row.cells.map((cell, index) => [opts.contests[index], cell])),
        rank: row.rank,
      })),
    },
  };
}

function cellOf(pack: PrecinctPack, index: number, answerCount: number) {
  const triple = pack.votes[index];
  const total = pack.total[index];
  const has = triple != null && total != null;
  const votes = has ? answersFrom(triple, answerCount) : null;
  return {
    votes,
    total,
    share: votes && total != null ? shares(votes, total) : null,
    est: estAt(pack.est, index),
    gray: isGray(has, null),
  };
}

function answersFrom(triple: [number, number, number], answerCount: number): number[] {
  const votes = [triple[0], triple[1], triple[2]];
  while (votes.length < answerCount) votes.push(0);
  return votes.slice(0, answerCount);
}
