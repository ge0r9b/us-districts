import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type pg from "pg";
import { STATE_ABBR } from "@usd/core";
import { insertJsonChunks } from "./batch.ts";
import { parseCsv } from "./csv.ts";
import { multiPolygon, unwrapJson } from "./geom.ts";
import { sha256Hex } from "./apply.ts";

export type BoundaryPaths = {
  countiesCsv: string;
  ushouseCsv: string;
  usstatesJs: string;
  uscountiesJs: string;
  uscdJs: string;
  /** Written for the shell. Omitted in tests that only check counts. */
  statesGeojson?: string;
  /** origin/data/geo commit stamped on the boundary load_batch. */
  gitCommit?: string | null;
};

export type BoundaryReport = {
  status: "applied" | "skipped";
  states: number;
  counties: number;
  ushouse: number;
  geoms: number;
  gaps: string[];
};

type UnitRow = {
  unit_type: string;
  unit_key: string;
  legacy_key: string;
  name: string;
  state_fips: string;
  state_abbr: string;
  geoid: string;
  source_record_id: string;
};

type GeomRow = { unit_type: string; unit_key: string; geojson: string };

const SCALE = 1000;

function loadNamePolys(path: string, keyOf: (row: unknown[]) => string): Map<string, unknown> {
  const data = unwrapJson(readFileSync(path, "utf8")) as unknown[][];
  const map = new Map<string, unknown>();
  for (const row of data) {
    if (!Array.isArray(row)) continue;
    map.set(keyOf(row), row);
  }
  return map;
}

async function insertGeoms(client: pg.PoolClient, rows: GeomRow[], gaps: string[]): Promise<number> {
  if (rows.length === 0) return 0;
  const sql = `insert into unit_geom (unit_id, lod, tolerance_m, min_zoom, geom)
    select u.id, 0, 0, 0,
      st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(g.geojson), 4326)), 3))
    from jsonb_to_recordset($1::jsonb) as g(unit_type text, unit_key text, geojson text)
    join boundary_set b on b.slug = 'v2-2024' and b.unit_type = g.unit_type
    join unit u on u.boundary_set_id = b.id and u.unit_key = g.unit_key
    where not st_isempty(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(g.geojson), 4326)), 3))
    on conflict (unit_id, lod) do update set geom = excluded.geom
    where unit_geom.geom is distinct from excluded.geom`;
  const run = async (batch: GeomRow[]): Promise<number> => {
    if (batch.length === 0) return 0;
    await client.query("savepoint geom");
    try {
      const res = await client.query(sql, [JSON.stringify(batch)]);
      await client.query("release savepoint geom");
      return res.rowCount ?? 0;
    } catch (err) {
      await client.query("rollback to savepoint geom");
      if (batch.length === 1) {
        gaps.push(`geom ${batch[0]!.unit_type} ${batch[0]!.unit_key}: ${(err as Error).message.split("\n")[0]}`);
        return 0;
      }
      const mid = Math.ceil(batch.length / 2);
      return (await run(batch.slice(0, mid))) + (await run(batch.slice(mid)));
    }
  };
  let n = 0;
  for (let i = 0; i < rows.length; i += 200) n += await run(rows.slice(i, i + 200));
  return n;
}

export async function loadBoundaries(pool: pg.Pool, paths: BoundaryPaths): Promise<BoundaryReport> {
  const bodies = [paths.countiesCsv, paths.ushouseCsv, paths.usstatesJs, paths.uscountiesJs, paths.uscdJs].map((p) =>
    readFileSync(p),
  );
  const sha = sha256Hex(Buffer.concat(bodies));
  const known = await pool.query<{ status: string }>(`select status from load_batch where file_sha256 = $1`, [sha]);
  if (known.rows[0]?.status === "applied") {
    if (paths.gitCommit) {
      await pool.query(
        `update load_batch set git_commit = $2 where file_sha256 = $1 and git_commit is distinct from $2`,
        [sha, paths.gitCommit],
      );
    }
    if (paths.statesGeojson) await writeStateGeojson(pool, paths.statesGeojson);
    const counts = await countsOf(pool);
    return { status: "skipped", ...counts, geoms: 0, gaps: [] };
  }

  const counties = parseCsv(bodies[0]!.toString("utf8")).rows;
  const houses = parseCsv(bodies[1]!.toString("utf8")).rows;
  const fipsByState = new Map<string, string>();
  for (const row of counties) {
    const fips = (row.geoid ?? "").slice(0, 2);
    const prev = fipsByState.get(row.state ?? "");
    if (prev && prev !== fips) throw new Error(`two FIPS prefixes for ${row.state}: ${prev} and ${fips}`);
    if (fips) fipsByState.set(row.state ?? "", fips);
  }

  const units: UnitRow[] = [];
  const gaps: string[] = [];
  for (const [name, fips] of fipsByState) {
    const abbr = STATE_ABBR[name];
    if (!abbr) {
      gaps.push(`no abbreviation for ${name}`);
      continue;
    }
    units.push({
      unit_type: "state",
      unit_key: fips,
      legacy_key: name,
      name,
      state_fips: fips,
      state_abbr: abbr,
      geoid: fips,
      source_record_id: fips,
    });
  }
  for (const row of counties) {
    const abbr = STATE_ABBR[row.state ?? ""];
    const fips = (row.geoid ?? "").slice(0, 2);
    if (!abbr || !row.geoid) {
      gaps.push(`county ${row.state}|${row.v2_name}`);
      continue;
    }
    units.push({
      unit_type: "county",
      unit_key: row.geoid,
      legacy_key: `${row.state}|${row.v2_name}`,
      name: row.v2_name || row.tiger_name || row.geoid,
      state_fips: fips,
      state_abbr: abbr,
      geoid: row.geoid,
      source_record_id: row.row?.trim() || row.geoid,
    });
  }
  for (const row of houses) {
    const abbr = STATE_ABBR[row.state ?? ""];
    const fips = (row.geoid ?? "").slice(0, 2);
    if (!abbr || !row.geoid) {
      gaps.push(`ushouse ${row.state}|${row.v2_name}`);
      continue;
    }
    units.push({
      unit_type: "ushouse",
      unit_key: row.geoid,
      legacy_key: `${row.state}|${row.v2_name}`,
      name: row.tiger_name || `District ${row.v2_name}`,
      state_fips: fips,
      state_abbr: abbr,
      geoid: row.geoid,
      source_record_id: row.row?.trim() || row.geoid,
    });
  }

  const statePolys = loadNamePolys(paths.usstatesJs, (row) => String(row[0]));
  const countyPolys = loadNamePolys(paths.uscountiesJs, (row) => `${row[0]}|${row[1]}`);
  const cdPolys = loadNamePolys(paths.uscdJs, (row) => `${row[0]}|${row[1]}`);
  const geoms: GeomRow[] = [];
  const pushGeom = (unitType: string, unitKey: string, legacy: string, table: Map<string, unknown>, polyIndex: number) => {
    const row = table.get(legacy);
    if (!row || !Array.isArray(row)) return;
    const geom = multiPolygon(row[polyIndex], SCALE);
    if (!geom) {
      gaps.push(`empty geom ${legacy}`);
      return;
    }
    geoms.push({ unit_type: unitType, unit_key: unitKey, geojson: JSON.stringify(geom) });
  };
  for (const unit of units) {
    if (unit.unit_type === "state") pushGeom("state", unit.unit_key, unit.legacy_key, statePolys, 1);
    else if (unit.unit_type === "county") pushGeom("county", unit.unit_key, unit.legacy_key, countyPolys, 2);
    else pushGeom("ushouse", unit.unit_key, unit.legacy_key, cdPolys, 2);
  }

  const client = await pool.connect();
  try {
    await client.query("begin");
    await client.query(
      `insert into load_batch (file_name, file_sha256, git_commit, row_count, status)
       values ('boundary:v2-2024', $1, $2, $3, 'staged')
       on conflict (file_sha256) do update set status = 'staged',
         git_commit = coalesce(excluded.git_commit, load_batch.git_commit)`,
      [sha, paths.gitCommit ?? null, units.length],
    );
    const unitWrites = await insertJsonChunks(
      client,
      `insert into unit (
         boundary_set_id, unit_type, unit_key, legacy_key, name, state_fips, state_abbr, geoid, country, source_record_id
       )
       select b.id, x.unit_type, x.unit_key, x.legacy_key, x.name, x.state_fips, x.state_abbr, x.geoid, 'us', x.source_record_id
       from jsonb_to_recordset($1::jsonb) as x(
         unit_type text, unit_key text, legacy_key text, name text, state_fips text, state_abbr text, geoid text,
         source_record_id text
       )
       join boundary_set b on b.slug = 'v2-2024' and b.unit_type = x.unit_type
       on conflict (boundary_set_id, unit_key) do update
         set legacy_key = excluded.legacy_key, name = excluded.name,
             state_fips = excluded.state_fips, state_abbr = excluded.state_abbr, geoid = excluded.geoid,
             source_record_id = excluded.source_record_id
         where unit.name is distinct from excluded.name
            or unit.legacy_key is distinct from excluded.legacy_key
            or unit.source_record_id is distinct from excluded.source_record_id`,
      units,
    );
    await client.query(
      `update unit child set parent_unit_id = parent.id
       from unit parent, boundary_set bc, boundary_set bp
       where child.boundary_set_id = bc.id and parent.boundary_set_id = bp.id
         and bc.slug = 'v2-2024' and bp.slug = 'v2-2024'
         and child.unit_type in ('county', 'ushouse') and parent.unit_type = 'state'
         and child.state_abbr = parent.state_abbr`,
    );
    const geomCount = await insertGeoms(client, geoms, gaps);
    if (unitWrites > 0 || geomCount > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query(
      `update unit u
       set centroid = st_pointonsurface(g.geom),
           bbox = st_envelope(g.geom)::box2d,
           area_m2 = st_area(g.geom::geography)
       from unit_geom g, boundary_set b
       where g.unit_id = u.id and g.lod = 0 and u.boundary_set_id = b.id and b.slug = 'v2-2024'`,
    );
    await client.query(
      `insert into boundary_set_default (unit_type, results_year, boundary_set_id)
       select b.unit_type, y.yr, b.id
       from boundary_set b
       cross join (values (2016), (2020), (2022), (2024)) as y(yr)
       where b.slug = 'v2-2024' and b.unit_type in ('state', 'county', 'ushouse')
       on conflict do nothing`,
    );
    await client.query(
      `update boundary_set b set feature_count = c.n
       from (
         select boundary_set_id, count(*)::int n from unit group by boundary_set_id
       ) c
       where b.id = c.boundary_set_id and b.slug = 'v2-2024'`,
    );
    await client.query(
      `update load_batch set status = 'applied', finished_at = now(), report = $2::jsonb where file_sha256 = $1`,
      [sha, JSON.stringify({ units: units.length, geoms: geomCount, gaps: gaps.slice(0, 30) })],
    );
    await client.query("commit");
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }

  if (paths.statesGeojson) await writeStateGeojson(pool, paths.statesGeojson);
  const counts = await countsOf(pool);
  return { status: "applied", ...counts, geoms: geoms.length, gaps };
}

async function countsOf(pool: pg.Pool): Promise<{ states: number; counties: number; ushouse: number }> {
  const r = await pool.query<{ unit_type: string; n: string }>(
    `select u.unit_type, count(*)::text n
     from unit u join boundary_set b on b.id = u.boundary_set_id
     where b.slug = 'v2-2024' and u.unit_type in ('state', 'county', 'ushouse')
     group by u.unit_type`,
  );
  const n = (t: string) => Number(r.rows.find((row) => row.unit_type === t)?.n ?? 0);
  return { states: n("state"), counties: n("county"), ushouse: n("ushouse") };
}

export async function writeStateGeojson(pool: pg.Pool, outPath: string): Promise<void> {
  const r = await pool.query<{ geojson: string }>(
    `select json_build_object(
       'type', 'FeatureCollection',
       'features', coalesce(json_agg(json_build_object(
         'type', 'Feature',
         'id', u.unit_key,
         'properties', json_build_object('key', u.unit_key, 'name', u.name),
         'geometry', st_asgeojson(g.geom)::json
       )), '[]'::json)
     )::text as geojson
     from unit u
     join unit_geom g on g.unit_id = u.id and g.lod = 0
     join boundary_set b on b.id = u.boundary_set_id
     where b.slug = 'v2-2024' and u.unit_type = 'state'`,
  );
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, r.rows[0]?.geojson ?? '{"type":"FeatureCollection","features":[]}');
}

export function boundarySha(paths: BoundaryPaths): string {
  return createHash("sha256")
    .update(Buffer.concat([paths.countiesCsv, paths.ushouseCsv].map((p) => readFileSync(p))))
    .digest("hex");
}
