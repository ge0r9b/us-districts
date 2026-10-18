import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type pg from "pg";
import { applyResults, sha256Hex, type ApplyReport } from "./apply.ts";
import { loadBoundaries, type BoundaryReport } from "./boundaries.ts";
import { missingResultHeaders, parseCsv } from "./csv.ts";
import { countyPresRows, ds2016Rows, readLegacy, uscdResultRows, type LegacyContext } from "./legacy.ts";
import type { RawResult } from "./validate.ts";

export function repoRoot(): string {
  return fileURLToPath(new URL("../..", import.meta.url));
}

export type LoadSummary = {
  boundaries: BoundaryReport;
  results: ApplyReport[];
  gaps: string[];
};

const ELECTION_FILES = [
  "data-v3/results/2016/us_president_2016_state_fec.csv",
  "data-v3/results/PA/pa_president_county_official_2016.csv",
  "data-v3/results/PA/pa_president_county_official.csv",
  "data-v3/results/2022/senate/us_senate_2022_state.csv",
  "data-v3/results/2022/senate/us_senate_2022_county.csv",
  "data-v3/results/2024/senate/us_senate_2024_state.csv",
  "data-v3/results/2024/senate/us_senate_2024_county.csv",
];

/** Left out of the default load: negative all-others residuals trip the 0.5% hard reject. */
const DEFERRED_FILES: [string, string][] = [
  [
    "data-v3/results/2022/senate/us_senate_2022_ushouse.csv",
    "54 negative all-others votes (above the 0.5% reject rate)",
  ],
  [
    "data-v3/results/2024/senate/us_senate_2024_ushouse.csv",
    "42 negative all-others votes (above the 0.5% reject rate)",
  ],
];

export function ensureDataCache(root = repoRoot()): { election: string; geo: string } {
  const dest = join(root, "v3/.cache");
  const election = join(dest, "election");
  const geo = join(dest, "geo");
  const marker = join(election, "data-v3/results/2024/senate/us_senate_2024_state.csv");
  const geoMarker = join(geo, "data-v3/geo/counties.csv");
  if (existsSync(marker) && existsSync(geoMarker)) return { election, geo };
  mkdirSync(dest, { recursive: true });
  try {
    execFileSync("git", ["fetch", "--no-tags", "origin", "data/election", "data/geo"], {
      cwd: root,
      stdio: "pipe",
      timeout: 120_000,
    });
  } catch {
    // The refs may already be on disk from an earlier fetch.
  }
  return extractArchives(root, dest, election, geo);
}

function extractArchives(root: string, dest: string, election: string, geo: string): { election: string; geo: string } {
  const electionTar = execFileSync("git", ["archive", "origin/data/election", ...ELECTION_FILES], {
    cwd: root,
    encoding: "buffer",
    maxBuffer: 64 * 1024 * 1024,
  });
  mkdirSync(election, { recursive: true });
  execFileSync("tar", ["-x", "-C", election], { input: electionTar });
  const geoTar = execFileSync(
    "git",
    ["archive", "origin/data/geo", "data-v3/geo/counties.csv", "data-v3/geo/ushouse.csv"],
    { cwd: root, encoding: "buffer", maxBuffer: 16 * 1024 * 1024 },
  );
  mkdirSync(geo, { recursive: true });
  execFileSync("tar", ["-x", "-C", geo], { input: geoTar });
  return { election, geo };
}

function gitFileTime(root: string, path: string): { sha: string; iso: string } {
  const sha = execFileSync("git", ["log", "-1", "--format=%H", "--", path], { cwd: root, encoding: "utf8" }).trim();
  const iso = execFileSync("git", ["log", "-1", "--format=%cI", "--", path], { cwd: root, encoding: "utf8" }).trim();
  return { sha, iso: iso || "2026-10-18T00:00:00Z" };
}

async function legacyMap(pool: pg.Pool, unitType: string): Promise<Map<string, string>> {
  const r = await pool.query<{ legacy_key: string; unit_key: string }>(
    `select u.legacy_key, u.unit_key
     from unit u join boundary_set b on b.id = u.boundary_set_id
     where b.slug = 'v2-2024' and u.unit_type = $1 and u.legacy_key is not null`,
    [unitType],
  );
  return new Map(r.rows.map((row) => [row.legacy_key, row.unit_key]));
}

function csvRows(path: string): { rows: RawResult[]; skipped: string | null } {
  const text = readFileSync(path, "utf8");
  const parsed = parseCsv(text);
  const missing = missingResultHeaders(parsed.headers);
  if (missing.length > 0) return { rows: [], skipped: `missing ${missing.join(",")}` };
  const rows: RawResult[] = parsed.rows.map((row, i) => ({
    lineNo: i + 2,
    state: row.state ?? "",
    year: row.year ?? "",
    office: row.office ?? "",
    district: row.district ?? "",
    unitId: row.unit_id ?? "",
    unitType: row.unit_type ?? "",
    candidateId: row.candidate_id ?? "",
    answer: row.answer ?? "",
    party: row.party ?? "",
    votes: row.votes ?? "",
    weight: row.weight ?? "",
    sourceUrl: row.source_url ?? "",
    retrievedAt: row.retrieved_at ?? "",
    method: row.method ?? "",
    boundarySet: row.boundary_set ?? "",
  }));
  return { rows, skipped: null };
}

export async function loadAll(pool: pg.Pool, root = repoRoot()): Promise<LoadSummary> {
  const cache = ensureDataCache(root);
  const v2 = join(root, "v2/data");
  const boundaries = await loadBoundaries(pool, {
    countiesCsv: join(cache.geo, "data-v3/geo/counties.csv"),
    ushouseCsv: join(cache.geo, "data-v3/geo/ushouse.csv"),
    usstatesJs: join(v2, "usstates.js"),
    uscountiesJs: join(v2, "uscounties.js"),
    uscdJs: join(v2, "uscd.js"),
    statesGeojson: join(root, "v3/app/public/geo/states.geojson"),
  });

  const gaps = [
    ...boundaries.gaps,
    ...DEFERRED_FILES.map(([file, why]) => `${file}: not loaded (${why})`),
  ];
  const results: ApplyReport[] = [];
  const countyLegacy = await legacyMap(pool, "county");
  const stateLegacy = await legacyMap(pool, "state");
  const cdLegacy = await legacyMap(pool, "ushouse");

  const v2Jobs: { file: string; build: (ctx: LegacyContext, source: string) => RawResult[] }[] = [
    { file: "election2016.js", build: (ctx, source) => countyPresRows(ctx.fileName, source, 2016, ctx) },
    { file: "election2020.js", build: (ctx, source) => countyPresRows(ctx.fileName, source, 2020, ctx) },
    { file: "election2024.js", build: (ctx, source) => countyPresRows(ctx.fileName, source, 2024, ctx) },
    { file: "ds2016-states.js", build: (ctx, source) => ds2016Rows(source, "state", ctx) },
    { file: "ds2016-cd.js", build: (ctx, source) => ds2016Rows(source, "ushouse", ctx) },
    { file: "uscd.js", build: (ctx, source) => uscdResultRows(source, ctx) },
  ];

  for (const job of v2Jobs) {
    const path = join(v2, job.file);
    const meta = gitFileTime(root, path);
    const source = readLegacy(path);
    const unitType = job.file.includes("states") ? "state" : job.file.includes("cd") || job.file === "uscd.js" ? "ushouse" : "county";
    const ctx: LegacyContext = {
      fileName: job.file,
      sourceUrl: `https://github.com/ge0r9b/us-districts/blob/${meta.sha}/v2/data/${job.file}`,
      retrievedAt: meta.iso,
      unitIdByLegacy: unitType === "state" ? stateLegacy : unitType === "ushouse" ? cdLegacy : countyLegacy,
      gaps,
    };
    const rows = job.build(ctx, source);
    results.push(
      await applyResults(pool, { fileName: `v2/data/${job.file}`, sha256: sha256Hex(source), gitCommit: meta.sha }, rows),
    );
  }

  let electionCommit = "";
  try {
    electionCommit = execFileSync("git", ["rev-parse", "origin/data/election"], { cwd: root, encoding: "utf8" }).trim();
  } catch {
    electionCommit = "";
  }
  for (const rel of ELECTION_FILES) {
    const path = join(cache.election, rel);
    const parsed = csvRows(path);
    if (parsed.skipped) {
      gaps.push(`${rel}: skipped (${parsed.skipped})`);
      continue;
    }
    results.push(
      await applyResults(
        pool,
        { fileName: rel, sha256: sha256Hex(readFileSync(path)), gitCommit: electionCommit },
        parsed.rows,
      ),
    );
  }
  return { boundaries, results, gaps };
}
