import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import type pg from "pg";
import { insertJsonChunks } from "./batch.ts";
import { fetchOrigin, needsRefresh, originCommit, stampCommit } from "./branch-cache.ts";
import { BUDGET_BYTES, COMPANY_LOCATION_ROWS, EST_LOCATION_BYTES, companyLoadAllowed, formatMb } from "./budget.ts";
import { writeClusterPmtiles, type ClusterPoint } from "./cluster-tiles.ts";
import { parseCsv, readFileText } from "./csv.ts";
import {
  EST_ORG_ENTITY_BYTES,
  ORG_ENTITY_ID,
  ORG_ENTITY_ROWS,
  ORG_FILES,
  ORG_LOCATION_ROWS,
  readOrganizationBundle,
  writeOrganizationEntities,
} from "./organizations.ts";

export type CompanyLoadReport = {
  status: "applied" | "skipped" | "tiles-only";
  rows: number;
  locations: number;
  tiles: number;
  /** Live `pg_database_size` at the moment the gate ran. */
  databaseBytes: number;
  gap: string | null;
};

const ENTITY_ID = /^wikidata:Q[0-9]+$/;
const COMPANY_REL = "data-v3/institutions/companies/company_locations.csv.gz";
const BRANDS_REL = "data-v3/institutions/companies/brands.csv";
const CACHE_FILES = [COMPANY_REL, BRANDS_REL, ...ORG_FILES];
const ENTITY_KINDS = new Set(["brand", "organization", "company", "nonprofit", "fund"]);

/** Store points plus the organization entities and their hq / campus rows. */
export function companyEstimateBytes(): number {
  return (COMPANY_LOCATION_ROWS + ORG_LOCATION_ROWS) * EST_LOCATION_BYTES + ORG_ENTITY_ROWS * EST_ORG_ENTITY_BYTES;
}

export function ensureCompaniesCache(root: string): string {
  const dest = join(root, "v3/.cache/companies");
  const file = join(dest, COMPANY_REL);
  fetchOrigin(root, ["data/companies"]);
  const head = originCommit(root, "data/companies");
  if (!needsRefresh(dest, head, CACHE_FILES)) return file;
  mkdirSync(dest, { recursive: true });
  const tar = execFileSync("git", ["archive", "origin/data/companies", ...CACHE_FILES], {
    cwd: root,
    encoding: "buffer",
    maxBuffer: 96 * 1024 * 1024,
  });
  execFileSync("tar", ["-x", "-C", dest], { input: tar });
  stampCommit(dest, head);
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

export type BrandName = { name: string; brand_name: string; kind: string };

export function readBrandCatalog(text: string): Map<string, BrandName> {
  const parsed = parseCsv(text);
  const names = new Map<string, BrandName>();
  for (const row of parsed.rows) {
    const id = (row.entity_id ?? "").trim();
    if (!ENTITY_ID.test(id)) continue;
    const kind = ENTITY_KINDS.has(row.kind ?? "") ? row.kind! : "brand";
    const name = (row.name ?? "").trim() || (row.brand_name ?? "").trim() || id;
    names.set(id, { name, brand_name: (row.brand_name ?? "").trim() || name, kind });
  }
  return names;
}

export async function loadCompanyRows(
  db: pg.Pool,
  rows: CompanyInput[],
  names: Map<string, BrandName> = new Map(),
): Promise<{ locations: number; skipped: number; relations: number }> {
  const entities = new Map<string, { entity_id: string; kind: string; name: string; country: string | null; brand_name: string | null }>();
  const relations = new Map<string, { parent_id: string; child_id: string }>();
  const locations: Record<string, unknown>[] = [];
  const sources = new Map<string, string | null>();
  let skipped = 0;
  const seen = new Set<string>();
  const remember = (entityId: string, fallback: string, country: string | null) => {
    if (entities.has(entityId)) return;
    const known = names.get(entityId);
    entities.set(entityId, {
      entity_id: entityId,
      kind: known?.kind ?? "brand",
      name: known?.name ?? fallback,
      country,
      brand_name: known?.brand_name ?? fallback,
    });
  };
  for (const row of rows) {
    const locationId = row.location_id.trim();
    const entityId = row.entity_id.trim();
    if (!locationId || seen.has(locationId) || !ORG_ENTITY_ID.test(entityId)) {
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
    remember(entityId, brand, country?.toLowerCase() ?? null);
    const subRaw = row.sub_entity_id?.trim() || "";
    const subId = ORG_ENTITY_ID.test(subRaw) ? subRaw : "";
    if (subId) {
      remember(subId, names.get(subId)?.name ?? subId, null);
      if (subId !== entityId) relations.set(`${entityId}|${subId}`, { parent_id: entityId, child_id: subId });
    }
    const sourceId = row.source_id?.trim() || "companies-bot";
    if (!sources.has(sourceId)) sources.set(sourceId, timestamp(row.retrieved_at));
    const role = row.role?.trim() === "hq_in" ? "hq_in" : "establishment_at";
    locations.push({
      location_key: locationId,
      entity_id: entityId,
      sub_entity_id: subId,
      role,
      name: row.name?.trim() || brand,
      address: row.address?.trim() || null,
      lon: hasPoint ? lon : null,
      lat: hasPoint ? lat : null,
      geoid,
      boundary_set: country && country !== "US" ? "" : row.boundary_set?.trim() || "",
      country_code: country,
      source_record_id: locationId,
      retrieved_at: timestamp(row.retrieved_at),
    });
  }
  if (locations.length === 0) return { locations: 0, skipped, relations: 0 };
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
       select entity_id, kind, name, 'companies_bot', nullif(country, ''), brand_name, entity_id
       from jsonb_to_recordset($1::jsonb) as x(entity_id text, kind text, name text, country text, brand_name text)
       on conflict (entity_id) do update
         set name = excluded.name, brand_name = excluded.brand_name
         where entity.name = entity.entity_id`,
      [...entities.values()],
    );
    if (relations.size > 0) {
      if (!sources.has("companies-bot")) sources.set("companies-bot", null);
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
        `insert into entity_relation (parent_nid, child_nid, relation, source_id, source_record_id)
         select p.nid, c.nid, 'brand_of', 'companies-bot', x.parent_id || '|' || x.child_id
         from jsonb_to_recordset($1::jsonb) as x(parent_id text, child_id text)
         join entity p on p.entity_id = x.parent_id
         join entity c on c.entity_id = x.child_id
         on conflict (parent_nid, child_nid, relation, valid_from) do nothing`,
        [...relations.values()],
      );
    }
    const written = await insertJsonChunks(
      client,
      `insert into entity_location (
         location_key, entity_nid, sub_entity_nid, role, name, address, geom, geoid, boundary_set,
         country_code, source_record_id, retrieved_at
       )
       select x.location_key, e.nid, s.nid, x.role, x.name, x.address,
              case when x.lon is not null and x.lat is not null
                then st_setsrid(st_makepoint(x.lon, x.lat), 4326) end,
              nullif(x.geoid, ''), nullif(x.boundary_set, ''),
              nullif(x.country_code, ''), x.source_record_id, x.retrieved_at
       from jsonb_to_recordset($1::jsonb) as x(
         location_key text, entity_id text, sub_entity_id text, role text, name text, address text,
         lon float8, lat float8, geoid text, boundary_set text, country_code text,
         source_record_id text, retrieved_at timestamptz
       )
       join entity e on e.entity_id = x.entity_id
       left join entity s on s.entity_id = nullif(x.sub_entity_id, '')
       on conflict (location_key) do update
         set country_code = excluded.country_code, geom = excluded.geom, name = excluded.name,
             sub_entity_nid = excluded.sub_entity_nid,
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
  return { locations: locations.length, skipped, relations: relations.size };
}

export async function loadCompanies(
  db: pg.Pool,
  opts: { root: string; currentBytes: number; allow: boolean; tilesPath: string },
): Promise<CompanyLoadReport> {
  const file = ensureCompaniesCache(opts.root);
  const { text } = readFileText(file);
  const brandsPath = join(opts.root, "v3/.cache/companies", BRANDS_REL);
  const names = existsSync(brandsPath) ? readBrandCatalog(readFileText(brandsPath).text) : new Map();
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
  const cacheDir = join(opts.root, "v3/.cache/companies");
  const orgs = readOrganizationBundle(cacheDir);
  for (const row of orgs.locations) {
    const lat = Number(row.lat);
    const lon = Number(row.lon);
    if (Number.isFinite(lat) && Number.isFinite(lon)) points.push({ lon, lat });
  }
  const tiles = points.length > 0 ? writeClusterPmtiles(points, opts.tilesPath) : 0;
  if (!companyLoadAllowed(opts.currentBytes, opts.allow)) {
    return {
      status: "tiles-only",
      rows: parsed.rows.length + orgs.locations.length,
      locations: 0,
      tiles,
      databaseBytes: opts.currentBytes,
      gap: `companies: database is ${formatMb(opts.currentBytes)} (pg_database_size), over ${formatMb(BUDGET_BYTES)}. Rows were not inserted. Tiles were written. Re-run with: npm run db:load -- --include=companies --allow-over-budget=companies`,
    };
  }
  await writeOrganizationEntities(db, orgs.drafts);
  const loaded = await loadCompanyRows(db, inputs, names);
  const orgLoaded = await loadCompanyRows(db, orgs.locations, names);
  return {
    status: "applied",
    rows: parsed.rows.length + orgs.locations.length,
    locations: loaded.locations + orgLoaded.locations,
    tiles,
    databaseBytes: opts.currentBytes,
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
