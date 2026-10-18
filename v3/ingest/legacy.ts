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

/** Dem, Rep, total. The optional fourth flag on a 2016 row is not part of this. */
export type VoteTriple = [number, number, number];

const DC_COUNTY_KEY = "District of Columbia|District of Columbia";
const DC_HOUSE_KEY = "District of Columbia|00";

function voteTriple(value: unknown): VoteTriple | null {
  const triple = asTriple(value);
  if (!triple) return null;
  return [triple[0], triple[1], triple[2]];
}

/** County or state name → triple. Blank and non-triples are dropped. */
export function readPresTable(source: string): Record<string, VoteTriple> {
  const data = unwrapJson(source) as Record<string, unknown>;
  const out: Record<string, VoteTriple> = {};
  for (const [key, value] of Object.entries(data)) {
    const triple = voteTriple(value);
    if (triple) out[key] = triple;
  }
  return out;
}

/** Official Alaska state totals and the 30 boroughs. Borough sums are not the state total. */
export function readAkPres(source: string): {
  boroughs: { 2020: Record<string, VoteTriple>; 2024: Record<string, VoteTriple> };
  state: { 2020: VoteTriple; 2024: VoteTriple };
} {
  const data = unwrapJson(source) as Record<string, unknown>;
  const mapOf = (key: string): Record<string, VoteTriple> => {
    const raw = data[key];
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`ak.js missing ${key}`);
    const out: Record<string, VoteTriple> = {};
    for (const [name, value] of Object.entries(raw as Record<string, unknown>)) {
      const triple = voteTriple(value);
      if (!triple) throw new Error(`ak.js ${key} ${name} is not a triple`);
      out[name] = triple;
    }
    return out;
  };
  const stateOf = (key: string): VoteTriple => {
    const triple = voteTriple(data[key]);
    if (!triple) throw new Error(`ak.js missing ${key}`);
    return triple;
  };
  return {
    boroughs: { 2020: mapOf("boro2020"), 2024: mapOf("boro2024") },
    state: { 2020: stateOf("state2020"), 2024: stateOf("state2024") },
  };
}

/** Citywide DC presidential totals. dc.js is an IIFE, so this reads the A20/A24 literals and does not eval. */
export function readDcCity(source: string): { 2020: VoteTriple; 2024: VoteTriple } {
  const tripleOf = (token: "A20" | "A24"): VoteTriple => {
    const match = source.match(new RegExp(`${token}=\\s*\\[\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*\\]`));
    if (!match) throw new Error(`dc.js missing ${token}`);
    return [Number(match[1]), Number(match[2]), Number(match[3])];
  };
  return { 2020: tripleOf("A20"), 2024: tripleOf("A24") };
}

/**
 * Keys missing from election2020.js and election2024.js.
 * Alaska boroughs use the names in ak.js. DC is the citywide county key.
 * 2016 already has both in election2016.js, so this is only for 2020 and 2024.
 */
export function countyPresOverlay(
  year: 2020 | 2024,
  akSource: string,
  dcSource: string,
): Record<string, VoteTriple> {
  const ak = readAkPres(akSource);
  const dc = readDcCity(dcSource);
  const out: Record<string, VoteTriple> = {};
  for (const [name, triple] of Object.entries(ak.boroughs[year])) out[`Alaska|${name}`] = triple;
  out[DC_COUNTY_KEY] = dc[year];
  return out;
}

/**
 * State totals for 2020 and 2024: sum of county triples, with the DC city row included.
 * Alaska is the official state triple from ak.js, not the sum of boroughs.
 * 2016 state totals stay on ds2016-states.js.
 */
export function statePresTotals(
  electionSource: string,
  year: 2020 | 2024,
  akSource: string,
  dcSource: string,
): Record<string, VoteTriple> {
  const merged: Record<string, VoteTriple> = { ...readPresTable(electionSource) };
  for (const [key, triple] of Object.entries(countyPresOverlay(year, akSource, dcSource))) {
    if (!merged[key]) merged[key] = triple;
  }
  const sums = new Map<string, VoteTriple>();
  for (const [key, triple] of Object.entries(merged)) {
    const state = key.split("|")[0] ?? "";
    if (!state) continue;
    const cur = sums.get(state) ?? [0, 0, 0];
    sums.set(state, [cur[0] + triple[0], cur[1] + triple[1], cur[2] + triple[2]]);
  }
  sums.set("Alaska", readAkPres(akSource).state[year]);
  return Object.fromEntries(sums);
}

export function rowsFromVoteMap(
  ctx: LegacyContext,
  input: {
    triples: Record<string, VoteTriple>;
    unitType: string;
    year: number;
    stateName: (legacyKey: string) => string;
  },
): RawResult[] {
  const out: RawResult[] = [];
  let n = 0;
  for (const [legacyKey, triple] of Object.entries(input.triples)) {
    n++;
    out.push(
      ...rowsFromTriple(ctx, {
        lineNo: n,
        stateName: input.stateName(legacyKey),
        legacyKey,
        unitType: input.unitType,
        year: input.year,
        triple,
        estimate: false,
      }),
    );
  }
  return out;
}

/** DC at-large presidential triples. uscd.js has Alaska at-large and no DC row. */
export function dcUshouseRows(dcSource: string, ctx: LegacyContext): RawResult[] {
  const city = readDcCity(dcSource);
  const out: RawResult[] = [];
  for (const year of [2024, 2020] as const) {
    out.push(
      ...rowsFromTriple(ctx, {
        lineNo: year,
        stateName: "District of Columbia",
        legacyKey: DC_HOUSE_KEY,
        unitType: "ushouse",
        year,
        triple: city[year],
        estimate: false,
      }),
    );
  }
  return out;
}
