import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type pg from "pg";
import { applyResults, refreshAggregates, sha256Hex, type ApplyReport } from "./apply.ts";
import { fetchOrigin, needsRefresh, originCommit, stampCommit } from "./branch-cache.ts";
import { loadBoundaries, type BoundaryReport } from "./boundaries.ts";
import { loadCompanies, type CompanyLoadReport } from "./companies.ts";
import { loadInstitutions, type InstitutionLoadReport } from "./inst-entities.ts";
import { assignLocationUnits, type LocationAssignReport } from "./locations.ts";
import { missingResultHeaders, parseCsv, readFileText } from "./csv.ts";
import {
  countyPresOverlay,
  countyPresRows,
  dcUshouseRows,
  ds2016Rows,
  readLegacy,
  rowsFromVoteMap,
  statePresTotals,
  uscdResultRows,
  type LegacyContext,
} from "./legacy.ts";
import { ensureUnits, unitsFromGeoCsv } from "./units.ts";
import { formatRejectRules, type RawResult } from "./validate.ts";

export function repoRoot(): string {
  return fileURLToPath(new URL("../..", import.meta.url));
}

export type LoadOptions = {
  /** Defaults to core only, so tests stay on the alpha.1 files. The db:load script passes the rest. */
  include?: string[];
  allowOverBudget?: string[];
  /** Price institutions and write nothing. Locations are not assigned. */
  dryRun?: boolean;
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
  institutions: InstitutionLoadReport | null;
  institutionsForeign: InstitutionLoadReport | null;
  locations: LocationAssignReport | null;
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

/** State legislative districts plus US House. The two ushouse files are clean at data/election 0e058f7 (1,023 rows each). */
export const DISTRICT_FILES = [
  "data-v3/results/2022/senate/us_senate_2022_sldu.csv",
  "data-v3/results/2022/senate/us_senate_2022_sldl.csv",
  "data-v3/results/2022/senate/us_senate_2022_ushouse.csv",
  "data-v3/results/2024/senate/us_senate_2024_sldu.csv",
  "data-v3/results/2024/senate/us_senate_2024_sldl.csv",
  "data-v3/results/2024/senate/us_senate_2024_ushouse.csv",
];

const SCHOOL_FILES = [
  "data-v3/results/2022/senate/us_senate_2022_school.csv.gz",
  "data-v3/results/2024/senate/us_senate_2024_school.csv.gz",
];

const HELD: { id: string; detail: string }[] = [
  {
    id: "governments",
    detail: "data/governments crosswalks are not loaded, and the column map is not reviewed",
  },
  {
    id: "seating",
    detail: "officeholder files on data/inst-officeholders are not loaded, and the column map is not reviewed",
  },
  {
    id: "people",
    detail: "data/people is not loaded, and the column map is not reviewed",
  },
];

export type DataCache = {
  election: string;
  geo: string;
  electionCommit: string;
  geoCommit: string;
};

const ELECTION_MARKERS = [
  "data-v3/results/2024/senate/precincts/CT.csv.gz",
  "data-v3/results/2024/senate/us_senate_2024_ushouse.csv",
  "data-v3/results/2022/senate/us_senate_2022_ushouse.csv",
];

const GEO_MARKERS = ["data-v3/geo/senate.csv", "data-v3/geo/schools.csv", "data-v3/geo/ushouse.csv"];

/** Refill a data-branch cache when origin's commit differs from the stamped one. */
export function ensureDataCache(root = repoRoot()): DataCache {
  const dest = join(root, "v3/.cache");
  const election = join(dest, "election");
  const geo = join(dest, "geo");
  fetchOrigin(root, ["data/election", "data/geo"]);
  const electionCommit = originCommit(root, "data/election");
  const geoCommit = originCommit(root, "data/geo");
  if (needsRefresh(election, electionCommit, ELECTION_MARKERS)) {
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
    stampCommit(election, electionCommit);
  }
  if (needsRefresh(geo, geoCommit, GEO_MARKERS)) {
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
    stampCommit(geo, geoCommit);
  }
  return { election, geo, electionCommit, geoCommit };
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

const emptyReport = (fileName: string, status: ApplyReport["status"]): ApplyReport => ({
  fileName,
  status,
  rows: 0,
  rejected: 0,
  changed: 0,
  rejects: [],
  rejectRules: {},
  examples: [],
});

async function storedRejects(pool: pg.Pool, sha: string): Promise<Pick<ApplyReport, "rejected" | "rejectRules" | "examples">> {
  const rules = await pool.query<{ rule: string; n: number }>(
    `select s.rule, count(*)::int n
     from stg_reject s join load_batch b on b.id = s.load_batch_id
     where b.file_sha256 = $1
     group by s.rule`,
    [sha],
  );
  const examples = await pool.query<{ line_no: number; detail: string }>(
    `select s.line_no, s.detail
     from stg_reject s join load_batch b on b.id = s.load_batch_id
     where b.file_sha256 = $1 and s.rule = 'R03_votes'
     order by s.line_no
     limit 3`,
    [sha],
  );
  const rejectRules: Record<string, number> = {};
  let rejected = 0;
  for (const row of rules.rows) {
    rejectRules[row.rule] = row.n;
    rejected += row.n;
  }
  return {
    rejected,
    rejectRules,
    examples: examples.rows.map((row) => ({ lineNo: row.line_no, detail: row.detail })),
  };
}

/** One election file. A known sha (applied or rejected) returns skipped without rewriting facts. */
export async function loadElectionFile(
  pool: pg.Pool,
  path: string,
  opts: { fileName?: string; gitCommit?: string | null; refreshAggregates?: boolean } = {},
): Promise<ApplyReport> {
  const fileName = opts.fileName ?? path;
  if (path.includes("/precincts/") || path.includes("\\precincts\\")) {
    return emptyReport(fileName, "skipped");
  }
  const { text, bytes } = readFileText(path);
  const sha = sha256Hex(bytes);
  const existing = await pool.query<{ status: string }>(`select status from load_batch where file_sha256 = $1`, [sha]);
  if (existing.rows[0]?.status === "applied" || existing.rows[0]?.status === "rejected") {
    if (opts.gitCommit) {
      await pool.query(
        `update load_batch set git_commit = $2 where file_sha256 = $1 and git_commit is distinct from $2`,
        [sha, opts.gitCommit],
      );
    }
    const prior = await storedRejects(pool, sha);
    return { ...emptyReport(fileName, "skipped"), ...prior };
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
      rejectRules: { headers: 1 },
      examples: [],
    };
  }
  const rows = toRaw(parsed.rows);
  return applyResults(
    pool,
    { fileName, sha256: sha, gitCommit: opts.gitCommit ?? null },
    rows,
    { refreshAggregates: opts.refreshAggregates },
  );
}

function resultGap(report: ApplyReport): string | null {
  if (report.rejected <= 0) return null;
  const why = formatRejectRules(report.rejectRules, report.examples);
  if (report.status === "applied") {
    return `${report.fileName}: applied, ${report.rejected} rows not loaded (${why}).`;
  }
  return `${report.fileName}: rejected ${report.rejected} rows (${why}). Facts were not written.`;
}

export async function loadAll(pool: pg.Pool, root = repoRoot(), options: LoadOptions = {}): Promise<LoadSummary> {
  const include = new Set(options.include ?? ["core"]);
  const allow = new Set(options.allowOverBudget ?? []);
  if (options.dryRun) {
    const current = await databaseBytes(pool);
    const gaps: string[] = [];
    const estimates: SizeEstimate[] = [];
    let institutions: InstitutionLoadReport | null = null;
    let institutionsForeign: InstitutionLoadReport | null = null;
    if (include.has("institutions")) {
      institutions = await loadInstitutions(pool, {
        root,
        currentBytes: current,
        allow: allow.has("institutions"),
        dryRun: true,
        scope: "domestic",
      });
      estimates.push({
        group: "institutions",
        bytes: institutions.estimate.projectedBytes ?? 0,
        action: `${institutions.status}; slim row width, nothing written`,
      });
      if (institutions.gap) gaps.push(institutions.gap);
    }
    if (include.has("institutions-foreign")) {
      institutionsForeign = await loadInstitutions(pool, {
        root,
        currentBytes: current,
        allow: allow.has("institutions-foreign"),
        dryRun: true,
        scope: "foreign",
      });
      estimates.push({
        group: "institutions-foreign",
        bytes: institutionsForeign.estimate.projectedBytes ?? 0,
        action: `${institutionsForeign.status}; FR/DE/GB governments, nothing written`,
      });
      if (institutionsForeign.gap) gaps.push(institutionsForeign.gap);
    }
    if (!institutions && !institutionsForeign) {
      gaps.push("dry-run writes nothing. Pass --include=institutions to price that load.");
    }
    return {
      boundaries: null,
      results: [],
      companies: null,
      institutions,
      institutionsForeign,
      locations: null,
      gaps,
      estimates,
      databaseBytes: current,
    };
  }
  const cache = ensureDataCache(root);
  const gaps: string[] = [];
  const results: ApplyReport[] = [];
  const estimates: SizeEstimate[] = [];
  let boundaries: BoundaryReport | null = null;
  let companies: CompanyLoadReport | null = null;
  let institutions: InstitutionLoadReport | null = null;
  let institutionsForeign: InstitutionLoadReport | null = null;
  let locations: LocationAssignReport | null = null;
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
      gitCommit: cache.geoCommit,
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
      const gap = resultGap(report);
      if (gap) gaps.push(gap);
      results.push(report);
    }
    // 2020/2024 county files omit Alaska and DC. A new batch sha (not the raw
    // election file hash) so an already-applied election*.js does not skip these rows.
    const akPath = join(v2, "ak.js");
    const dcPath = join(v2, "dc.js");
    const akSource = readLegacy(akPath);
    const dcSource = readLegacy(dcPath);
    const akMeta = gitFileTime(root, akPath);
    const dcMeta = gitFileTime(root, dcPath);
    const applyExtra = async (
      fileName: string,
      shaBody: string,
      meta: { sha: string; iso: string },
      sourceFile: string,
      unitType: "county" | "state" | "ushouse",
      build: (ctx: LegacyContext) => RawResult[],
    ) => {
      const ctx: LegacyContext = {
        fileName,
        sourceUrl: `https://github.com/ge0r9b/us-districts/blob/${meta.sha}/v2/data/${sourceFile}`,
        retrievedAt: meta.iso,
        unitIdByLegacy: unitType === "state" ? stateLegacy : unitType === "ushouse" ? cdLegacy : countyLegacy,
        gaps,
      };
      const report = await applyResults(
        pool,
        { fileName, sha256: sha256Hex(shaBody), gitCommit: meta.sha },
        build(ctx),
        { refreshAggregates: false },
      );
      if (report.changed > 0) changed = true;
      const gap = resultGap(report);
      if (gap) gaps.push(gap);
      results.push(report);
    };
    for (const year of [2020, 2024] as const) {
      const electionFile = `election${year}.js`;
      const electionPath = join(v2, electionFile);
      const electionSource = readLegacy(electionPath);
      const electionMeta = gitFileTime(root, electionPath);
      await applyExtra(
        `v2/data/${electionFile}#ak-dc`,
        `ak-dc:${year}\n${akSource}\n${dcSource}`,
        akMeta,
        "ak.js",
        "county",
        (ctx) =>
          rowsFromVoteMap(ctx, {
            triples: countyPresOverlay(year, akSource, dcSource),
            unitType: "county",
            year,
            stateName: (key) => key.split("|")[0] ?? "",
          }),
      );
      await applyExtra(
        `v2/data/${electionFile}#states`,
        `states:${year}\n${electionSource}\n${akSource}\n${dcSource}`,
        electionMeta,
        electionFile,
        "state",
        (ctx) =>
          rowsFromVoteMap(ctx, {
            triples: statePresTotals(electionSource, year, akSource, dcSource),
            unitType: "state",
            year,
            stateName: (key) => key,
          }),
      );
    }
    await applyExtra(
      "v2/data/dc.js#ushouse",
      `ushouse\n${dcSource}`,
      dcMeta,
      "dc.js",
      "ushouse",
      (ctx) => dcUshouseRows(dcSource, ctx),
    );
    for (const rel of ELECTION_FILES) {
      const report = await loadElectionFile(pool, join(cache.election, rel), {
        fileName: rel,
        gitCommit: cache.electionCommit,
        refreshAggregates: false,
      });
      if (report.changed > 0) changed = true;
      const gap = resultGap(report);
      if (gap) gaps.push(gap);
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
      estimates.push({ group: rel, bytes: 0, action: "units loaded; budget is pg_database_size" });
      await ensureUnits(pool, built.units);
    }
    const files = [
      ...(include.has("districts") ? DISTRICT_FILES : []),
      ...(include.has("schools") ? SCHOOL_FILES : []),
    ];
    for (const rel of files) {
      const report = await loadElectionFile(pool, join(cache.election, rel), {
        fileName: rel,
        gitCommit: cache.electionCommit,
        refreshAggregates: false,
      });
      if (report.changed > 0) changed = true;
      const gap = resultGap(report);
      if (gap) gaps.push(gap);
      results.push(report);
    }
  }

  if (include.has("precincts")) {
    estimates.push({ group: "precincts", bytes: 0, action: "packs and PMTiles, not Postgres" });
    gaps.push(
      "precincts: kept out of Postgres. Geometry is PMTiles and results are content-hashed packs keyed by precinct id. The database stores precinct_rollup only, not precinct units or unit_crosswalk. Run: npm run precincts",
    );
  } else {
    estimates.push({ group: "precincts", bytes: 0, action: "not requested (npm run precincts)" });
  }

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
      bytes: current,
      action: `${companies.status}; budget is pg_database_size`,
    });
    if (companies.gap) gaps.push(companies.gap);
  } else {
    estimates.push({
      group: "companies",
      bytes: 0,
      action: "not requested (npm run db:load -- --include=companies)",
    });
  }

  for (const held of HELD) {
    if (!include.has(held.id)) {
      estimates.push({ group: held.id, bytes: 0, action: "not requested" });
      continue;
    }
    estimates.push({ group: held.id, bytes: 0, action: "refused" });
    const override = allow.has(held.id) ? " --allow-over-budget was set, and" : "";
    gaps.push(`${held.id}:${override} ${held.detail}. Rows were not inserted.`);
  }

  locations = await assignLocationUnits(pool);
  if (locations.outside > 0) {
    gaps.push(
      `locations: ${locations.outside} US points fall outside every county, state, and US House unit (flag no_unit_resolved). ${locations.skippedNonUs} non-US points were left unit-less.`,
    );
  }

  if (include.has("institutions")) {
    const current = await databaseBytes(pool);
    institutions = await loadInstitutions(pool, {
      root,
      currentBytes: current,
      allow: allow.has("institutions"),
      scope: "domestic",
    });
    estimates.push({
      group: "institutions",
      bytes: institutions.estimate.projectedBytes ?? institutions.estimate.fileBytes,
      action: `${institutions.status}; slim row width, after locations`,
    });
    if (institutions.gap) gaps.push(institutions.gap);
  } else {
    estimates.push({
      group: "institutions",
      bytes: 0,
      action: "not requested (npm run db:load -- --include=institutions)",
    });
  }

  if (include.has("institutions-foreign")) {
    const current = await databaseBytes(pool);
    institutionsForeign = await loadInstitutions(pool, {
      root,
      currentBytes: current,
      allow: allow.has("institutions-foreign"),
      scope: "foreign",
    });
    estimates.push({
      group: "institutions-foreign",
      bytes: institutionsForeign.estimate.projectedBytes ?? institutionsForeign.estimate.fileBytes,
      action: `${institutionsForeign.status}; FR/DE/GB governments, after domestic institutions`,
    });
    if (institutionsForeign.gap) gaps.push(institutionsForeign.gap);
  } else {
    estimates.push({
      group: "institutions-foreign",
      bytes: 0,
      action: "not requested (npm run db:load -- --include=institutions-foreign)",
    });
  }

  if (changed) await refreshAggregates(pool);
  return {
    boundaries,
    results,
    companies,
    institutions,
    institutionsForeign,
    locations,
    gaps,
    estimates,
    databaseBytes: await databaseBytes(pool),
  };
}
