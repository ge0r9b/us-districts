import { existsSync } from "node:fs";
import { join } from "node:path";
import type pg from "pg";
import { insertJsonChunks } from "./batch.ts";
import { parseCsv, readFileText } from "./csv.ts";

/** colleges_us.csv at data/companies 7022011. */
export const COLLEGE_ROWS = 5_731;
/** Rows whose entity_id is ipeds:<UNITID>. */
export const COLLEGE_IPEDS_ROWS = 2_450;
export const AIRLINE_ROWS = 5_888;
export const AIRLINE_HQ_ROWS = 3_911;
export const TELECOM_ROWS = 2_954;
export const TELECOM_HQ_ROWS = 2_098;

export const ORG_LOCATION_ROWS = COLLEGE_ROWS + AIRLINE_HQ_ROWS + TELECOM_HQ_ROWS;
export const ORG_ENTITY_ROWS = COLLEGE_ROWS + AIRLINE_ROWS + TELECOM_ROWS;
/** Entity row plus indexes, beside the 520-byte location estimate. */
export const EST_ORG_ENTITY_BYTES = 365;

export const ORG_REL = {
  colleges: "data-v3/institutions/companies/organizations/colleges_us.csv",
  collegeLocations: "data-v3/institutions/companies/organizations/colleges_us_locations.csv",
  airlines: "data-v3/institutions/companies/organizations/airlines_world.csv",
  airlineLocations: "data-v3/institutions/companies/organizations/airlines_world_locations.csv",
  telecoms: "data-v3/institutions/companies/organizations/telecoms_world.csv",
  telecomLocations: "data-v3/institutions/companies/organizations/telecoms_world_locations.csv",
} as const;

export const ORG_FILES = Object.values(ORG_REL);

const QID = /^wikidata:Q[0-9]+$/;
const USD_ID = /^usd:[0-9a-f-]{36}$/;
const IPEDS_ID = /^ipeds:[0-9]{6}$/;
const UNITID = /^[0-9]{6}$/;
export const ORG_ENTITY_ID = /^(wikidata:Q[0-9]+|ipeds:[0-9]{6})$/;

const KINDS = new Set(["brand", "organization", "company", "nonprofit", "fund"]);

const COLLEGE_META = [
  "unitid", "opeid", "ein", "sector", "sector_label", "level", "degree_granting",
  "highest_offering", "carnegie_basic", "carnegie_basic_label", "hbcu", "tribal",
  "land_grant", "system_name", "system_unitid", "control", "website",
];
const AIRLINE_META = [
  "iata", "icao", "callsign", "active", "description", "hubs", "openflights_id",
  "website", "instance_of", "country",
];
const TELECOM_META = [
  "service_type", "mcc", "mnc", "active", "corporate_name", "description",
  "instance_of", "website",
];

export type IdMerge = {
  from_id: string;
  into_id: string;
  match_rule: "usd_to_qid" | "ipeds_to_qid";
};

/** Re-key a reserved id onto a Wikidata item. The old id stays; it is not deleted. */
export function planIdMerge(fromId: string, intoId: string): IdMerge | null {
  const from = fromId.trim();
  const into = intoId.trim();
  if (!QID.test(into) || from === into) return null;
  if (USD_ID.test(from)) return { from_id: from, into_id: into, match_rule: "usd_to_qid" };
  if (IPEDS_ID.test(from)) return { from_id: from, into_id: into, match_rule: "ipeds_to_qid" };
  return null;
}

/** Six-digit UNITID from the column, or from an ipeds: entity id. */
export function ipedsUnit(entityId: string, unitid: string | undefined): string | null {
  const raw = (unitid ?? "").trim();
  if (UNITID.test(raw)) return raw;
  const match = /^ipeds:([0-9]{6})$/.exec(entityId.trim());
  return match?.[1] ?? null;
}

export type OrgLogo = {
  file: string | null;
  license: string;
  fair_use: boolean;
  public: boolean;
  attribution: string;
  source_url: string | null;
};

/**
 * A public logo needs attribution and a free licence.
 * A hidden logo needs attribution and a source URL.
 * Anything else is skipped. No image bytes are downloaded.
 */
export function mapOrgLogo(row: {
  logo_file?: string;
  logo_license?: string;
  logo_attribution?: string;
  logo_source_url?: string;
}): OrgLogo | null {
  const file = (row.logo_file ?? "").trim() || null;
  const licenseRaw = (row.logo_license ?? "").trim();
  const attribution = (row.logo_attribution ?? "").trim();
  const sourceUrl = (row.logo_source_url ?? "").trim() || null;
  if (!file && !licenseRaw && !attribution) return null;
  const fair = /fair/i.test(licenseRaw) || licenseRaw.toLowerCase() === "fair-use";
  if (!fair && attribution && licenseRaw && licenseRaw.toLowerCase() !== "fair-use") {
    return { file, license: licenseRaw, fair_use: false, public: true, attribution, source_url: sourceUrl };
  }
  if (attribution && sourceUrl) {
    return {
      file,
      license: licenseRaw || "fair-use",
      fair_use: true,
      public: false,
      attribution,
      source_url: sourceUrl,
    };
  }
  return null;
}

/** Company inception may be a year. Dates before 2016 stay. Institutions use a different cut. */
export function orgDate(raw: string | undefined): { date: string | null; precision: "day" | "month" | "year" | null } {
  const text = (raw ?? "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return { date: text, precision: "day" };
  if (/^\d{4}-\d{2}$/.test(text)) return { date: `${text}-01`, precision: "month" };
  if (/^\d{4}$/.test(text)) return { date: `${text}-01-01`, precision: "year" };
  return { date: null, precision: null };
}

export type OrgDraft = {
  entity_id: string;
  kind: string;
  name: string;
  brand_name: string | null;
  country: string | null;
  meta: Record<string, string>;
  inception: string | null;
  inception_precision: "day" | "month" | "year" | null;
  inception_source: string | null;
  valid_to: string | null;
  aliases: { alias: string; entity_id: string; kind: string; scheme: string }[];
  parents: string[];
  merge: IdMerge | null;
  logo: OrgLogo | null;
};

export type OrgLocation = {
  location_id: string;
  entity_id: string;
  role: string;
  name: string;
  address: string;
  geoid: string;
  boundary_set: string;
  lat: string;
  lon: string;
  source_id: string;
  retrieved_at: string;
  brand_name: string;
  country_code: string;
};

export type OrgBundle = {
  drafts: OrgDraft[];
  locations: OrgLocation[];
};

/** Outside the US, boundary_set stays empty. The point still renders. */
export function boundaryForCountry(country: string | null, boundary: string | undefined): string {
  if (country && country !== "US") return "";
  return (boundary ?? "").trim();
}

function countryCode(raw: string | undefined): string | null {
  const code = (raw ?? "").trim().toUpperCase();
  return /^[A-Z]{2}$/.test(code) ? code : null;
}

function metaOf(row: Record<string, string>, keys: readonly string[]): Record<string, string> {
  const meta: Record<string, string> = {};
  for (const key of keys) {
    const value = (row[key] ?? "").trim();
    if (value) meta[key] = value;
  }
  return meta;
}

function linkedId(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  if (ORG_ENTITY_ID.test(text)) return text;
  if (/^Q[0-9]+$/.test(text)) return `wikidata:${text}`;
  return null;
}

function draftBase(row: Record<string, string>, name: string, metaKeys: readonly string[]): OrgDraft | null {
  const entityId = (row.entity_id ?? "").trim();
  const kind = (row.kind ?? "").trim();
  if (!ORG_ENTITY_ID.test(entityId) || !KINDS.has(kind) || !name) return null;
  const country = countryCode(row.country_code);
  const started = orgDate(row.inception);
  const ended = orgDate(row.dissolved);
  return {
    entity_id: entityId,
    kind,
    name,
    brand_name: (row.brand_name ?? "").trim() || null,
    country: country && country !== "US" ? country.toLowerCase() : null,
    meta: metaOf(row, metaKeys),
    inception: started.date,
    inception_precision: started.date ? started.precision : null,
    inception_source: started.date ? "wikidata:P571" : null,
    valid_to: ended.date,
    aliases: [],
    parents: [],
    merge: null,
    logo: mapOrgLogo(row),
  };
}

export function mapCollege(row: Record<string, string>): OrgDraft | null {
  const draft = draftBase(row, (row.name ?? "").trim(), COLLEGE_META);
  if (!draft) return null;
  const unit = ipedsUnit(draft.entity_id, row.unitid);
  if (unit) {
    draft.aliases.push({ alias: unit, entity_id: draft.entity_id, kind: "external_id", scheme: "ipeds" });
  }
  const into = linkedId(row.wikidata_qid);
  if (into) draft.merge = planIdMerge(draft.entity_id, into);
  for (const key of ["system_entity_id", "main_campus_entity_id"]) {
    const parent = linkedId(row[key]);
    if (parent && parent !== draft.entity_id) draft.parents.push(parent);
  }
  return draft;
}

export function mapAirline(row: Record<string, string>): OrgDraft | null {
  const draft = draftBase(row, (row.name ?? "").trim(), AIRLINE_META);
  if (!draft) return null;
  const parent = linkedId(row.parent_entity_id);
  if (parent && parent !== draft.entity_id) draft.parents.push(parent);
  return draft;
}

export function mapTelecom(row: Record<string, string>): OrgDraft | null {
  const name = (row.brand_name ?? "").trim() || (row.corporate_name ?? "").trim() || (row.entity_id ?? "").trim();
  const draft = draftBase(row, name, TELECOM_META);
  if (!draft) return null;
  draft.brand_name = (row.brand_name ?? "").trim() || draft.name;
  for (const key of ["corporate_qid", "ultimate_parent_qid"]) {
    const parent = linkedId(row[key]);
    if (parent && parent !== draft.entity_id) draft.parents.push(parent);
  }
  return draft;
}

export function mapOrgLocation(row: Record<string, string>): OrgLocation | null {
  const locationId = (row.location_id ?? "").trim();
  const entityId = (row.entity_id ?? "").trim();
  if (!locationId || !ORG_ENTITY_ID.test(entityId)) return null;
  const country = countryCode(row.country_code);
  const role = (row.role ?? "").trim() === "hq_in" ? "hq_in" : "establishment_at";
  return {
    location_id: locationId,
    entity_id: entityId,
    role,
    name: (row.name ?? "").trim(),
    address: (row.address ?? "").trim(),
    geoid: (row.geoid ?? "").trim(),
    boundary_set: boundaryForCountry(country, row.boundary_set),
    lat: (row.lat ?? "").trim(),
    lon: (row.lon ?? "").trim(),
    source_id: (row.source_id ?? row.source ?? "").trim() || "companies-bot",
    retrieved_at: (row.retrieved_at ?? row.source_date ?? "").trim(),
    brand_name: (row.brand_name ?? row.name ?? "").trim(),
    country_code: country ?? "",
  };
}

function readRows(dir: string, rel: string): Record<string, string>[] {
  const path = join(dir, rel);
  if (!existsSync(path)) return [];
  return parseCsv(readFileText(path).text).rows;
}

export function readOrganizationBundle(dir: string): OrgBundle {
  const drafts: OrgDraft[] = [];
  const seen = new Set<string>();
  const take = (row: OrgDraft | null) => {
    if (!row || seen.has(row.entity_id)) return;
    seen.add(row.entity_id);
    drafts.push(row);
  };
  for (const row of readRows(dir, ORG_REL.colleges)) take(mapCollege(row));
  for (const row of readRows(dir, ORG_REL.airlines)) take(mapAirline(row));
  for (const row of readRows(dir, ORG_REL.telecoms)) take(mapTelecom(row));
  const locations: OrgLocation[] = [];
  const seenLoc = new Set<string>();
  for (const rel of [ORG_REL.collegeLocations, ORG_REL.airlineLocations, ORG_REL.telecomLocations]) {
    for (const row of readRows(dir, rel)) {
      const mapped = mapOrgLocation(row);
      if (!mapped || seenLoc.has(mapped.location_id)) continue;
      seenLoc.add(mapped.location_id);
      locations.push(mapped);
    }
  }
  return { drafts, locations };
}

export async function writeOrganizationEntities(
  db: pg.Pool,
  drafts: readonly OrgDraft[],
): Promise<{ entities: number; aliases: number; relations: number; images: number; merges: number }> {
  if (drafts.length === 0) return { entities: 0, aliases: 0, relations: 0, images: 0, merges: 0 };
  const entities = drafts.map((row) => ({
    entity_id: row.entity_id,
    kind: row.kind,
    name: row.name,
    country: row.country ?? "",
    brand_name: row.brand_name,
    meta: row.meta,
    inception: row.inception,
    inception_precision: row.inception_precision,
    inception_source: row.inception_source,
    valid_to: row.valid_to,
  }));
  const aliases = drafts.flatMap((row) => row.aliases);
  const relations = drafts.flatMap((row) =>
    row.parents.map((parent) => ({ parent_id: parent, child_id: row.entity_id })),
  );
  const images = drafts.flatMap((row) =>
    row.logo
      ? [{
          entity_id: row.entity_id,
          file: row.logo.file,
          license: row.logo.license,
          fair_use: row.logo.fair_use,
          public: row.logo.public,
          attribution: row.logo.attribution,
          source_url: row.logo.source_url,
        }]
      : [],
  );
  const merges = drafts.flatMap((row) => (row.merge ? [row.merge] : []));
  const mergeAliases = merges.map((row) => ({
    alias: row.from_id,
    entity_id: row.into_id,
    kind: "merged_id",
    scheme: row.match_rule === "ipeds_to_qid" ? "ipeds" : "usd",
  }));
  const client = await db.connect();
  try {
    await client.query("begin");
    await client.query(
      `insert into source (source_id, title) values ('companies-bot', 'companies') on conflict (source_id) do nothing`,
    );
    const entityWrites = await insertJsonChunks(
      client,
      `insert into entity (
         entity_id, kind, name, origin, country, brand_name, source_record_id, meta,
         inception, inception_precision, inception_source, valid_to
       )
       select entity_id, kind, name, 'companies_bot', nullif(country, ''), brand_name, entity_id, meta,
              inception, inception_precision, inception_source, valid_to
       from jsonb_to_recordset($1::jsonb) as x(
         entity_id text, kind text, name text, country text, brand_name text, meta jsonb,
         inception date, inception_precision text, inception_source text, valid_to date
       )
       on conflict (entity_id) do update
         set kind = excluded.kind, name = excluded.name, brand_name = excluded.brand_name,
             country = excluded.country, meta = excluded.meta,
             inception = excluded.inception, inception_precision = excluded.inception_precision,
             inception_source = excluded.inception_source, valid_to = excluded.valid_to
         where entity.origin = 'companies_bot'`,
      entities,
    );
    const aliasWrites = aliases.length
      ? await insertJsonChunks(
          client,
          `insert into entity_alias (alias, entity_id, kind, scheme, source_id)
           select alias, entity_id, kind, scheme, 'companies-bot'
           from jsonb_to_recordset($1::jsonb) as x(alias text, entity_id text, kind text, scheme text)
           on conflict (alias, entity_id) where entity_id is not null do nothing`,
          aliases,
        )
      : 0;
    const relationWrites = relations.length
      ? await insertJsonChunks(
          client,
          `insert into entity_relation (parent_nid, child_nid, relation, source_id, source_record_id)
           select p.nid, c.nid, 'parent_org', 'companies-bot', x.child_id || '|parent_org|' || x.parent_id
           from jsonb_to_recordset($1::jsonb) as x(parent_id text, child_id text)
           join entity p on p.entity_id = x.parent_id
           join entity c on c.entity_id = x.child_id
           on conflict (parent_nid, child_nid, relation, valid_from) do nothing`,
          relations,
        )
      : 0;
    const imageWrites = images.length
      ? await insertJsonChunks(
          client,
          `insert into entity_image (
             entity_id, role, file, license, fair_use, public, attribution, source_url, icon
           )
           select entity_id, 'logo', file, license, fair_use, public, attribution, source_url, false
           from jsonb_to_recordset($1::jsonb) as x(
             entity_id text, file text, license text, fair_use boolean, public boolean,
             attribution text, source_url text
           )
           on conflict (entity_id, feed_entity_id, role) do update
             set file = excluded.file, license = excluded.license, fair_use = excluded.fair_use,
                 public = excluded.public, attribution = excluded.attribution, source_url = excluded.source_url`,
          images,
        )
      : 0;
    const mergeWrites = merges.length
      ? await insertJsonChunks(
          client,
          `insert into entity_merge (from_id, into_id, match_confidence, match_rule, decided_by)
           select x.from_id, x.into_id, 1, x.match_rule, 'auto'
           from jsonb_to_recordset($1::jsonb) as x(from_id text, into_id text, match_rule text)
           join entity e on e.entity_id = x.into_id
           on conflict (from_id) do nothing`,
          merges,
        )
      : 0;
    if (mergeAliases.length > 0) {
      await insertJsonChunks(
        client,
        `insert into entity_alias (alias, entity_id, kind, scheme, source_id)
         select x.alias, x.entity_id, x.kind, x.scheme, 'companies-bot'
         from jsonb_to_recordset($1::jsonb) as x(alias text, entity_id text, kind text, scheme text)
         join entity e on e.entity_id = x.entity_id
         on conflict (alias, entity_id) where entity_id is not null do nothing`,
        mergeAliases,
      );
    }
    if (entityWrites + aliasWrites + relationWrites + imageWrites + mergeWrites > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query("commit");
    return {
      entities: entities.length,
      aliases: aliasWrites,
      relations: relationWrites,
      images: imageWrites,
      merges: mergeWrites,
    };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}
