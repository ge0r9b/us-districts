import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import type pg from "pg";
import { contestKey, stateName } from "@usd/core";
import { loadPrecinctState, precinctStateNames, type PrecinctFeature, type PrecinctState } from "./precinct-source.ts";
import { writePrecinctPmtiles } from "./precinct-tiles.ts";
import { ensureUnits } from "./units.ts";

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
  const bytes = Buffer.from(est, "base64");
  return ((bytes[index >> 3] ?? 0) & (1 << (index & 7))) !== 0;
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
  await storeMembership(db, state);
  return { abbr: state.abbr, features: state.features.length, gaps: state.gaps };
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

async function storeMembership(db: pg.Pool, state: PrecinctState): Promise<void> {
  const fips = await db.query<{ fips: string }>(
    `select btrim(u.state_fips) fips
     from unit u join boundary_set b on b.id = u.boundary_set_id
     where b.slug = 'v2-2024' and u.unit_type = 'state' and btrim(u.state_abbr) = $1`,
    [state.abbr],
  );
  await ensureUnits(
    db,
    state.features.map((feature) => ({
      unit_type: "precinct",
      unit_key: feature.id,
      legacy_key: `${state.name}|${feature.county}|${feature.name}|${feature.ordinal}`,
      name: feature.name,
      state_fips: fips.rows[0]?.fips ?? null,
      state_abbr: state.abbr,
      geoid: null,
      source_record_id: String(feature.ordinal),
    })),
  );
  const client = await db.connect();
  try {
    await client.query("begin");
    await client.query(
      `update unit u
       set centroid = st_setsrid(st_makepoint(x.lon, x.lat), 4326),
           parent_unit_id = c.id
       from jsonb_to_recordset($1::jsonb) as x(unit_key text, lon float8, lat float8, county text)
       join boundary_set bp on bp.slug = 'v2-2024' and bp.unit_type = 'precinct'
       join boundary_set bc on bc.slug = 'v2-2024' and bc.unit_type = 'county'
       join unit c on c.boundary_set_id = bc.id and btrim(c.state_abbr) = $2 and c.name = x.county
       where u.boundary_set_id = bp.id and u.unit_key = x.unit_key
         and (u.parent_unit_id is distinct from c.id
           or u.centroid is distinct from st_setsrid(st_makepoint(x.lon, x.lat), 4326))`,
      [
        JSON.stringify(state.features.map((feature) => ({
          unit_key: feature.id,
          lon: feature.lon,
          lat: feature.lat,
          county: feature.county,
        }))),
        state.abbr,
      ],
    );
    await client.query(
      `insert into unit_crosswalk (from_unit_id, to_unit_id, weight, method)
       select u.id, u.parent_unit_id, 1, 'exact'
       from unit u
       join boundary_set b on b.id = u.boundary_set_id
       where b.slug = 'v2-2024' and u.unit_type = 'precinct' and btrim(u.state_abbr) = $1
         and u.parent_unit_id is not null
       on conflict (from_unit_id, to_unit_id) do nothing`,
      [state.abbr],
    );
    await client.query(
      `insert into unit_crosswalk (from_unit_id, to_unit_id, weight, method)
       select picked.from_id, picked.to_id, 1, 'area'
       from (
         select distinct on (p.id) p.id as from_id, d.id as to_id
         from unit p
         join boundary_set bp on bp.id = p.boundary_set_id
         join unit d on d.unit_type = 'ushouse' and btrim(d.state_abbr) = btrim(p.state_abbr)
         join boundary_set bd on bd.id = d.boundary_set_id and bd.slug = 'v2-2024'
         join unit_geom g on g.unit_id = d.id and g.lod = 0
         where bp.slug = 'v2-2024' and bp.unit_type = 'precinct'
           and btrim(p.state_abbr) = $1
           and p.centroid is not null
           and st_covers(g.geom, p.centroid)
         order by p.id, st_area(g.geom)
       ) picked
       on conflict (from_unit_id, to_unit_id) do nothing`,
      [state.abbr],
    );
    let rollupChanged = 0;
    for (const year of YEARS) {
      const key = contestKey({ year, office: "president", state: "US" });
      const votes = state.features.map((feature) => {
        const vote = feature.votes[year];
        return {
          unit_key: feature.id,
          d: vote?.d ?? 0,
          r: vote?.r ?? 0,
          o: vote?.other ?? 0,
          total: vote?.total ?? 0,
          gray: vote == null,
        };
      });
      const written = await client.query(
        `insert into precinct_rollup (contest_key, parent_unit_id, votes_d, votes_r, votes_o, total_votes, precincts)
         select $1, x.to_unit_id, sum(v.d)::bigint, sum(v.r)::bigint, sum(v.o)::bigint, sum(v.total)::bigint, count(*)::int
         from jsonb_to_recordset($2::jsonb) as v(unit_key text, d int, r int, o int, total int, gray boolean)
         join unit p on p.unit_key = v.unit_key and p.unit_type = 'precinct'
         join boundary_set b on b.id = p.boundary_set_id and b.slug = 'v2-2024'
         join unit_crosswalk x on x.from_unit_id = p.id
         where v.gray is not true and btrim(p.state_abbr) = $3
         group by x.to_unit_id
         on conflict (contest_key, parent_unit_id) do update
           set votes_d = excluded.votes_d, votes_r = excluded.votes_r, votes_o = excluded.votes_o,
               total_votes = excluded.total_votes, precincts = excluded.precincts
           where precinct_rollup.total_votes is distinct from excluded.total_votes
              or precinct_rollup.precincts is distinct from excluded.precincts`,
        [key, JSON.stringify(votes), state.abbr],
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
