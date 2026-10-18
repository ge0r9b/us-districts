import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import type pg from "pg";
import { contestKey, estBit, stateName } from "@usd/core";
import { loadPrecinctState, precinctStateNames, type PrecinctFeature, type PrecinctState } from "./precinct-source.ts";
import { writePrecinctPmtiles } from "./precinct-tiles.ts";
import { catalogRowBytes } from "./row-width.ts";

export type PrecinctPack = {
  v: 3;
  state: string;
  year: number;
  office: "president";
  answers: ["dem_nominee", "rep_nominee", "other"];
  ids: string[];
  names: string[];
  votes: ([number, number, number] | null)[];
  total: (number | null)[];
  est: string;
};

export type PackIndex = Record<string, { sha: string; file: string }>;

const YEARS = [2016, 2020, 2024] as const;

export function packsRoot(repo: string): string {
  return join(repo, "v3/app/public/packs/precinct");
}

export function tilesPath(repo: string, abbr: string): string {
  return join(repo, "v3/app/public/tiles/precinct-2024", `${abbr}.pmtiles`);
}

export function buildPack(features: PrecinctFeature[], year: (typeof YEARS)[number], abbr: string): {
  pack: PrecinctPack;
  json: string;
  sha256: string;
} {
  const flags: boolean[] = [];
  const pack: PrecinctPack = {
    v: 3,
    state: abbr,
    year,
    office: "president",
    answers: ["dem_nominee", "rep_nominee", "other"],
    ids: [],
    names: [],
    votes: [],
    total: [],
    est: "",
  };
  for (const feature of features) {
    const vote = feature.votes[year] ?? null;
    pack.ids.push(feature.id);
    pack.names.push(feature.name);
    if (!vote) {
      pack.votes.push(null);
      pack.total.push(null);
      flags.push(false);
    } else {
      pack.votes.push([vote.d, vote.r, vote.other]);
      pack.total.push(vote.total);
      flags.push(vote.est);
    }
  }
  pack.est = encodeEst(flags);
  const json = JSON.stringify(pack);
  return { pack, json, sha256: createHash("sha256").update(json).digest("hex") };
}

export function encodeEst(flags: boolean[]): string {
  const bytes = Buffer.alloc(Math.ceil(flags.length / 8));
  flags.forEach((on, index) => {
    if (on) bytes[index >> 3] |= 1 << (index & 7);
  });
  return bytes.toString("base64");
}

export function estAt(est: string, index: number): boolean {
  return estBit(est, index);
}

export function writePack(repo: string, abbr: string, year: number, built: { json: string; sha256: string }): string {
  const rel = `${abbr}/${year}/president/${built.sha256.slice(0, 12)}.json`;
  const path = join(packsRoot(repo), rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, built.json);
  const indexPath = join(packsRoot(repo), "index.json");
  const index: PackIndex = existsSync(indexPath) ? (JSON.parse(readFileSync(indexPath, "utf8")) as PackIndex) : {};
  index[`${abbr}|${year}|president`] = { sha: built.sha256, file: rel };
  writeFileSync(indexPath, JSON.stringify(index));
  return `/packs/precinct/${rel}`;
}

export function locatePack(
  dir: string,
  state: string,
  year: number,
  office: string,
): { file: string; publicPath: string; sha: string } | null {
  const indexPath = join(dir, "index.json");
  if (!existsSync(indexPath)) return null;
  const index = JSON.parse(readFileSync(indexPath, "utf8")) as PackIndex;
  const hit = index[`${state.toUpperCase()}|${year}|${office}`];
  if (!hit || !existsSync(join(dir, hit.file))) return null;
  return { file: join(dir, hit.file), publicPath: `/packs/precinct/${hit.file}`, sha: hit.sha };
}

export async function buildPrecinctState(
  db: pg.Pool,
  repo: string,
  nameOrAbbr: string,
  opts: { tiles?: boolean } = {},
): Promise<{ abbr: string; features: number; gaps: string[] }> {
  const name = nameOrAbbr.length === 2 ? (stateName(nameOrAbbr) ?? nameOrAbbr) : nameOrAbbr;
  const state = loadPrecinctState(repo, name);
  for (const year of YEARS) writePack(repo, state.abbr, year, buildPack(state.features, year, state.abbr));
  if (opts.tiles !== false && state.features.some((feature) => feature.coordinates.length > 0)) {
    writePrecinctPmtiles(state.features, tilesPath(repo, state.abbr));
  }
  await storeRollup(db, state);
  return { abbr: state.abbr, features: state.features.length, gaps: state.gaps };
}

export type PrecinctGrowth = {
  states: number;
  /** Precinct feature ids. They stay in the pack and the PMTiles archive. */
  units: number;
  /** County and US House parents implied by each feature. Not stored as unit_crosswalk. */
  crosswalk: number;
  /** County and US House parents, times the three presidential years. This is the Postgres write. */
  rollup: number;
  databaseBytes: number;
  /** precinct_rollup only. Units and unit_crosswalk add nothing. */
  estimatedBytes: number | null;
  projectedBytes: number | null;
  parts: { table: string; rows: number; bytesPerRow: number | null; bytes: number | null }[];
  note: string;
};

/**
 * Count precinct features and price precinct_rollup. Writes nothing.
 * Units and unit_crosswalk are not a Postgres cost: feature ids stay in the pack and in PMTiles.
 */
export async function dryRunPrecincts(
  db: pg.Pool,
  repo: string,
  opts: { state?: string } = {},
): Promise<PrecinctGrowth> {
  const names = opts.state
    ? [opts.state.length === 2 ? (stateName(opts.state) ?? opts.state) : opts.state]
    : precinctStateNames(repo);
  let units = 0;
  const abbrs: string[] = [];
  for (const name of names) {
    const state = loadPrecinctState(repo, name);
    units += state.features.length;
    abbrs.push(state.abbr);
  }
  const parents = await db.query<{ n: string }>(
    `select count(*)::text n
     from unit u
     join boundary_set b on b.id = u.boundary_set_id
     where b.slug = 'v2-2024'
       and u.unit_type in ('county', 'ushouse')
       and btrim(u.state_abbr) = any($1::text[])`,
    [abbrs],
  );
  const crosswalk = units * 2;
  const rollup = Number(parents.rows[0]?.n ?? 0) * YEARS.length;
  const sized = await db.query<{ db: string; rollup_bytes: string; rollup_rows: string }>(
    `select pg_database_size(current_database())::text db,
            pg_total_relation_size('usd.precinct_rollup')::text rollup_bytes,
            (select count(*)::text from precinct_rollup) rollup_rows`,
  );
  const size = sized.rows[0];
  const liveRows = Number(size?.rollup_rows ?? 0);
  const rollupWidth =
    liveRows > 0
      ? Number(size?.rollup_bytes ?? 0) / liveRows
      : await catalogRowBytes(db, "usd.precinct_rollup", {
          textBytes: { contest_key: 28 },
          indexBytes: 48,
        });
  const rollupBytes = Math.round(rollup * rollupWidth);
  const parts = [
    { table: "unit", rows: units, bytesPerRow: 0, bytes: 0 },
    { table: "unit_crosswalk", rows: crosswalk, bytesPerRow: 0, bytes: 0 },
    { table: "precinct_rollup", rows: rollup, bytesPerRow: rollupWidth, bytes: rollupBytes },
  ];
  const databaseBytes = Number(size?.db ?? 0);
  const note = [
    "Precinct units and unit_crosswalk stay out of Postgres. Feature ids live in the content-hashed pack and in the PMTiles archive.",
    "Postgres keeps precinct_rollup only. The US House parent is chosen from lon/lat in that transaction and is not stored as a unit row.",
    "Precinct result facts stay out of Postgres.",
    "Upper bound if these rollup rows are not loaded yet. A second run does not insert another copy.",
    `Measured: precinct_rollup ${rollupBytes} bytes at ${Math.round(rollupWidth)} bytes per row. unit 0 bytes. unit_crosswalk 0 bytes.`,
  ].join(" ");
  return {
    states: names.length,
    units,
    crosswalk,
    rollup,
    databaseBytes,
    estimatedBytes: rollupBytes,
    projectedBytes: databaseBytes + rollupBytes,
    parts,
    note,
  };
}

export async function buildPrecincts(
  db: pg.Pool,
  repo: string,
  opts: { state?: string; tiles?: boolean } = {},
): Promise<{ states: number; gaps: string[] }> {
  const names = opts.state ? [opts.state] : precinctStateNames(repo);
  const gaps: string[] = [];
  for (const name of names) {
    const built = await buildPrecinctState(db, repo, name, opts);
    gaps.push(...built.gaps);
  }
  return { states: names.length, gaps };
}

async function storeRollup(db: pg.Pool, state: PrecinctState): Promise<void> {
  const client = await db.connect();
  try {
    await client.query("begin");
    await client.query(
      `create temp table precinct_vote (
         unit_key text,
         county text,
         lon float8,
         lat float8,
         d int,
         r int,
         o int,
         total int,
         gray boolean
       ) on commit drop`,
    );
    let rollupChanged = 0;
    for (const year of YEARS) {
      const key = contestKey({ year, office: "president", state: "US" });
      const votes = state.features.map((feature) => {
        const vote = feature.votes[year];
        return {
          unit_key: feature.id,
          county: feature.county,
          lon: feature.lon,
          lat: feature.lat,
          d: vote?.d ?? 0,
          r: vote?.r ?? 0,
          o: vote?.other ?? 0,
          total: vote?.total ?? 0,
          gray: vote == null,
        };
      });
      await client.query("truncate precinct_vote");
      await client.query(
        `insert into precinct_vote (unit_key, county, lon, lat, d, r, o, total, gray)
         select unit_key, county, lon, lat, d, r, o, total, gray
         from jsonb_to_recordset($1::jsonb) as v(
           unit_key text, county text, lon float8, lat float8, d int, r int, o int, total int, gray boolean
         )`,
        [JSON.stringify(votes)],
      );
      const written = await client.query(
        `insert into precinct_rollup (contest_key, parent_unit_id, votes_d, votes_r, votes_o, total_votes, precincts)
         select $1, parent_id, sum(d)::bigint, sum(r)::bigint, sum(o)::bigint, sum(total)::bigint, count(*)::int
         from (
           select c.id as parent_id, v.d, v.r, v.o, v.total
           from precinct_vote v
           join boundary_set bc on bc.slug = 'v2-2024' and bc.unit_type = 'county'
           join unit c on c.boundary_set_id = bc.id and btrim(c.state_abbr) = $2 and c.name = v.county
           where v.gray is not true
           union all
           select picked.parent_id, picked.d, picked.r, picked.o, picked.total
           from (
             select distinct on (v.unit_key) d.id as parent_id, v.d, v.r, v.o, v.total
             from precinct_vote v
             join unit d on d.unit_type = 'ushouse' and btrim(d.state_abbr) = $2
             join boundary_set bd on bd.id = d.boundary_set_id and bd.slug = 'v2-2024'
             join unit_geom g on g.unit_id = d.id and g.lod = 0
             where v.gray is not true
               and v.lon is not null and v.lat is not null
               and st_covers(g.geom, st_setsrid(st_makepoint(v.lon, v.lat), 4326))
             order by v.unit_key, st_area(g.geom)
           ) picked
         ) linked
         group by parent_id
         on conflict (contest_key, parent_unit_id) do update
           set votes_d = excluded.votes_d, votes_r = excluded.votes_r, votes_o = excluded.votes_o,
               total_votes = excluded.total_votes, precincts = excluded.precincts
           where precinct_rollup.total_votes is distinct from excluded.total_votes
              or precinct_rollup.precincts is distinct from excluded.precincts`,
        [key, state.abbr],
      );
      rollupChanged += written.rowCount ?? 0;
    }
    if (rollupChanged > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query("commit");
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}
