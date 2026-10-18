import { readFileSync } from "node:fs";
import { stateAbbr } from "@usd/core";
import type { RawResult } from "./validate.ts";
import { unwrapJson } from "./geom.ts";

type Triple = [number, number, number, number?];

const PRES: Record<number, { dem: [string, string]; rep: [string, string] }> = {
  2016: { dem: ["clinton-hillary-r", "Hillary Clinton"], rep: ["trump-donald-j", "Donald J. Trump"] },
  2020: { dem: ["biden-joseph-r", "Joseph R. Biden Jr."], rep: ["trump-donald-j", "Donald J. Trump"] },
  2024: { dem: ["harris-kamala-d", "Kamala D. Harris"], rep: ["trump-donald-j", "Donald J. Trump"] },
};

export type LegacyContext = {
  fileName: string;
  sourceUrl: string;
  retrievedAt: string;
  /** legacy_key → unit_id (GEOID) for the unit type being read. */
  unitIdByLegacy: Map<string, string>;
  gaps?: string[];
};

function rowsFromTriple(
  ctx: LegacyContext,
  input: {
    lineNo: number;
    stateName: string;
    legacyKey: string;
    unitType: string;
    year: number;
    triple: Triple | null;
    estimate: boolean;
  },
): RawResult[] {
  if (!input.triple) return [];
  const [d, r, tot] = input.triple;
  if (d == null || r == null || tot == null) return [];
  const other = tot - d - r;
  if (other < 0) {
    ctx.gaps?.push(`${ctx.fileName}: negative other ${input.legacyKey} ${input.year}`);
    return [];
  }
  const abbr = stateAbbr(input.stateName);
  const unitId = ctx.unitIdByLegacy.get(input.legacyKey);
  if (!abbr || !unitId) {
    ctx.gaps?.push(`${ctx.fileName}: no unit for ${input.legacyKey}`);
    return [];
  }
  const who = PRES[input.year];
  if (!who) throw new Error(`no presidential candidates for ${input.year}`);
  const base = {
    state: abbr,
    year: String(input.year),
    office: "president",
    district: "statewide",
    unitId,
    unitType: input.unitType,
    weight: "1",
    sourceUrl: ctx.sourceUrl,
    retrievedAt: ctx.retrievedAt,
    method: "v2_import",
    boundarySet: "v2-2024",
    estimate: input.estimate,
  };
  const specs: [string, string, string, number][] = [
    [who.dem[0], who.dem[1], "DEM", d],
    [who.rep[0], who.rep[1], "REP", r],
    ["all-others", "All others", "OTH", other],
  ];
  return specs.map((spec, i) => ({
    lineNo: input.lineNo * 10 + i,
    ...base,
    candidateId: spec[0],
    answer: spec[1],
    party: spec[2],
    votes: String(spec[3]),
  }));
}

function asTriple(value: unknown): Triple | null {
  if (!Array.isArray(value) || value.length < 3) return null;
  if (value[0] == null || value[1] == null || value[2] == null) return null;
  return value as Triple;
}

/** County presidential tables: election2016/2020/2024.js. */
export function countyPresRows(fileName: string, source: string, year: number, ctx: LegacyContext): RawResult[] {
  const data = unwrapJson(source) as Record<string, unknown>;
  const out: RawResult[] = [];
  let n = 0;
  for (const [key, value] of Object.entries(data)) {
    n++;
    const stateName = key.split("|")[0] ?? "";
    out.push(
      ...rowsFromTriple(ctx, {
        lineNo: n,
        stateName,
        legacyKey: key,
        unitType: "county",
        year,
        triple: asTriple(value),
        estimate: false,
      }),
    );
  }
  void fileName;
  return out;
}

/** ds2016-states.js and ds2016-cd.js. Fourth element 1 → estimate. */
export function ds2016Rows(source: string, unitType: "state" | "ushouse", ctx: LegacyContext): RawResult[] {
  const data = unwrapJson(source) as Record<string, unknown>;
  const out: RawResult[] = [];
  let n = 0;
  for (const [key, value] of Object.entries(data)) {
    n++;
    const triple = asTriple(value);
    if (!triple) continue;
    const stateName = unitType === "state" ? key : (key.split("|")[0] ?? "");
    const estimate = triple[3] === 1;
    out.push(
      ...rowsFromTriple(ctx, {
        lineNo: n,
        stateName,
        legacyKey: key,
        unitType,
        year: 2016,
        triple,
        estimate,
      }),
    );
  }
  return out;
}

type CdRow = [string, string, unknown, unknown, unknown, string?];

/** uscd.js carries 2024 then 2020 presidential triples on each district. */
export function uscdResultRows(source: string, ctx: LegacyContext): RawResult[] {
  const data = unwrapJson(source) as CdRow[];
  const out: RawResult[] = [];
  data.forEach((row, i) => {
    const stateName = row[0];
    const code = row[1];
    const legacyKey = `${stateName}|${code}`;
    const flag = row[5];
    out.push(
      ...rowsFromTriple(ctx, {
        lineNo: i + 1,
        stateName,
        legacyKey,
        unitType: "ushouse",
        year: 2024,
        triple: asTriple(row[3]),
        estimate: flag === "est" || flag === "e24",
      }),
    );
    out.push(
      ...rowsFromTriple(ctx, {
        lineNo: i + 1 + data.length,
        stateName,
        legacyKey,
        unitType: "ushouse",
        year: 2020,
        triple: asTriple(row[4]),
        estimate: flag === "est" || flag === "e20",
      }),
    );
  });
  return out;
}

export function readLegacy(path: string): string {
  return readFileSync(path, "utf8");
}
