import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import type pg from "pg";
import { insertJsonChunks } from "./batch.ts";
import { BUDGET_BYTES, COMPANY_LOCATION_ROWS, EST_LOCATION_BYTES, fitsBudget, formatMb } from "./budget.ts";
import { writeClusterPmtiles, type ClusterPoint } from "./cluster-tiles.ts";
import { parseCsv, readFileText } from "./csv.ts";

export type CompanyLoadReport = {
  status: "applied" | "skipped" | "tiles-only";
  rows: number;
  locations: number;
  tiles: number;
  estimateBytes: number;
  gap: string | null;
};

const ENTITY_ID = /^wikidata:Q[0-9]+$/;
const COMPANY_REL = "data-v3/institutions/companies/company_locations.csv.gz";

export function companyEstimateBytes(): number {
  return COMPANY_LOCATION_ROWS * EST_LOCATION_BYTES;
}

export function ensureCompaniesCache(root: string): string {
  const dest = join(root, "v3/.cache/companies");
  const file = join(dest, COMPANY_REL);
  if (existsSync(file)) return file;
  mkdirSync(dest, { recursive: true });
  try {
    execFileSync("git", ["fetch", "--no-tags", "origin", "data/companies"], {
      cwd: root,
      stdio: "pipe",
      timeout: 120_000,
    });
  } catch {
    // The ref may already be local.
  }
  const tar = execFileSync("git", ["archive", "origin/data/companies", COMPANY_REL], {
    cwd: root,
    encoding: "buffer",
    maxBuffer: 32 * 1024 * 1024,
  });
  execFileSync("tar", ["-x", "-C", dest], { input: tar });
  return file;
}

export type CompanyInput = {
  location_id: string;
  entity_id: string;
  sub_entity_id?: string;
  role?: string;
  name?: string;
  address?: string;
  geoid?: string;
  boundary_set?: string;
  lat?: string;
  lon?: string;
  source_id?: string;
  retrieved_at?: string;
  brand_name?: string;
  country_code?: string;
};

export async function loadCompanyRows(db: pg.Pool, rows: CompanyInput[]): Promise<{ locations: number; skipped: number }> {
  const entities = new Map<string, { entity_id: string; name: string; country: string | null; brand_name: string | null }>();
  const locations: Record<string, unknown>[] = [];
  const sources = new Map<string, string | null>();
  let skipped = 0;
  const seen = new Set<string>();
  for (const row of rows) {
    const locationId = row.location_id.trim();
    const entityId = row.entity_id.trim();
    if (!locationId || seen.has(locationId) || !ENTITY_ID.test(entityId)) {
      skipped++;
      continue;
    }
    const lat = row.lat?.trim() ? Number(row.lat) : null;
    const lon = row.lon?.trim() ? Number(row.lon) : null;
    const geoid = row.geoid?.trim() || "";
    const hasPoint = lat != null && lon != null && Number.isFinite(lat) && Number.isFinite(lon);
    if (!hasPoint && !geoid) {
      skipped++;
      continue;
    }
    seen.add(locationId);
    const country = countryCode(row.country_code);
    const brand = row.brand_name?.trim() || row.name?.trim() || entityId;
    if (!entities.has(entityId)) {
      entities.set(entityId, { entity_id: entityId, name: brand, country: country?.toLowerCase() ?? null, brand_name: brand });
    }
    const sourceId = row.source_id?.trim() || "companies-bot";
    if (!sources.has(sourceId)) sources.set(sourceId, timestamp(row.retrieved_at));
    const role = row.role?.trim() === "hq_in" ? "hq_in" : "establishment_at";
    locations.push({
      location_key: locationId,
      entity_id: entityId,
      sub_entity_id: row.sub_entity_id?.trim() || null,
      role,
      name: row.name?.trim() || brand,
      address: row.address?.trim() || null,
      lon: hasPoint ? lon : null,
      lat: hasPoint ? lat : null,
      geoid,
      boundary_set: row.boundary_set?.trim() || "",
      country_code: country,
      source_record_id: locationId,
      retrieved_at: timestamp(row.retrieved_at),
    });
  }
  if (locations.length === 0) return { locations: 0, skipped };
  const client = await db.connect();
  try {
    await client.query("begin");
    await insertJsonChunks(
      client,
      `insert into source (source_id, title, retrieved_at)
       select source_id, 'companies', retrieved_at
       from jsonb_to_recordset($1::jsonb) as x(source_id text, retrieved_at timestamptz)
       on conflict (source_id) do nothing`,
      [...sources.entries()].map(([source_id, retrieved_at]) => ({ source_id, retrieved_at })),
    );
    await insertJsonChunks(
      client,
      `insert into entity (entity_id, kind, name, origin, country, brand_name, source_record_id)
       select entity_id, 'brand', name, 'companies_bot', nullif(country, ''), brand_name, entity_id
       from jsonb_to_recordset($1::jsonb) as x(entity_id text, name text, country text, brand_name text)
       on conflict (entity_id) do nothing`,
      [...entities.values()],
    );
    const written = await insertJsonChunks(
      client,
      `insert into entity_location (
         location_key, entity_id, sub_entity_id, role, name, address, geom, geoid, boundary_set,
         country_code, source_record_id, retrieved_at
       )
       select x.location_key, x.entity_id, nullif(x.sub_entity_id, ''), x.role, x.name, x.address,
              case when x.lon is not null and x.lat is not null
                then st_setsrid(st_makepoint(x.lon, x.lat), 4326) end,
              nullif(x.geoid, ''), nullif(x.boundary_set, ''),
              nullif(x.country_code, ''), x.source_record_id, x.retrieved_at
       from jsonb_to_recordset($1::jsonb) as x(
         location_key text, entity_id text, sub_entity_id text, role text, name text, address text,
         lon float8, lat float8, geoid text, boundary_set text, country_code text,
         source_record_id text, retrieved_at timestamptz
       )
       on conflict (location_key) do update
         set country_code = excluded.country_code, geom = excluded.geom, name = excluded.name,
             address = excluded.address, source_record_id = excluded.source_record_id, geoid = excluded.geoid`,
      locations,
    );
    if (written > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query("commit");
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
  return { locations: locations.length, skipped };
}

export async function loadCompanies(
  db: pg.Pool,
  opts: { root: string; currentBytes: number; allow: boolean; tilesPath: string },
): Promise<CompanyLoadReport> {
  const estimateBytes = companyEstimateBytes();
  const file = ensureCompaniesCache(opts.root);
  const { text } = readFileText(file);
  const parsed = parseCsv(text);
  const points: ClusterPoint[] = [];
  const inputs: CompanyInput[] = parsed.rows.map((row) => {
    const lat = Number(row.lat);
    const lon = Number(row.lon);
    if (Number.isFinite(lat) && Number.isFinite(lon)) points.push({ lon, lat });
    return {
      location_id: row.location_id ?? "",
      entity_id: row.entity_id ?? "",
      sub_entity_id: row.sub_entity_id,
      role: row.role,
      name: row.name,
      address: row.address,
      geoid: row.geoid,
      boundary_set: row.boundary_set,
      lat: row.lat,
      lon: row.lon,
      source_id: row.source_id,
      retrieved_at: row.retrieved_at,
      brand_name: row.brand_name,
      country_code: row.country_code,
    };
  });
  const tiles = points.length > 0 ? writeClusterPmtiles(points, opts.tilesPath) : 0;
  const over = !fitsBudget(opts.currentBytes, estimateBytes);
  if (over && !opts.allow) {
    return {
      status: "tiles-only",
      rows: parsed.rows.length,
      locations: 0,
      tiles,
      estimateBytes,
      gap: `companies: estimated ${formatMb(estimateBytes)} on top of ${formatMb(opts.currentBytes)} would pass ${formatMb(BUDGET_BYTES)}. Rows were not inserted. Tiles were written. Re-run with: npm run db:load -- --include=companies --allow-over-budget=companies`,
    };
  }
  const loaded = await loadCompanyRows(db, inputs);
  return {
    status: "applied",
    rows: parsed.rows.length,
    locations: loaded.locations,
    tiles,
    estimateBytes,
    gap: null,
  };
}

function countryCode(raw: string | undefined): string | null {
  const code = (raw ?? "").trim().toUpperCase();
  return /^[A-Z]{2}$/.test(code) ? code : null;
}

function timestamp(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  if (!text) return null;
  const ms = Date.parse(text);
  return Number.isNaN(ms) ? null : new Date(ms).toISOString();
}
