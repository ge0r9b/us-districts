import { createHash } from "node:crypto";
import type pg from "pg";
import { normalizeAddress, placeChain, type PlaceChain } from "@usd/core";

export type GeocodeDeps = {
  pool: pg.Pool;
  fetchImpl?: typeof fetch;
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
};

export type LocateHit = {
  dv: number;
  point: { lon: number; lat: number };
  units: Record<string, string>;
  chain: PlaceChain;
};

type Point = { lon: number; lat: number; provider: string; match: string };

const CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies";
const NOMINATIM = "https://nominatim.openstreetmap.org/search";
const USER_AGENT = "us-districts-v3/0.1 (local dev; +https://github.com/ge0r9b/us-districts)";
const BUDGET_MS = 2500;

let nextNominatimAt = 0;

export function parseAddressParts(q: string): { street: string; city: string; state: string; zip: string } | null {
  const match = /^(.*?),\s*([^,]+),\s*([A-Za-z]{2})\s*(\d{5})?(?:-\d{4})?$/.exec(q.trim());
  if (!match?.[1] || !match[2] || !match[3]) return null;
  return { street: match[1].trim(), city: match[2].trim(), state: match[3].toUpperCase(), zip: match[4] ?? "" };
}

function hashAddress(normalized: string): Buffer {
  return createHash("sha256").update(normalized).digest();
}

function coordsFromCensus(body: unknown): Point | null {
  const matches = (body as { result?: { addressMatches?: { coordinates?: { x?: number; y?: number } }[] } })?.result
    ?.addressMatches;
  const c = matches?.[0]?.coordinates;
  if (c?.x == null || c.y == null) return null;
  return { lon: c.x, lat: c.y, provider: "census", match: "exact" };
}

async function census(
  url: string,
  fetchImpl: typeof fetch,
  signal: AbortSignal,
): Promise<Point | null> {
  const res = await fetchImpl(url, { signal, headers: { accept: "application/json" } });
  if (!res.ok) return null;
  return coordsFromCensus(await res.json());
}

async function nominatim(
  q: string,
  fetchImpl: typeof fetch,
  signal: AbortSignal,
  sleep: (ms: number) => Promise<void>,
): Promise<Point | null> {
  const wait = nextNominatimAt - Date.now();
  if (wait > 0) await sleep(wait);
  nextNominatimAt = Date.now() + 1000;
  const url = `${NOMINATIM}?format=jsonv2&limit=1&q=${encodeURIComponent(q)}`;
  const res = await fetchImpl(url, { signal, headers: { accept: "application/json", "user-agent": USER_AGENT } });
  if (!res.ok) return null;
  const body = (await res.json()) as { lon?: string; lat?: string }[];
  const hit = body[0];
  if (!hit?.lon || !hit.lat) return null;
  return { lon: Number(hit.lon), lat: Number(hit.lat), provider: "nominatim", match: "fallback" };
}

export async function locatePoint(pool: pg.Pool, lon: number, lat: number, dv: number): Promise<LocateHit> {
  const roundedLon = Math.round(lon * 1e5) / 1e5;
  const roundedLat = Math.round(lat * 1e5) / 1e5;
  const found = await pool.query<{ unit_type: string; unit_key: string; state_abbr: string | null; name: string | null }>(
    `with p as (select st_setsrid(st_makepoint($1, $2), 4326) g)
     select u.unit_type, u.unit_key, btrim(u.state_abbr) state_abbr, u.name
     from p
     join unit_geom ug on ug.lod = 0 and st_covers(ug.geom, p.g)
     join unit u on u.id = ug.unit_id
     join boundary_set b on b.id = u.boundary_set_id and b.is_current and b.visibility = 'public'
     order by u.unit_type, u.unit_key`,
    [roundedLon, roundedLat],
  );
  const units: Record<string, string> = {};
  for (const row of found.rows) {
    if (!units[row.unit_type]) units[row.unit_type] = row.unit_key;
  }
  return { dv, point: { lon: roundedLon, lat: roundedLat }, units, chain: placeChain(found.rows) };
}

/**
 * Census one-line, then Census components when the query parses, then Nominatim.
 * The point then goes through locatePoint, which is the PostGIS ST_Covers point-in-polygon.
 * A cache hit skips providers. A 5-digit ZIP never calls a provider (no ZCTA table in alpha.1).
 */
export async function geocodeAddress(
  deps: GeocodeDeps,
  q: string,
  dv: number,
): Promise<
  | { ok: true; body: LocateHit & { query: string; match: string; provider: string | null } }
  | { ok: false; status: number; code: string; message: string }
> {
  const normalized = normalizeAddress(q);
  if (!normalized) return { ok: false, status: 400, code: "empty_query", message: "Missing q" };
  if (/^\d{5}$/.test(normalized)) {
    const zcta = await deps.pool.query(`select 1 from zcta_unit_share where zcta = $1 limit 1`, [normalized]);
    if (zcta.rows.length === 0) {
      return { ok: false, status: 404, code: "no_zcta", message: "ZIP is not in the local ZCTA table" };
    }
  }
  const digest = hashAddress(normalized);
  const cached = await deps.pool.query<{ provider: string; lon: number; lat: number; match_quality: string }>(
    `select provider, lon, lat, match_quality from geocode_cache where query_hash = $1`,
    [digest],
  );
  let point: Point | null = cached.rows[0]
    ? {
        lon: cached.rows[0].lon,
        lat: cached.rows[0].lat,
        provider: cached.rows[0].provider,
        match: cached.rows[0].match_quality,
      }
    : null;
  if (!point) {
    const fetchImpl = deps.fetchImpl ?? fetch;
    const sleep = deps.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    const started = (deps.now ?? Date.now)();
    const signal = () => AbortSignal.timeout(Math.max(1, BUDGET_MS - ((deps.now ?? Date.now)() - started)));
    try {
      point = await census(
        `${CENSUS}/onelineaddress?address=${encodeURIComponent(q)}&benchmark=Public_AR_Current&vintage=Current_Current&format=json`,
        fetchImpl,
        signal(),
      );
      if (!point) {
        const parts = parseAddressParts(q);
        if (parts) {
          const params = new URLSearchParams({
            street: parts.street,
            city: parts.city,
            state: parts.state,
            zip: parts.zip,
            benchmark: "Public_AR_Current",
            vintage: "Current_Current",
            format: "json",
          });
          point = await census(`${CENSUS}/address?${params}`, fetchImpl, signal());
        }
      }
      if (!point) point = await nominatim(q, fetchImpl, signal(), sleep);
    } catch {
      point = point ?? null;
    }
    if (!point) return { ok: false, status: 404, code: "no_match", message: "No geocoder match" };
    await deps.pool.query(
      `insert into geocode_cache (query_hash, provider, lon, lat, match_quality)
       values ($1, $2, $3, $4, $5)
       on conflict (query_hash) do nothing`,
      [digest, point.provider, point.lon, point.lat, point.match],
    );
  }
  const located = await locatePoint(deps.pool, point.lon, point.lat, dv);
  return { ok: true, body: { ...located, query: q, match: point.match, provider: point.provider } };
}
