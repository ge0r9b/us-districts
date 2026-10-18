import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { compareAnswerKeys, encodeEstBits, staticPackKey, type PlaceName, type ResultPack } from "@usd/core";
import type { Sql } from "../api/src/sql.ts";
import { buildUnitArchive, type UnitFeature } from "./unit-tiles.ts";

/** Cloudflare Pages rejects a single file at 25 MiB. */
export const STATIC_FILE_LIMIT = 25 * 1024 * 1024;

const UNIT_TYPES = ["state", "county", "ushouse"] as const;
const ZOOM = 3;

export type StaticFile = { path: string; bytes: number };

type VoteRow = {
  unit_key: string;
  legacy_key: string | null;
  name: string;
  state_abbr: string | null;
  geoid: string | null;
  votes: Record<string, number> | null;
  mv_total: string | null;
  total_votes: string | null;
  is_estimate: boolean | null;
};

type GeomRow = { unit_key: string; name: string; geom: string | null };

export function assertStaticLimit(bytes: number, path: string): void {
  if (bytes >= STATIC_FILE_LIMIT) {
    throw new Error(`${path} is ${bytes} bytes, over the 25 MiB file limit`);
  }
}

export async function sampleContestKeys(sql: Sql): Promise<string[]> {
  const found = await sql.query<{ contest_key: string; office_key: string }>(
    `select c.contest_key, o.office_key
     from contest c join office o on o.id = c.office_id
     where c.year = 2024
       and (
         o.office_key = 'president'
         or (
           o.office_key ilike '%house%'
           and o.office_key not ilike '%senate%'
           and o.label not ilike '%senate%'
         )
       )`,
  );
  const keys = new Set(found.rows.map((row) => row.contest_key));
  // The shell asks for 2016 states, then 2020 and 2024 counties. 2024 districts are the US House sample.
  for (const year of [2016, 2020, 2024]) keys.add(`${year}|US|president|`);
  return [...keys].sort();
}

export async function exportStaticSample(
  sql: Sql,
  opts: {
    packsDir: string;
    tilesDir: string;
    contests?: string[];
    unitTypes?: readonly string[];
    tiles?: boolean;
  },
): Promise<{ dv: number; files: StaticFile[] }> {
  const version = await sql.query<{ dv: number }>("select dv from data_version where id = 1");
  const dv = version.rows[0]?.dv ?? 1;
  const contests = opts.contests ?? (await sampleContestKeys(sql));
  const unitTypes = opts.unitTypes ?? UNIT_TYPES;
  mkdirSync(opts.packsDir, { recursive: true });
  const files: StaticFile[] = [];
  const packs: Record<string, { sha: string; file: string }> = {};
  const names = new Map<string, PlaceName>();

  for (const contest of contests) {
    for (const unitType of unitTypes) {
      const built = await buildContestPack(sql, contest, unitType);
      const json = JSON.stringify(built.pack);
      const sha = createHash("sha256").update(json).digest("hex");
      const file = `${sha.slice(0, 12)}.json`;
      const path = join(opts.packsDir, file);
      writeChecked(path, json, files);
      packs[staticPackKey(contest, unitType)] = { sha, file };
      for (const name of built.names) names.set(`${name.kind}|${name.unit}`, name);
    }
  }

  const index = JSON.stringify({ v: 3, dv, packs });
  writeChecked(join(opts.packsDir, "index.json"), index, files);
  const nameFile = JSON.stringify({ v: 3, names: [...names.values()].sort((a, b) => a.name.localeCompare(b.name)) });
  writeChecked(join(opts.packsDir, "names.json"), nameFile, files);

  if (opts.tiles !== false) {
    mkdirSync(opts.tilesDir, { recursive: true });
    await writeTiles(sql, "state", "state", join(opts.tilesDir, "state-2024@1.pmtiles"), files);
    await writeTiles(sql, "ushouse", "districts", join(opts.tilesDir, "ushouse-2024@1.pmtiles"), files);
  }
  return { dv, files };
}

async function buildContestPack(
  sql: Sql,
  contest: string,
  unitType: string,
): Promise<{ pack: ResultPack; names: PlaceName[] }> {
  const answerRows = await sql.query<{ answer_key: string }>(
    `select a.answer_key
     from answer a join contest c on c.id = a.contest_id
     where c.contest_key = $1`,
    [contest],
  );
  const answers = answerRows.rows.map((row) => row.answer_key).sort(compareAnswerKeys);
  const listed = answers.length > 0 ? answers : ["dem_nominee", "rep_nominee", "other"];
  const slots = await sql.query<{ slot: string; answer_key: string }>(
    `select s.slot, a.answer_key
     from contest_display_slot s
     join contest c on c.id = s.contest_id
     join answer a on a.id = s.answer_id
     where c.contest_key = $1`,
    [contest],
  );
  const display: Record<string, string> = {};
  for (const slot of slots.rows) display[slot.slot] = slot.answer_key;
  if (!display.d && listed.includes("dem_nominee")) display.d = "dem_nominee";
  if (!display.r && listed.includes("rep_nominee")) display.r = "rep_nominee";

  const data = await sql.query<VoteRow>(
    `select u.unit_key, u.legacy_key, u.name, btrim(u.state_abbr) as state_abbr, u.geoid,
            a.votes, a.total::text as mv_total, rt.total_votes::text, a.is_estimate
     from unit u
     join boundary_set b on b.id = u.boundary_set_id and b.slug = 'v2-2024'
     left join contest c on c.contest_key = $1
     left join unit_contest_agg a on a.contest_id = c.id and a.unit_id = u.id
     left join result_total rt on rt.contest_id = c.id and rt.unit_id = u.id
     where u.unit_type = $2
     order by u.unit_key`,
    [contest, unitType],
  );

  const flags: boolean[] = [];
  const pack: ResultPack = {
    v: 3,
    contest,
    unit_type: unitType,
    boundary_set: "v2-2024",
    answers: listed,
    display_slots: display,
    ids: [],
    names: [],
    legacy: [],
    states: [],
    geoids: [],
    votes: [],
    total: [],
    est: "",
  };
  const names: PlaceName[] = [];
  const kind = unitType === "ushouse" ? "district" : unitType;
  for (const row of data.rows) {
    const has = row.votes != null;
    const total = row.total_votes != null ? Number(row.total_votes) : row.mv_total != null ? Number(row.mv_total) : null;
    pack.ids.push(row.unit_key);
    pack.names.push(row.name);
    pack.legacy.push(row.legacy_key);
    pack.states.push(row.state_abbr);
    pack.geoids.push(row.geoid);
    pack.votes.push(has ? listed.map((key) => Number(row.votes?.[key] ?? 0)) : null);
    pack.total.push(has ? total : null);
    flags.push(row.is_estimate === true);
    names.push({ name: row.name, state: row.state_abbr, kind, unit: row.unit_key });
  }
  pack.est = encodeEstBits(flags);
  return { pack, names };
}

async function writeTiles(sql: Sql, unitType: string, layer: string, path: string, files: StaticFile[]): Promise<void> {
  let tolerance = unitType === "state" ? 0.2 : 0.08;
  let last: Uint8Array<ArrayBufferLike> = new Uint8Array();
  for (let attempt = 0; attempt < 3; attempt++) {
    const features = await loadFeatures(sql, unitType, tolerance);
    if (features.length === 0) return;
    last = buildUnitArchive(features, layer, ZOOM);
    if (last.length < STATIC_FILE_LIMIT) {
      mkdirSync(join(path, ".."), { recursive: true });
      writeFileSync(path, last);
      files.push({ path, bytes: last.length });
      return;
    }
    tolerance *= 2;
  }
  assertStaticLimit(last.length, path);
}

async function loadFeatures(sql: Sql, unitType: string, tolerance: number): Promise<UnitFeature[]> {
  const rows = await sql.query<GeomRow>(
    `select u.unit_key, u.name,
            ST_AsGeoJSON(ST_SimplifyPreserveTopology(ug.geom, $2)) as geom
     from unit u
     join boundary_set b on b.id = u.boundary_set_id and b.slug = 'v2-2024'
     join unit_geom ug on ug.unit_id = u.id
     where u.unit_type = $1
       and ug.lod = (select max(g.lod) from unit_geom g where g.unit_id = u.id)`,
    [unitType, tolerance],
  );
  const features: UnitFeature[] = [];
  for (const row of rows.rows) {
    if (!row.geom) continue;
    const rings = ringsFromGeoJson(row.geom);
    if (rings.length === 0) continue;
    features.push({ id: row.unit_key, name: row.name, rings });
  }
  return features;
}

function ringsFromGeoJson(text: string): [number, number][][] {
  const geom = JSON.parse(text) as { type?: string; coordinates?: unknown };
  const rings: [number, number][][] = [];
  const push = (ring: unknown) => {
    if (!Array.isArray(ring)) return;
    const pairs: [number, number][] = [];
    for (const point of ring) {
      if (!Array.isArray(point) || point.length < 2) continue;
      const lon = Number(point[0]);
      const lat = Number(point[1]);
      if (Number.isFinite(lon) && Number.isFinite(lat)) pairs.push([lon, lat]);
    }
    if (pairs.length >= 3) rings.push(pairs);
  };
  if (geom.type === "Polygon" && Array.isArray(geom.coordinates)) push(geom.coordinates[0]);
  if (geom.type === "MultiPolygon" && Array.isArray(geom.coordinates)) {
    for (const polygon of geom.coordinates) {
      if (Array.isArray(polygon)) push(polygon[0]);
    }
  }
  return rings;
}

function writeChecked(path: string, body: string, files: StaticFile[]): void {
  const bytes = Buffer.byteLength(body);
  assertStaticLimit(bytes, path);
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, body);
  files.push({ path, bytes });
}
