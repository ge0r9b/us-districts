import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type pg from "pg";
import { applyResults, refreshAggregates, sha256Hex, type ApplyReport } from "./apply.ts";
import { loadBoundaries, type BoundaryReport } from "./boundaries.ts";
import { BUDGET_BYTES, EST_RESULT_BYTES, EST_UNIT_BYTES, estimateRowsFromGzip, fitsBudget, formatMb } from "./budget.ts";
import { companyEstimateBytes, loadCompanies, type CompanyLoadReport } from "./companies.ts";
import { missingResultHeaders, parseCsv, readFileText } from "./csv.ts";
import { countyPresRows, ds2016Rows, readLegacy, uscdResultRows, type LegacyContext } from "./legacy.ts";
import { ensureUnits, unitsFromGeoCsv, unitsFromResultRows } from "./units.ts";
import type { RawResult } from "./validate.ts";

export function repoRoot(): string {
  return fileURLToPath(new URL("../..", import.meta.url));
}

export type LoadOptions = {
  /** Defaults to core only, so tests stay on the alpha.1 files. The db:load script passes the rest. */
  include?: string[];
  allowOverBudget?: string[];
};

export type SizeEstimate = {
  group: string;
  bytes: number;
  action: string;
};

export type LoadSummary = {
  boundaries: BoundaryReport | null;
  results: ApplyReport[];
  companies: CompanyLoadReport | null;
  gaps: string[];
  estimates: SizeEstimate[];
  databaseBytes: number;
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

const DISTRICT_FILES = [
  "data-v3/results/2022/senate/us_senate_2022_sldu.csv",
  "data-v3/results/2022/senate/us_senate_2022_sldl.csv",
  "data-v3/results/2024/senate/us_senate_2024_sldu.csv",
  "data-v3/results/2024/senate/us_senate_2024_sldl.csv",
];

const SCHOOL_FILES = [
  "data-v3/results/2022/senate/us_senate_2022_school.csv.gz",
  "data-v3/results/2024/senate/us_senate_2024_school.csv.gz",
];

/** Left out of every load: negative all-others residuals trip the 0.5% hard reject. */
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

const HELD: { id: string; bytes: number; detail: string }[] = [
  {
    id: "institutions",
    bytes: 120 * 1024 * 1024,
    detail: "data/inst-* entities and crosswalks are about 120 MB in Postgres, and the column map is not reviewed",
  },
  {
    id: "governments",
    bytes: 40 * 1024 * 1024,
    detail: "data/governments crosswalks are about 40 MB in Postgres, and the column map is not reviewed",
  },
  {
    id: "seating",
    bytes: 30 * 1024 * 1024,
    detail: "officeholder files on data/inst-officeholders are about 30 MB in Postgres, and the column map is not reviewed",
  },
  {
    id: "people",
    bytes: 20 * 1024 * 1024,
    detail: "data/people is about 20 MB in Postgres, and the column map is not reviewed",
  },
];

export function ensureDataCache(root = repoRoot()): { election: string; geo: string } {
  const dest = join(root, "v3/.cache");
  const election = join(dest, "election");
  const geo = join(dest, "geo");
  const marker = join(election, "data-v3/results/2024/senate/precincts/CT.csv.gz");
  const geoMarker = join(geo, "data-v3/geo/senate.csv");
  if (existsSync(marker) && existsSync(geoMarker) && existsSync(join(geo, "data-v3/geo/schools.csv"))) {
    return { election, geo };
  }
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
  return extractArchives(root, election, geo);
}

function extractArchives(root: string, election: string, geo: string): { election: string; geo: string } {
  const electionTar = execFileSync(
    "git",
    [
      "archive",
      "origin/data/election",
      "data-v3/results/2016",
      "data-v3/results/PA",
      "data-v3/results/2022/senate",
      "data-v3/results/2024/senate",
    ],
    { cwd: root, encoding: "buffer", maxBuffer: 64 * 1024 * 1024 },
  );
  mkdirSync(election, { recursive: true });
  execFileSync("tar", ["-x", "-C", election], { input: electionTar });
  const geoTar = execFileSync(
    "git",
    [
      "archive",
      "origin/data/geo",
      "data-v3/geo/counties.csv",
      "data-v3/geo/ushouse.csv",
      "data-v3/geo/senate.csv",
      "data-v3/geo/statehouse.csv",
      "data-v3/geo/schools.csv",
    ],
    { cwd: root, encoding: "buffer", maxBuffer: 32 * 1024 * 1024 },
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

async function fipsByAbbr(pool: pg.Pool): Promise<Map<string, string>> {
  const r = await pool.query<{ abbr: string; fips: string }>(
    `select btrim(u.state_abbr) abbr, btrim(u.state_fips) fips
     from unit u join boundary_set b on b.id = u.boundary_set_id
     where b.slug = 'v2-2024' and u.unit_type = 'state' and u.state_fips is not null`,
  );
  return new Map(r.rows.map((row) => [row.abbr, row.fips]));
}

function toRaw(rows: Record<string, string>[]): RawResult[] {
  return rows.map((row, i) => ({
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
}

export async function databaseBytes(pool: pg.Pool): Promise<number> {
  const r = await pool.query<{ n: string }>("select pg_database_size(current_database())::text n");
  return Number(r.rows[0]?.n ?? 0);
}

/** One election file. A known sha (applied or rejected) returns skipped without rewriting facts. */
export async function loadElectionFile(
  pool: pg.Pool,
  path: string,
  opts: { fileName?: string; gitCommit?: string | null; unitsFromRows?: boolean; refreshAggregates?: boolean } = {},
): Promise<ApplyReport> {
  const fileName = opts.fileName ?? path;
  const { text, bytes } = readFileText(path);
  const sha = sha256Hex(bytes);
  const existing = await pool.query<{ status: string }>(`select status from load_batch where file_sha256 = $1`, [sha]);
  if (existing.rows[0]?.status === "applied" || existing.rows[0]?.status === "rejected") {
    return { fileName, status: "skipped", rows: 0, rejected: 0, changed: 0, rejects: [] };
  }
  const parsed = parseCsv(text);
  const missing = missingResultHeaders(parsed.headers);
  if (missing.length > 0) {
    return {
      fileName,
      status: "rejected",
      rows: 0,
      rejected: 1,
      changed: 0,
      rejects: [{ lineNo: 1, rule: "headers", detail: missing.join(",") }],
    };
  }
  const rows = toRaw(parsed.rows);
  if (opts.unitsFromRows) {
    await ensureUnits(pool, unitsFromResultRows(rows, await fipsByAbbr(pool)));
  }
  return applyResults(
    pool,
    { fileName, sha256: sha, gitCommit: opts.gitCommit ?? null },
    rows,
    { refreshAggregates: opts.refreshAggregates },
  );
}

function precinctPaths(election: string): string[] {
  const out: string[] = [];
  for (const year of ["2022", "2024"]) {
    const dir = join(election, "data-v3/results", year, "senate", "precincts");
    if (!existsSync(dir)) continue;
    for (const name of readdirSync(dir)) {
      if (name.endsWith(".csv") || name.endsWith(".csv.gz")) out.push(join(dir, name));
    }
  }
  return out.sort();
}

function precinctEstimate(paths: string[]): { rows: number; bytes: number } {
  let compressed = 0;
  for (const path of paths) compressed += statSync(path).size;
  const rows = estimateRowsFromGzip(compressed);
  return { rows, bytes: rows * EST_RESULT_BYTES + Math.ceil(rows / 4) * EST_UNIT_BYTES };
}

export async function loadAll(pool: pg.Pool, root = repoRoot(), options: LoadOptions = {}): Promise<LoadSummary> {
  const include = new Set(options.include ?? ["core"]);
  const allow = new Set(options.allowOverBudget ?? []);
  const cache = ensureDataCache(root);
  const gaps: string[] = DEFERRED_FILES.map(([file, why]) => `${file}: not loaded (${why})`);
  const results: ApplyReport[] = [];
  const estimates: SizeEstimate[] = [];
  let boundaries: BoundaryReport | null = null;
  let companies: CompanyLoadReport | null = null;
  let changed = false;

  if (include.has("core")) {
    const v2 = join(root, "v2/data");
    boundaries = await loadBoundaries(pool, {
      countiesCsv: join(cache.geo, "data-v3/geo/counties.csv"),
      ushouseCsv: join(cache.geo, "data-v3/geo/ushouse.csv"),
      usstatesJs: join(v2, "usstates.js"),
      uscountiesJs: join(v2, "uscounties.js"),
      uscdJs: join(v2, "uscd.js"),
      statesGeojson: join(root, "v3/app/public/geo/states.geojson"),
    });
    gaps.push(...boundaries.gaps);
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
      const report = await applyResults(
        pool,
        { fileName: `v2/data/${job.file}`, sha256: sha256Hex(source), gitCommit: meta.sha },
        rows,
        { refreshAggregates: false },
      );
      if (report.changed > 0) changed = true;
      results.push(report);
    }
    let electionCommit = "";
    try {
      electionCommit = execFileSync("git", ["rev-parse", "origin/data/election"], { cwd: root, encoding: "utf8" }).trim();
    } catch {
      electionCommit = "";
    }
    for (const rel of ELECTION_FILES) {
      const report = await loadElectionFile(pool, join(cache.election, rel), {
        fileName: rel,
        gitCommit: electionCommit,
        refreshAggregates: false,
      });
      if (report.changed > 0) changed = true;
      results.push(report);
    }
  }

  if (include.has("districts") || include.has("schools")) {
    const geoJobs: [string, readonly string[]][] = [];
    if (include.has("districts")) {
      geoJobs.push(["data-v3/geo/senate.csv", ["sldu"]], ["data-v3/geo/statehouse.csv", ["sldl"]]);
    }
    if (include.has("schools")) geoJobs.push(["data-v3/geo/schools.csv", ["unsd", "elsd", "scsd"]]);
    for (const [rel, tigerSets] of geoJobs) {
      const built = unitsFromGeoCsv(readFileText(join(cache.geo, rel)).text, tigerSets);
      gaps.push(...built.gaps.slice(0, 20));
      const bytes = built.units.length * EST_UNIT_BYTES;
      estimates.push({ group: rel, bytes, action: "load units" });
      await ensureUnits(pool, built.units);
    }
    const files = [
      ...(include.has("districts") ? DISTRICT_FILES : []),
      ...(include.has("schools") ? SCHOOL_FILES : []),
    ];
    for (const rel of files) {
      const report = await loadElectionFile(pool, join(cache.election, rel), {
        fileName: rel,
        refreshAggregates: false,
      });
      if (report.changed > 0) changed = true;
      if (report.status === "rejected") {
        gaps.push(`${rel}: rejected ${report.rejected} rows (${report.rejects[0]?.rule ?? "rule"}); facts were not written`);
      }
      results.push(report);
    }
  }

  const precincts = precinctPaths(cache.election);
  const precinctSize = precinctEstimate(precincts);
  if (include.has("precincts")) {
    const current = await databaseBytes(pool);
    if (!fitsBudget(current, precinctSize.bytes) && !allow.has("precincts")) {
      estimates.push({ group: "precincts", bytes: precinctSize.bytes, action: "skipped, over budget" });
      gaps.push(
        `precincts: ${precincts.length} files, about ${precinctSize.rows} rows, estimated ${formatMb(precinctSize.bytes)} on top of ${formatMb(current)} would pass ${formatMb(BUDGET_BYTES)}. No precinct polygons are in data/geo, so this load is results plus unit keys only. Not loaded. Re-run with: npm run db:load -- --allow-over-budget=precincts`,
      );
    } else {
      estimates.push({ group: "precincts", bytes: precinctSize.bytes, action: "load" });
      for (const path of precincts) {
        const rel = path.slice(cache.election.length + 1);
        const report = await loadElectionFile(pool, path, {
          fileName: rel,
          unitsFromRows: true,
          refreshAggregates: false,
        });
        if (report.changed > 0) changed = true;
        if (report.status === "rejected") {
          gaps.push(`${rel}: rejected ${report.rejected} rows (${report.rejects[0]?.rule ?? "rule"})`);
        }
        results.push(report);
      }
    }
  } else {
    estimates.push({
      group: "precincts",
      bytes: precinctSize.bytes,
      action: "not requested",
    });
  }

  const companyBytes = companyEstimateBytes();
  if (include.has("companies")) {
    const current = await databaseBytes(pool);
    companies = await loadCompanies(pool, {
      root,
      currentBytes: current,
      allow: allow.has("companies"),
      tilesPath: join(root, "v3/app/public/tiles/companies.pmtiles"),
    });
    estimates.push({
      group: "companies",
      bytes: companyBytes,
      action: companies.status === "applied" ? "load" : "tiles only",
    });
    if (companies.gap) gaps.push(companies.gap);
  } else {
    estimates.push({
      group: "companies",
      bytes: companyBytes,
      action: "not requested (npm run db:load -- --include=companies)",
    });
  }

  const currentForHeld = await databaseBytes(pool);
  for (const held of HELD) {
    const over = !fitsBudget(currentForHeld, held.bytes);
    if (!include.has(held.id)) {
      estimates.push({ group: held.id, bytes: held.bytes, action: "not requested" });
      continue;
    }
    estimates.push({ group: held.id, bytes: held.bytes, action: "refused" });
    const budget = over
      ? ` Estimated ${formatMb(held.bytes)} on top of ${formatMb(currentForHeld)} would pass ${formatMb(BUDGET_BYTES)}.`
      : "";
    const override = allow.has(held.id) ? " --allow-over-budget was set, and" : "";
    gaps.push(`${held.id}:${override} ${held.detail}.${budget} Rows were not inserted.`);
  }

  if (changed) await refreshAggregates(pool);
  return { boundaries, results, companies, gaps, estimates, databaseBytes: await databaseBytes(pool) };
}
