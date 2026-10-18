import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { stateAbbr } from "@usd/core";
import { fetchOrigin, needsRefresh, originCommit, stampCommit } from "./branch-cache.ts";
import { multiPolygon } from "./geom.ts";

const SCALE = 10000;

export type YearVotes = {
  d: number;
  r: number;
  total: number;
  other: number;
  est: boolean;
};

export type PrecinctFeature = {
  id: string;
  ordinal: number;
  county: string;
  name: string;
  lon: number;
  lat: number;
  coordinates: number[][][][];
  votes: Partial<Record<2016 | 2020 | 2024, YearVotes | null>>;
};

export type PrecinctState = {
  abbr: string;
  name: string;
  features: PrecinctFeature[];
  gaps: string[];
};

/** First balanced JSON array at `start`, respecting strings. Never eval. */
export function extractJsonArray(source: string, start: number): unknown[] {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < source.length; i++) {
    const ch = source[i]!;
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') {
      inString = true;
      continue;
    }
    if (ch === "[") depth++;
    else if (ch === "]") {
      depth--;
      if (depth === 0) return JSON.parse(source.slice(start, i + 1)) as unknown[];
    }
  }
  throw new Error("unclosed JSON array in precinct file");
}

export function parsePrecinctCall(source: string): { state: string; rows: unknown[][] } {
  const mark = source.indexOf("__prec");
  if (mark < 0) throw new Error("precinct file has no __prec call");
  const quote = source.indexOf('"', mark);
  let i = quote + 1;
  let state = "";
  while (i < source.length) {
    const ch = source[i]!;
    if (ch === "\\") {
      state += source[i + 1] ?? "";
      i += 2;
      continue;
    }
    if (ch === '"') break;
    state += ch;
    i++;
  }
  while (i < source.length && source[i] !== "[") i++;
  const rows = extractJsonArray(source, i) as unknown[][];
  return { state, rows };
}

function votesOf(row: unknown[], withGeometry: boolean): YearVotes | null {
  if (!Array.isArray(row) || row.length < 5) return null;
  const d = Number(row[2]);
  const r = Number(row[3]);
  const total = Number(row[4]);
  if (![d, r, total].every((n) => Number.isFinite(n))) return null;
  const other = total - d - r;
  if (other < 0 || d < 0 || r < 0 || total < 0) return null;
  const flag = row[5];
  const est = !withGeometry && flag === 1;
  return { d, r, total, other, est };
}

function centroid(coordinates: number[][][][]): { lon: number; lat: number } {
  const ring = coordinates[0]?.[0] ?? [];
  if (ring.length === 0) return { lon: 0, lat: 0 };
  let lon = 0;
  let lat = 0;
  for (const point of ring) {
    lon += point[0] ?? 0;
    lat += point[1] ?? 0;
  }
  return { lon: lon / ring.length, lat: lat / ring.length };
}

function fileName(stateName: string): string {
  return `${stateName.replaceAll(" ", "_")}.js`;
}

function readGeometry(root: string, name: string): string {
  return readFileSync(join(root, "v2/data/precincts2024", fileName(name)), "utf8");
}

/** 2016/2020 value files live on data/election as __prec16 / __prec20. The checkout's v2 copies are not those files. */
export function ensurePrecinctValues(root: string): string {
  const dest = join(root, "v3/.cache/precinct-values");
  const marker = "v2/data/precincts2016/Vermont.js";
  fetchOrigin(root, ["data/election"]);
  const head = originCommit(root, "data/election");
  if (!needsRefresh(dest, head, [marker]) && readFileSync(join(dest, marker), "utf8").includes("__prec16")) {
    return dest;
  }
  mkdirSync(dest, { recursive: true });
  const tar = execFileSync(
    "git",
    ["archive", "origin/data/election", "v2/data/precincts2016", "v2/data/precincts2020"],
    { cwd: root, encoding: "buffer", maxBuffer: 64 * 1024 * 1024 },
  );
  execFileSync("tar", ["-x", "-C", dest], { input: tar });
  stampCommit(dest, head);
  return dest;
}

function readValues(cache: string, year: 2016 | 2020, name: string): string | null {
  const path = join(cache, "v2/data", `precincts${year}`, fileName(name));
  if (!existsSync(path)) return null;
  return readFileSync(path, "utf8");
}

export function loadPrecinctState(root: string, name: string): PrecinctState {
  const abbr = stateAbbr(name);
  if (!abbr) throw new Error(`unknown precinct state ${name}`);
  const gaps: string[] = [];
  const geometry = parsePrecinctCall(readGeometry(root, name));
  const cache = ensurePrecinctValues(root);
  const older: { year: 2016 | 2020; rows: unknown[][] | null }[] = ([2016, 2020] as const).map((year) => {
    const text = readValues(cache, year, geometry.state);
    if (!text) {
      gaps.push(`${abbr} ${year}: no __prec${year === 2016 ? "16" : "20"} file`);
      return { year, rows: null };
    }
    const parsed = parsePrecinctCall(text);
    if (parsed.rows.length !== geometry.rows.length) {
      gaps.push(`${abbr} ${year}: ${parsed.rows.length} rows, 2024 has ${geometry.rows.length}`);
      return { year, rows: null };
    }
    return { year, rows: parsed.rows };
  });

  const features: PrecinctFeature[] = [];
  geometry.rows.forEach((row, ordinal) => {
    const county = String(row[0] ?? "");
    const precinct = String(row[1] ?? "");
    const shape = multiPolygon(row[row.length - 1], SCALE);
    const coordinates = shape?.coordinates ?? [];
    const point = centroid(coordinates);
    const votes: PrecinctFeature["votes"] = {};
    const current = votesOf(row, true);
    votes[2024] = current;
    if (!current && row.length >= 5) gaps.push(`${abbr}:${ordinal} 2024 votes are not a non-negative triple`);
    for (const side of older) {
      if (!side.rows) {
        votes[side.year] = null;
        continue;
      }
      const aligned = side.rows[ordinal] ?? [];
      if (String(aligned[0] ?? "") !== county || String(aligned[1] ?? "") !== precinct) {
        gaps.push(`${abbr}:${ordinal} ${side.year} is not row-aligned (${aligned[0]}|${aligned[1]})`);
        votes[side.year] = null;
        continue;
      }
      votes[side.year] = votesOf(aligned, false);
    }
    features.push({
      id: `${abbr}:${ordinal}`,
      ordinal,
      county,
      name: precinct,
      lon: point.lon,
      lat: point.lat,
      coordinates,
      votes,
    });
  });
  return { abbr, name: geometry.state, features, gaps };
}

export function precinctStateNames(root: string): string[] {
  const dir = join(root, "v2/data/precincts2024");
  return readdirSync(dir)
    .filter((file) => file.endsWith(".js"))
    .map((file) => file.slice(0, -3).replaceAll("_", " "))
    .filter((name) => stateAbbr(name))
    .sort();
}
