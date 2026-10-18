import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import type pg from "pg";
import { markSuperseded, sha256Hex } from "./apply.ts";
import { insertJsonChunks } from "./batch.ts";
import { fetchOrigin, needsRefresh, originCommit, stampCommit } from "./branch-cache.ts";
import { BUDGET_BYTES, formatMb, loadGrowthRefused } from "./budget.ts";
import { sideTableBytes } from "../db/vacuum.ts";
import { parseCsv, readFileText } from "./csv.ts";
import {
  imagePackKey,
  instPacksRoot,
  mergeInstPack,
  readInstPack,
  writeFeedMapPack,
  writeInstPack,
  type FeedEnum,
  type FeedMapPackRow,
  type InstPack,
} from "./inst-pack.ts";
import {
  MEASURED_ENTITY_DEAD_TUPLES,
  MEASURED_ENTITY_HEAP_BYTES,
  MEASURED_ENTITY_INDEX_BYTES,
  MEASURED_INSTITUTION_DELTA_BYTES,
  MEASURED_TOAST_BYTES,
  FOREIGN_GOVERNMENT_BYTES_PER_ROW,
  SLIM_ALIAS_BYTES_PER_ROW,
  SLIM_BODY_BYTES_PER_ROW,
  SLIM_ENTITY_BYTES_PER_ROW,
  SLIM_IMAGE_BYTES_PER_ROW,
  SLIM_RELATION_BYTES_PER_ROW,
  slimInstitutionBytes,
} from "./size-plan.ts";

const RELATION_INSERT = `insert into entity_relation (parent_nid, child_nid, relation, method, source_id, source_set, source_record_id)
 select p.nid, c.nid, x.relation, x.method, x.source_id, x.source_set, x.source_record_id
 from jsonb_to_recordset($1::jsonb) as x(
   parent_id text, child_id text, relation text, method text, source_id text, source_set text, source_record_id text
 )
 join entity p on p.entity_id = x.parent_id
 join entity c on c.entity_id = x.child_id
 on conflict (parent_nid, child_nid, relation, valid_from) do update
   set method = excluded.method, source_id = excluded.source_id, source_set = excluded.source_set,
       source_record_id = excluded.source_record_id
   where entity_relation.method is distinct from excluded.method
      or entity_relation.source_id is distinct from excluded.source_id
      or entity_relation.source_set is distinct from excluded.source_set
      or entity_relation.source_record_id is distinct from excluded.source_record_id`;

const WIKIDATA = /^wikidata:Q[0-9]+$/;
const BARE_Q = /^Q[0-9]+$/;
const ROLES = new Set(["seal", "flag", "logo"]);

/**
 * entities.csv `wikidata` at data/inst-entities 1fde48d is already `wikidata:Q…`.
 * entity_images.csv `wikidata_qid` is still a bare `Q…` in that commit. A bare id
 * is prefixed once. A value that already has the prefix is kept as-is.
 */
export function wikidataId(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  if (!text) return null;
  if (WIKIDATA.test(text)) return text;
  if (BARE_Q.test(text)) return `wikidata:${text}`;
  return null;
}

export type InstRelationRow = {
  entity_id: string;
  relation: string;
  related_entity_id: string;
  method?: string;
  source_id?: string;
  source_set?: string;
};

const RELATION_METHODS = new Set(["sourced", "overlay", "point_in_polygon", "manual"]);

export type RelationMethod = "sourced" | "overlay" | "point_in_polygon" | "manual";

/**
 * The file's method is empty, one of the schema values, or a source token such as
 * `tceq_wdd_primary_county`. A token is stored as `sourced`, and the raw text is
 * kept on source_record_id. An empty method stays null.
 */
export function mapRelationMethod(raw: string | undefined): { method: RelationMethod | null; token: string | null } {
  const text = (raw ?? "").trim();
  if (!text) return { method: null, token: null };
  if (RELATION_METHODS.has(text)) return { method: text as RelationMethod, token: null };
  return { method: "sourced", token: text };
}

export type InstRelationName =
  | "parent"
  | "consolidated_with"
  | "in_county"
  | "member_of"
  | "area"
  | "predecessor";

export type MappedRelation = {
  parent_id: string;
  child_id: string;
  relation: InstRelationName;
  method: RelationMethod | null;
  source_id: string | null;
  source_set: string | null;
  source_record_id: string;
};

function firstSource(raw: string | undefined): string | null {
  const id = (raw ?? "").split(";")[0]?.trim() ?? "";
  return id || null;
}

function sourceList(raw: string | undefined): string[] {
  const ids = (raw ?? "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
  return [...new Set(ids)];
}

/**
 * `entity_relations.csv`: `parent` means entity_id is the child and related_entity_id
 * is the parent. That parent is written to `entity.parent_id` and to `entity_relation`.
 * `consolidated_with` keeps entity_id as the parent (the county) and does not set parent_id.
 * `in_county` means entity_id is the special district and related_entity_id is the county.
 * It does not change `entity.parent_id` (the district's parent is still the state).
 * `member_of` is the member (entity_id) and the body (related_entity_id). Method is sourced.
 * `area` is the council (entity_id) and the area it governs. `predecessor` points at the
 * entity this one replaced. None of those three change `entity.parent_id`.
 */
export function mapInstRelations(rows: InstRelationRow[]): {
  relations: MappedRelation[];
  parents: { entity_id: string; parent_id: string }[];
  skipped: number;
} {
  const relations: MappedRelation[] = [];
  const parents: { entity_id: string; parent_id: string }[] = [];
  let skipped = 0;
  const seenParent = new Set<string>();
  for (const row of rows) {
    const child = row.entity_id.trim();
    const related = row.related_entity_id.trim();
    const relation = row.relation.trim();
    if (!child || !related || child === related) {
      skipped++;
      continue;
    }
    const hash = sourceSetHash(row.source_set);
    const sourceId = hash ? null : firstSource(row.source_id);
    const mappedMethod = mapRelationMethod(row.method);
    const record = (parentId: string, childId: string, name: MappedRelation["relation"]) => {
      const token = mappedMethod.token ? `|method:${mappedMethod.token}` : "";
      relations.push({
        parent_id: parentId,
        child_id: childId,
        relation: name,
        method: mappedMethod.method,
        source_id: sourceId,
        source_set: hash,
        source_record_id: `${childId}|${name}|${parentId}${token}`,
      });
    };
    if (relation === "parent") {
      record(related, child, "parent");
      if (!seenParent.has(child)) {
        seenParent.add(child);
        parents.push({ entity_id: child, parent_id: related });
      }
      continue;
    }
    if (relation === "consolidated_with") {
      record(child, related, "consolidated_with");
      continue;
    }
    if (relation === "in_county") {
      record(related, child, "in_county");
      continue;
    }
    if (relation === "member_of") {
      record(related, child, "member_of");
      continue;
    }
    if (relation === "area") {
      record(child, related, "area");
      continue;
    }
    if (relation === "predecessor") {
      record(related, child, "predecessor");
      continue;
    }
    skipped++;
  }
  return { relations, parents, skipped };
}

export type MappedImage = {
  entity_id: string | null;
  feed_entity_id: string | null;
  role: "seal" | "flag" | "logo";
  file: string | null;
  file_url: string | null;
  license: string;
  licence_url: string | null;
  fair_use: boolean;
  public: boolean;
  icon: boolean;
  usage_basis: string | null;
  attribution: string | null;
  source_url: string | null;
  note: string | null;
  wikidata: string | null;
  retrieved_at: string | null;
  source_ids: string[];
  source_set: string | null;
};

function yes(raw: string | undefined): boolean {
  const text = (raw ?? "").trim().toLowerCase();
  return text === "yes" || text === "true" || text === "1";
}

function orNull(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return text || null;
}

/**
 * entity_images.csv: `role`, `file`, `feed_id`, plus `public` and `icon`.
 * Older names (`image_kind`, `commons_file`, `feed_entity_id`) still map.
 * A public row needs a free licence and attribution. A hidden row needs
 * attribution and a source URL. Rows that cannot satisfy either check are
 * skipped. No image bytes are downloaded. An icon has to be public.
 */
export function mapInstImage(row: Record<string, string>): MappedImage | null {
  const role = (row.role ?? row.image_kind ?? "").trim();
  if (!ROLES.has(role)) return null;
  const entityId = orNull(row.entity_id);
  const feedId = orNull(row.feed_id ?? row.feed_entity_id);
  if (!entityId && !feedId) return null;
  const fairUse = yes(row.fair_use);
  const attribution = orNull(row.attribution);
  const sourceUrl = orNull(row.source_url);
  const commonsUrl = orNull(row.commons_url ?? row.file_url);
  const licenseRaw = (row.license ?? "").trim();
  const license = licenseRaw || (fairUse ? "fair-use" : "unknown");
  const askedPublic = row.public != null && row.public.trim() !== "" ? yes(row.public) : !fairUse;
  const isPublic =
    askedPublic && !fairUse && attribution != null && licenseRaw !== "" && licenseRaw.toLowerCase() !== "fair-use";
  if (!isPublic && (attribution == null || sourceUrl == null)) return null;
  const icon = yes(row.icon) && isPublic;
  return {
    entity_id: entityId,
    feed_entity_id: feedId,
    role: role as MappedImage["role"],
    file: orNull(row.file ?? row.commons_file),
    file_url: commonsUrl && commonsUrl !== sourceUrl ? commonsUrl : null,
    license,
    licence_url: orNull(row.licence_url),
    fair_use: fairUse,
    public: isPublic,
    icon,
    usage_basis: orNull(row.usage_basis),
    attribution,
    source_url: sourceUrl,
    note: orNull(row.note),
    wikidata: wikidataId(row.wikidata ?? row.wikidata_qid),
    retrieved_at: orNull(row.retrieved_at),
    source_ids: sourceList(row.source_id),
    source_set: sourceSetHash(row.source_set),
  };
}

/** At most one icon per entity. Extra icons stay as ordinary images. */
export function dedupeIcons(images: MappedImage[]): MappedImage[] {
  const seen = new Set<string>();
  return images.map((row) => {
    if (!row.icon) return row;
    const key = row.entity_id ?? row.feed_entity_id ?? "";
    if (seen.has(key)) return { ...row, icon: false };
    seen.add(key);
    return row;
  });
}

function imagePayload(row: MappedImage): Record<string, unknown> {
  return {
    entity_id: row.entity_id ?? "",
    feed_entity_id: row.feed_entity_id ?? "",
    role: row.role,
    file: row.file,
    file_url: row.file_url,
    license: row.license,
    fair_use: row.fair_use,
    public: row.public,
    icon: row.icon,
    wikidata: row.wikidata,
    retrieved_at: row.retrieved_at,
    attribution: row.attribution,
    source_url: row.source_url,
    usage_basis: row.usage_basis,
    note: row.note,
    source_set: row.source_set,
  };
}

/** Licence deeds are one `license` row. Attribution is the institution pack, not a second table. */
async function writeImageRows(client: pg.PoolClient, ready: MappedImage[]): Promise<number> {
  if (ready.length === 0) return 0;
  const licences = new Map<string, string | null>();
  for (const row of ready) {
    if (!licences.has(row.license) || (row.licence_url && !licences.get(row.license))) {
      licences.set(row.license, row.licence_url);
    }
  }
  await insertJsonChunks(
    client,
    `insert into license (code, name, url)
     select code, code, url
     from jsonb_to_recordset($1::jsonb) as x(code text, url text)
     on conflict (code) do update
       set url = excluded.url
       where excluded.url is not null and license.url is distinct from excluded.url`,
    [...licences].map(([code, url]) => ({ code, url })),
  );
  const written = await insertJsonChunks(
    client,
    `insert into entity_image (
       entity_id, feed_entity_id, role, file, file_url, license, fair_use, public, icon, wikidata, retrieved_at, source_set
     )
     select nullif(entity_id, ''), nullif(feed_entity_id, ''), role, file, file_url, license,
            fair_use, public, icon, wikidata, retrieved_at, source_set
     from jsonb_to_recordset($1::jsonb) as x(
       entity_id text, feed_entity_id text, role text, file text, file_url text, license text,
       fair_use boolean, public boolean, icon boolean, wikidata text, retrieved_at timestamptz, source_set text
     )
     on conflict (entity_id, feed_entity_id, role) do update
       set file = excluded.file, file_url = excluded.file_url, license = excluded.license,
           fair_use = excluded.fair_use, public = excluded.public, icon = excluded.icon,
           wikidata = excluded.wikidata, attribution = null, source_url = null, usage_basis = null,
           source_set = excluded.source_set`,
    ready.map(imagePayload),
  );
  return written;
}

async function ensureSources(
  db: pg.PoolClient,
  ids: string[],
  titles?: Map<string, string>,
): Promise<void> {
  const unique = [...new Set(ids.filter(Boolean))];
  if (unique.length === 0) return;
  await insertJsonChunks(
    db,
    `insert into source (source_id, title)
     select source_id, title
     from jsonb_to_recordset($1::jsonb) as x(source_id text, title text)
     on conflict (source_id) do nothing`,
    unique.map((source_id) => ({ source_id, title: titles?.get(source_id) || "inst-entities" })),
  );
}

async function writeEnum(
  client: pg.PoolClient,
  table: "enum_feed" | "enum_feed_map_status" | "enum_load_group",
  codeKey: "feed" | "status" | "load_group",
  rows: Record<string, string>[],
): Promise<void> {
  const payload = rows.flatMap((row) => {
    const code = feedCode(row[codeKey]);
    const name = (row.name ?? "").trim();
    if (code == null || !name) return [];
    return [{ code, name, description: blank(row.description) }];
  });
  if (payload.length === 0) return;
  await insertJsonChunks(
    client,
    `insert into ${table} (${codeKey}, name, description)
     select code, name, description
     from jsonb_to_recordset($1::jsonb) as x(code smallint, name text, description text)
     on conflict (${codeKey}) do update
       set name = excluded.name, description = excluded.description
       where ${table}.name is distinct from excluded.name
          or ${table}.description is distinct from excluded.description`,
    payload,
  );
}

async function writeSourceUrls(client: pg.PoolClient, rows: Record<string, string>[]): Promise<void> {
  const payload = rows.flatMap((row) => {
    const sourceId = (row.source_id ?? "").trim();
    const url = (row.url ?? "").trim();
    const ord = Number((row.ord ?? "").trim());
    if (!sourceId || !url || !Number.isInteger(ord) || ord < 1 || ord > 32767) return [];
    return [{ source_id: sourceId, ord, url, label: blank(row.label) }];
  });
  if (payload.length === 0) return;
  await insertJsonChunks(
    client,
    `insert into source_url (source_id, ord, url, label)
     select source_id, ord, url, label
     from jsonb_to_recordset($1::jsonb) as x(source_id text, ord smallint, url text, label text)
     on conflict (source_id, ord) do update
       set url = excluded.url, label = excluded.label
       where source_url.url is distinct from excluded.url
          or source_url.label is distinct from excluded.label`,
    payload,
  );
}

async function writeSourceSets(client: pg.PoolClient, rows: Record<string, string>[]): Promise<void> {
  const seen = new Set<string>();
  const payload = rows.flatMap((row) => {
    const sourceSet = sourceSetHash(row.source_set);
    const sourceId = (row.source_id ?? "").trim();
    const ord = Number((row.ord ?? "").trim());
    if (!sourceSet || !sourceId || !Number.isInteger(ord) || ord < 1 || ord > 32767) return [];
    const key = `${sourceSet}\0${ord}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{ source_set: sourceSet, ord, source_id: sourceId }];
  });
  if (payload.length === 0) return;
  await insertJsonChunks(
    client,
    `insert into source_set_member (source_set, ord, source_id)
     select source_set, ord, source_id
     from jsonb_to_recordset($1::jsonb) as x(source_set text, ord smallint, source_id text)
     on conflict (source_set, ord) do update
       set source_id = excluded.source_id
       where source_set_member.source_id is distinct from excluded.source_id`,
    payload,
  );
}

export async function applyInstRelations(
  db: pg.Pool,
  rows: InstRelationRow[],
): Promise<{ relations: number; parents: number; skipped: number }> {
  const mapped = mapInstRelations(rows);
  if (mapped.relations.length === 0) return { relations: 0, parents: 0, skipped: mapped.skipped };
  const client = await db.connect();
  try {
    await client.query("begin");
    await ensureSources(
      client,
      mapped.relations.map((row) => row.source_id ?? ""),
    );
    const written = await insertJsonChunks(client, RELATION_INSERT, mapped.relations);
    if (mapped.parents.length > 0) {
      await client.query(
        `update entity e set parent_id = x.parent_id
         from jsonb_to_recordset($1::jsonb) as x(entity_id text, parent_id text)
         where e.entity_id = x.entity_id and e.parent_id is distinct from x.parent_id`,
        [JSON.stringify(mapped.parents)],
      );
    }
    await client.query("commit");
    return { relations: written, parents: mapped.parents.length, skipped: mapped.skipped };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

export async function applyInstImages(
  db: pg.Pool,
  rows: Record<string, string>[],
): Promise<{ images: number; skipped: number }> {
  const images: MappedImage[] = [];
  let skipped = 0;
  for (const row of rows) {
    const mapped = mapInstImage(row);
    if (!mapped) {
      skipped++;
      continue;
    }
    images.push(mapped);
  }
  const ready = dedupeIcons(images);
  if (ready.length === 0) return { images: 0, skipped };
  const client = await db.connect();
  try {
    await client.query("begin");
    await ensureSources(
      client,
      ready.flatMap((row) => row.source_ids),
    );
    const written = await writeImageRows(client, ready);
    await client.query("commit");
    return { images: written, skipped };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

/** Manifest path on origin/data/inst-entities. The file itself is not a db batch. */
export const INST_MANIFEST = "data-v3/inst/load_manifest.csv";

/** Paths from load_manifest.csv. `db` is the Postgres batch. `pack` is archived and not inserted. `repo` is omitted. */
export function classifyManifest(rows: { file?: string; target?: string }[]): { db: string[]; pack: string[] } {
  const db: string[] = [];
  const pack: string[] = [];
  for (const row of rows) {
    const file = (row.file ?? "").trim();
    const target = (row.target ?? "").trim();
    if (!file || file.includes("..")) continue;
    const rel = file.startsWith("data-v3/") ? file : `data-v3/inst/${file}`;
    if (target === "db") db.push(rel);
    else if (target === "pack") pack.push(rel);
  }
  return { db, pack };
}

const ENTITY_KINDS = new Set([
  "nation", "territory", "province", "state", "county", "municipality", "township",
  "school_unified", "school_elementary", "school_secondary",
  "chamber", "dc_council", "subdivision", "court", "special_district", "indigenous_government",
  "local_authority", "regional_authority", "intermunicipal", "submunicipal", "parish",
  "government_other", "brand", "organization", "company", "nonprofit", "fund", "other",
]);

const BODY_ROLES = new Set(["council", "mayor", "chamber", "court", "board"]);
const PRECISIONS = new Set(["day", "month", "year"]);

export type InstitutionEstimate = {
  entities: number;
  relations: number;
  images: number;
  bodies: number;
  fileBytes: number;
  databaseBytes: number;
  projectedBytes: number | null;
  parts: { table: string; rows: number; bytesPerRow: number | null; bytes: number | null }[];
  note: string;
};

export type InstitutionLoadReport = {
  status: "applied" | "refused" | "dry-run";
  entities: number;
  relations: number;
  images: number;
  imagesSkipped: number;
  bodies: number;
  parents: number;
  estimate: InstitutionEstimate;
  gap: string | null;
  gitCommit: string | null;
};

type InstInputs = {
  entities: Record<string, string>[];
  relations: Record<string, string>[];
  images: Record<string, string>[];
  bodies: Record<string, string>[];
  geoids?: Record<string, string>[];
  sourceSets?: Record<string, string>[];
  sources?: Record<string, string>[];
  sourceUrls?: Record<string, string>[];
  feedMap?: Record<string, string>[];
  feedEnums?: Record<string, string>[];
  statusEnums?: Record<string, string>[];
  loadGroupEnums?: Record<string, string>[];
  files: { fileName: string; sha256: string; rows: number }[];
  fileBytes: number;
  gitCommit: string | null;
  scope?: InstitutionScope;
};

export function selectInstitutionScope(input: InstInputs, scope: InstitutionScope): InstInputs {
  const keep = (row: { load_group?: string }) => rowScope(row) === scope;
  return {
    ...input,
    scope,
    entities: input.entities.filter(keep),
    relations: input.relations.filter(keep),
    images: input.images.filter(keep),
    geoids: (input.geoids ?? []).filter(keep),
    bodies: input.bodies.filter((row) => ((row.load_group ?? "").trim() === "" ? scope === "domestic" : keep(row))),
    files: input.files.map((file) =>
      scope === "domestic"
        ? file
        : {
            ...file,
            fileName: `${file.fileName}#foreign`,
            sha256: sha256Hex(`${file.sha256}:foreign`),
          },
    ),
  };
}

function blank(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return text || null;
}

function day(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : null;
}

/** Institution history starts 2016-01-01. Earlier dates, and anything that is not a day, become null. */
export const HISTORY_CUT = "2016-01-01";

export function historyDate(raw: string | undefined): string | null {
  const text = day(raw);
  if (!text || text < HISTORY_CUT) return null;
  return text;
}

function textList(raw: string | undefined): string[] | null {
  const items = (raw ?? "").split(";").map((part) => part.trim()).filter(Boolean);
  return items.length ? items : null;
}

export type InstitutionScope = "domestic" | "foreign";

const FOREIGN_ID = /^(?:county|municipality|local_authority|regional_authority|intermunicipal|submunicipal|parish):([a-z]{2})-/;

/** Country code baked into a FR/DE/GB government id. US ids and other kinds stay null. */
export function institutionCountry(entityId: string): string | null {
  const cc = FOREIGN_ID.exec(entityId)?.[1];
  if (!cc || cc === "us") return null;
  return cc;
}

/** load_group 2 is the GB/DE/FR layer. A blank group is the older domestic file. */
export function rowScope(row: { load_group?: string }): InstitutionScope {
  return (row.load_group ?? "").trim() === "2" ? "foreign" : "domestic";
}

const SOURCE_SET = /^[0-9a-f]{8}$/;

/** The 8-hex hash from source_sets.csv. Anything else, including a source id, is null. */
export function sourceSetHash(raw: string | undefined): string | null {
  const text = (raw ?? "").trim();
  return SOURCE_SET.test(text) ? text : null;
}

/** Smallint code from enum_feed.csv, enum_feed_map_status.csv, or enum_load_group.csv. A name is null. */
export function feedCode(raw: string | undefined): number | null {
  const text = (raw ?? "").trim();
  if (!/^[0-9]{1,4}$/.test(text)) return null;
  const n = Number(text);
  if (!Number.isInteger(n) || n < 1 || n > 32767) return null;
  return n;
}

const OVERLAPS = new Set(["equal", "split", "contained"]);

export type MappedGeoid = {
  entity_id: string;
  unit_layer: string;
  geoid: string;
  vintage: number;
  relation: string;
  boundary_set: string;
  overlap: string | null;
  share_of_geoid_in_entity: number | null;
  share_of_entity_in_geoid: number | null;
  source_record_id: string | null;
  source_set: string | null;
};

function shareOrSkip(raw: string | undefined): number | null | undefined {
  const text = (raw ?? "").trim();
  if (!text) return null;
  const n = Number(text);
  if (!Number.isFinite(n) || n < 0 || n > 1) return undefined;
  return n;
}

/** A row that would fail entity_geoid's checks is skipped. A missing entity is skipped at insert. */
export function mapGeoidRow(row: Record<string, string>): MappedGeoid | null {
  const entityId = (row.entity_id ?? "").trim();
  const unitLayer = (row.unit_layer ?? "").trim();
  const geoid = (row.geoid ?? "").trim();
  const relation = (row.relation ?? "").trim();
  const boundarySet = (row.boundary_set ?? "").trim();
  const vintage = Number((row.vintage ?? "").trim());
  if (!entityId || !unitLayer || !geoid || !relation || !boundarySet) return null;
  if (!Number.isInteger(vintage) || vintage < 0 || vintage > 32767) return null;
  const overlap = (row.overlap ?? "").trim();
  if (overlap && !OVERLAPS.has(overlap)) return null;
  const shareGeoid = shareOrSkip(row.share_of_geoid_in_entity);
  const shareEntity = shareOrSkip(row.share_of_entity_in_geoid);
  if (shareGeoid === undefined || shareEntity === undefined) return null;
  return {
    entity_id: entityId,
    unit_layer: unitLayer,
    geoid,
    vintage,
    relation,
    boundary_set: boundarySet,
    overlap: overlap || null,
    share_of_geoid_in_entity: shareGeoid,
    share_of_entity_in_geoid: shareEntity,
    source_record_id: blank(row.source_record_id),
    source_set: sourceSetHash(row.source_set),
  };
}

function sourceTitles(rows: Record<string, string>[]): Map<string, string> {
  const titles = new Map<string, string>();
  for (const row of rows) {
    const id = (row.source_id ?? "").trim();
    if (!id) continue;
    titles.set(id, (row.source ?? row.title ?? "").trim() || "inst-entities");
  }
  return titles;
}

function enumLegend(rows: Record<string, string>[], codeKey: string): FeedEnum[] {
  const out: FeedEnum[] = [];
  for (const row of rows) {
    const code = (row[codeKey] ?? "").trim();
    const name = (row.name ?? "").trim();
    if (code && name) out.push({ code, name });
  }
  return out;
}

export function mapFeedRows(rows: Record<string, string>[]): FeedMapPackRow[] {
  const out: FeedMapPackRow[] = [];
  for (const row of rows) {
    const feed = (row.feed ?? "").trim();
    const feedId = (row.feed_id ?? row.feed_entity_id ?? "").trim();
    if (!feed || !feedId) continue;
    out.push({
      feed,
      feed_id: feedId,
      role: (row.role ?? "").trim(),
      primary: yes(row.is_primary ?? row.primary),
      entity_id: orNull(row.entity_id),
      status: (row.status ?? "").trim(),
      note: orNull(row.note),
    });
  }
  return out;
}

type ExtraDraft = {
  entity_id: string;
  valid_from_source: string | null;
  inception_source: string | null;
};

/** entity_geoid rows. Same order of magnitude as an alias row. Not a size-plan constant. */
const GEOID_BYTES_PER_ROW = 96;

/**
 * Postgres bytes for the shrunk institution load: tuple header, alignment,
 * page overhead, indexes, and one toast allowance. Calibrated on f0f1f6d,
 * where the string-length model said about 31.5 MB and the database grew by
 * 77,037,568 bytes. v2 text and image attribution are pack bytes, priced at 0.
 */
export function projectInstitutionBytes(
  input: InstInputs,
  databaseBytes: number,
  alreadyLoaded: boolean,
): InstitutionEstimate & { imagesSkipped: number } {
  let entities = 0;
  let aliasRows = 0;
  for (const row of input.entities) {
    const entityId = (row.entity_id ?? "").trim();
    const kind = (row.kind ?? "").trim();
    const name = (row.name ?? "").trim();
    if (!entityId || !name || !ENTITY_KINDS.has(kind)) continue;
    entities++;
    aliasRows += textList(row.alias)?.length ?? 0;
  }
  const relations = mapInstRelations(
    input.relations.map((row) => ({
      entity_id: row.entity_id ?? "",
      relation: row.relation ?? "",
      related_entity_id: row.related_entity_id ?? "",
      method: row.method,
      source_id: row.source_id,
    })),
  );
  let images = 0;
  let imagesSkipped = 0;
  for (const row of input.images) {
    if (!mapInstImage(row)) {
      imagesSkipped++;
      continue;
    }
    images++;
  }
  let bodies = 0;
  for (const row of input.bodies) {
    const role = (row.role ?? "").trim();
    const entityId = (row.entity_id ?? "").trim();
    const bodyKey = (row.body_key ?? "").trim();
    if (!bodyKey || !entityId || !BODY_ROLES.has(role)) continue;
    bodies++;
  }
  let geoids = 0;
  for (const row of input.geoids ?? []) {
    if (mapGeoidRow(row)) geoids++;
  }
  const counts = {
    entities,
    relations: relations.relations.length,
    images,
    aliases: aliasRows,
    bodies,
  };
  const entityRate = input.scope === "foreign" ? FOREIGN_GOVERNMENT_BYTES_PER_ROW : SLIM_ENTITY_BYTES_PER_ROW;
  const slim =
    slimInstitutionBytes({ ...counts, entities: 0 }) + entities * entityRate + geoids * GEOID_BYTES_PER_ROW;
  const part = (table: string, rows: number, bytesPerRow: number) => ({
    table,
    rows,
    bytesPerRow,
    bytes: alreadyLoaded ? 0 : rows * bytesPerRow,
  });
  const parts = [
    part("entity", entities, entityRate),
    part("entity_relation", counts.relations, SLIM_RELATION_BYTES_PER_ROW),
    part("entity_image", images, SLIM_IMAGE_BYTES_PER_ROW),
    part("entity_alias", aliasRows, SLIM_ALIAS_BYTES_PER_ROW),
    part("body_entity", bodies, SLIM_BODY_BYTES_PER_ROW),
    part("entity_geoid", geoids, GEOID_BYTES_PER_ROW),
    part("toast", alreadyLoaded ? 0 : 1, MEASURED_TOAST_BYTES),
    { table: "entity_extra", rows: 0, bytesPerRow: 0, bytes: 0 },
    { table: "entity_image_text", rows: 0, bytesPerRow: 0, bytes: 0 },
    { table: "entity_image_source", rows: 0, bytesPerRow: 0, bytes: 0 },
  ];
  const added = alreadyLoaded ? 0 : slim;
  const note = [
    `Source files are ${input.fileBytes} bytes on disk. That number is the CSV size, not a Postgres estimate.`,
    `The cc8f628 load grew the database by ${MEASURED_INSTITUTION_DELTA_BYTES} bytes. Entity heap was ${MEASURED_ENTITY_HEAP_BYTES} bytes, indexes ${MEASURED_ENTITY_INDEX_BYTES} bytes, and ${MEASURED_ENTITY_DEAD_TUPLES} dead tuples. Toast was ${MEASURED_TOAST_BYTES} bytes.`,
    `This projection is the shrunk shape: ${SLIM_ENTITY_BYTES_PER_ROW} bytes per entity including indexes and page overhead, relation ids stored as entity.nid, and v2 text plus image attribution in the pack (0 database bytes).`,
    "State text is omitted when state_fips is set. Image binaries are not loaded. A second run does not insert another copy.",
    alreadyLoaded
      ? "These files are already applied, so the projection adds nothing. The reload still writes the pack and deletes the side-table rows; npm run db:vacuum returns that space. A flat or smaller projection is allowed when the live database is already over the gate."
      : "Upper bound if these rows are not loaded yet.",
  ].join(" ");
  return {
    entities,
    relations: counts.relations,
    images,
    bodies,
    fileBytes: input.fileBytes,
    databaseBytes,
    projectedBytes: databaseBytes + added,
    parts,
    note,
    imagesSkipped,
  };
}

function showManifest(root: string): string {
  fetchOrigin(root, ["data/inst-entities"]);
  return execFileSync("git", ["show", `origin/data/inst-entities:${INST_MANIFEST}`], {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 2 * 1024 * 1024,
  });
}

export function ensureInstCache(root: string): { dir: string; commit: string } {
  const dest = join(root, "v3/.cache/inst-entities");
  const text = showManifest(root);
  const head = originCommit(root, "data/inst-entities");
  const { db, pack } = classifyManifest(parseCsv(text).rows);
  const markers = [INST_MANIFEST, ...db, ...pack];
  if (!needsRefresh(dest, head, markers)) return { dir: dest, commit: head };
  mkdirSync(dest, { recursive: true });
  const tar = execFileSync("git", ["archive", "origin/data/inst-entities", ...markers], {
    cwd: root,
    encoding: "buffer",
    maxBuffer: 120 * 1024 * 1024,
  });
  execFileSync("tar", ["-x", "-C", dest], { input: tar });
  stampCommit(dest, head);
  return { dir: dest, commit: head };
}

let readCache: { key: string; input: InstInputs } | null = null;

function namedTable(loaded: Map<string, { rows: Record<string, string>[] }>, name: string): Record<string, string>[] {
  for (const [rel, file] of loaded) {
    if (rel === name || rel.endsWith(`/${name}`)) return file.rows;
  }
  return [];
}

function readInst(root: string): InstInputs {
  const { dir, commit } = ensureInstCache(root);
  const key = `${dir}\0${commit}`;
  if (readCache?.key === key) return readCache.input;
  const manifest = parseCsv(readFileText(join(dir, INST_MANIFEST)).text);
  const { db, pack } = classifyManifest(manifest.rows);
  const paths = [INST_MANIFEST, ...db, ...pack];
  const loaded = new Map(
    paths.map((rel) => {
      const file = readFileText(join(dir, rel));
      return [rel, { rel, buffer: file.bytes, rows: parseCsv(file.text).rows }] as const;
    }),
  );
  const table = (name: string) => namedTable(loaded, name);
  const input: InstInputs = {
    entities: table("entities.csv"),
    relations: table("entity_relations.csv"),
    images: table("entity_images.csv"),
    bodies: table("body_entity.csv"),
    geoids: table("entity_geoid_xwalk.csv"),
    sourceSets: table("source_sets.csv"),
    sources: table("sources.csv"),
    sourceUrls: table("source_urls.csv"),
    feedMap: table("entity_feed_map.csv"),
    feedEnums: table("enum_feed.csv"),
    statusEnums: table("enum_feed_map_status.csv"),
    loadGroupEnums: table("enum_load_group.csv"),
    files: db.map((rel) => {
      const file = loaded.get(rel)!;
      return { fileName: rel, sha256: sha256Hex(file.buffer), rows: file.rows.length };
    }),
    fileBytes: [...loaded.values()].reduce((sum, file) => sum + file.buffer.byteLength, 0),
    gitCommit: commit || null,
    scope: "domestic",
  };
  readCache = { key, input };
  return input;
}

export async function loadInstitutionTables(
  db: pg.Pool,
  input: InstInputs,
  opts: { packsDir: string },
): Promise<Omit<InstitutionLoadReport, "estimate" | "gap"> & { imagesSkipped: number }> {
  const scope = input.scope ?? "domestic";
  const titles = sourceTitles(input.sources ?? []);
  const entityIds = new Set(input.entities.map((row) => row.entity_id.trim()).filter(Boolean));
  const entities: Record<string, unknown>[] = [];
  const extras = new Map<string, ExtraDraft>();
  const aliases: { alias: string; entity_id: string }[] = [];
  const parents: { entity_id: string; parent_id: string }[] = [];
  const succession: { predecessor_id: string; successor_id: string }[] = [];
  const sourceIds: string[] = [];
  for (const row of input.sources ?? []) sourceIds.push((row.source_id ?? "").trim());
  for (const row of input.sourceSets ?? []) sourceIds.push((row.source_id ?? "").trim());
  for (const row of input.sourceUrls ?? []) sourceIds.push((row.source_id ?? "").trim());
  for (const row of input.entities) {
    const entityId = (row.entity_id ?? "").trim();
    const kind = (row.kind ?? "").trim();
    const name = (row.name ?? "").trim();
    if (!entityId || !name || !ENTITY_KINDS.has(kind)) continue;
    const stateFips = /^\d{2}$/.test((row.state_fips ?? "").trim()) ? row.state_fips.trim() : null;
    const code = blank(row.code);
    const codeScheme = blank(row.code_scheme);
    entities.push({
      entity_id: entityId,
      kind,
      state_fips: stateFips,
      state: stateFips ? null : blank(row.state),
      country: institutionCountry(entityId),
      name,
      label: blank(row.label),
      gov_status: blank(row.gov_status),
      valid_from: historyDate(row.valid_from),
      valid_to: day(row.valid_to),
      feed: feedCode(row.feed),
      source_set: sourceSetHash(row.source_set),
      level: blank(row.level),
      type: blank(row.type),
      cog_pid6: blank(row.cog_pid6),
      flags: textList(row.flags),
      source_record_id: blank(row.source_record_id),
      wikidata: wikidataId(row.wikidata),
      iso_3166_2: blank(row.iso_3166_2),
      constituent_qid: /^Q[0-9]+$/.test((row.constituent_qid ?? "").trim()) ? row.constituent_qid.trim() : null,
      inception: historyDate(row.inception),
      inception_precision: PRECISIONS.has((row.inception_precision ?? "").trim()) ? row.inception_precision.trim() : null,
      code_scheme: code && codeScheme ? codeScheme : null,
      code: code && codeScheme ? code : null,
    });
    const validFromSource = blank(row.valid_from_source);
    const inceptionSource = blank(row.inception_source);
    if (validFromSource || inceptionSource) {
      extras.set(entityId, {
        entity_id: entityId,
        valid_from_source: validFromSource,
        inception_source: inceptionSource,
      });
    }
    for (const alias of textList(row.alias) ?? []) {
      aliases.push({ alias, entity_id: entityId });
    }
    const parentId = (row.parent_id ?? "").trim();
    if (parentId && parentId !== entityId) parents.push({ entity_id: entityId, parent_id: parentId });
    for (const predecessor of textList(row.predecessor_id) ?? []) {
      if (predecessor !== entityId && entityIds.has(predecessor)) {
        succession.push({ predecessor_id: predecessor, successor_id: entityId });
      }
    }
    for (const successor of textList(row.successor_id) ?? []) {
      if (successor !== entityId && entityIds.has(successor)) {
        succession.push({ predecessor_id: entityId, successor_id: successor });
      }
    }
  }
  const mappedRelations = mapInstRelations(
    input.relations.map((row) => ({
      entity_id: row.entity_id ?? "",
      relation: row.relation ?? "",
      related_entity_id: row.related_entity_id ?? "",
      method: row.method,
      source_id: row.source_id,
      source_set: row.source_set,
    })),
  );
  sourceIds.push(...mappedRelations.relations.map((row) => row.source_id ?? ""));
  const images: MappedImage[] = [];
  let imagesSkipped = 0;
  for (const row of input.images) {
    const mapped = mapInstImage(row);
    if (!mapped) {
      imagesSkipped++;
      continue;
    }
    images.push(mapped);
  }
  const readyImages = dedupeIcons(images);
  sourceIds.push(...readyImages.flatMap((row) => row.source_ids));
  const geoids = (input.geoids ?? []).flatMap((row) => {
    const mapped = mapGeoidRow(row);
    return mapped ? [mapped] : [];
  });
  const bodies = input.bodies.flatMap((row) => {
    const role = (row.role ?? "").trim();
    const entityId = (row.entity_id ?? "").trim();
    const bodyKey = (row.body_key ?? "").trim();
    if (!bodyKey || !entityId || !BODY_ROLES.has(role)) return [];
    return [{
      body_key: bodyKey,
      entity_id: entityId,
      role,
      source_record_id: blank(row.source_record_id),
      source_set: sourceSetHash(row.source_set),
    }];
  });
  const parentOf = new Map(parents.map((row) => [row.entity_id, row.parent_id]));
  for (const row of mappedRelations.parents) parentOf.set(row.entity_id, row.parent_id);
  for (const entity of entities) entity.parent_id = parentOf.get(String(entity.entity_id)) ?? null;
  const pack: InstPack = { v: 3, extra: {}, images: {} };
  for (const extra of extras.values()) {
    pack.extra[extra.entity_id] = {
      v2_layer: null,
      v2_key: null,
      v2_row: null,
      valid_from_source: extra.valid_from_source,
      inception_source: extra.inception_source,
      sources: null,
    };
  }
  for (const image of readyImages) {
    pack.images[imagePackKey(image.entity_id, image.feed_entity_id, image.role)] = {
      entity_id: image.entity_id,
      feed_entity_id: image.feed_entity_id,
      role: image.role,
      attribution: image.attribution,
      source_url: image.source_url,
      usage_basis: image.usage_basis,
      note: image.note,
      sources: image.source_ids,
    };
  }
  const merged = mergeInstPack(readInstPack(opts.packsDir), pack);
  for (const [id, extra] of Object.entries(merged.extra)) {
    extra.v2_layer = null;
    extra.v2_key = null;
    extra.v2_row = null;
    extra.sources = null;
    if (!extra.valid_from_source && !extra.inception_source) delete merged.extra[id];
  }
  writeInstPack(opts.packsDir, merged);
  const feedRows = mapFeedRows(input.feedMap ?? []);
  if (feedRows.length > 0) {
    writeFeedMapPack(opts.packsDir, {
      v: 3,
      feeds: enumLegend(input.feedEnums ?? [], "feed"),
      statuses: enumLegend(input.statusEnums ?? [], "status"),
      rows: feedRows,
    });
  }

  const client = await db.connect();
  try {
    await client.query("begin");
    await client.query("set local statement_timeout = '10min'");
    await writeEnum(client, "enum_feed", "feed", input.feedEnums ?? []);
    await writeEnum(client, "enum_feed_map_status", "status", input.statusEnums ?? []);
    await writeEnum(client, "enum_load_group", "load_group", input.loadGroupEnums ?? []);
    await ensureSources(client, sourceIds, titles);
    await writeSourceUrls(client, input.sourceUrls ?? []);
    await writeSourceSets(client, input.sourceSets ?? []);
    const batchIds = new Set(entities.map((row) => String(row.entity_id)));
    const missingParents = [...new Set(
      entities
        .map((row) => (row.parent_id == null ? "" : String(row.parent_id)))
        .filter((id) => id && !batchIds.has(id)),
    )];
    if (missingParents.length > 0) {
      const found = await client.query<{ entity_id: string }>(
        `select entity_id from entity where entity_id = any($1::text[])`,
        [missingParents],
      );
      const present = new Set(found.rows.map((row) => row.entity_id));
      for (const entity of entities) {
        const parent = entity.parent_id == null ? "" : String(entity.parent_id);
        if (parent && !batchIds.has(parent) && !present.has(parent)) entity.parent_id = null;
      }
    }
    const entityWrites = await insertJsonChunks(
      client,
      `insert into entity (
         entity_id, kind, state_fips, state, country, name, label, gov_status, parent_id, valid_from, valid_to,
         feed, source_set, level, type, cog_pid6, flags, origin,
         source_record_id, wikidata, iso_3166_2, constituent_qid,
         inception, inception_precision, code_scheme, code
       )
       select entity_id, kind, state_fips, state, country, name, label, gov_status, parent_id, valid_from, valid_to,
              feed, source_set, level, type, cog_pid6, flags, 'inst',
              source_record_id, wikidata, iso_3166_2, constituent_qid,
              inception, inception_precision, code_scheme, code
       from jsonb_to_recordset($1::jsonb) as x(
         entity_id text, kind text, state_fips text, state text, country text, name text, label text, gov_status text,
         parent_id text, valid_from date, valid_to date,
         feed smallint, source_set text, level text, type text, cog_pid6 text, flags text[], source_record_id text,
         wikidata text, iso_3166_2 text, constituent_qid text, inception date,
         inception_precision text, code_scheme text, code text
       )
       on conflict (entity_id) do update
         set kind = excluded.kind, state_fips = excluded.state_fips, state = excluded.state,
             country = excluded.country,
             name = excluded.name, label = excluded.label, gov_status = excluded.gov_status,
             parent_id = excluded.parent_id,
             valid_from = excluded.valid_from, valid_to = excluded.valid_to,
             v2_layer = null, v2_key = null, v2_row = null, inception_source = null,
             valid_from_source = null,
             feed = excluded.feed, source_set = excluded.source_set,
             level = excluded.level, type = excluded.type, cog_pid6 = excluded.cog_pid6,
             flags = excluded.flags, source_record_id = excluded.source_record_id,
             wikidata = excluded.wikidata, iso_3166_2 = excluded.iso_3166_2,
             constituent_qid = excluded.constituent_qid, inception = excluded.inception,
             inception_precision = excluded.inception_precision,
             code_scheme = excluded.code_scheme, code = excluded.code
         where entity.origin = 'inst'
           and (entity.kind is distinct from excluded.kind
             or entity.state_fips is distinct from excluded.state_fips
             or entity.state is distinct from excluded.state
             or entity.country is distinct from excluded.country
             or entity.name is distinct from excluded.name
             or entity.label is distinct from excluded.label
             or entity.gov_status is distinct from excluded.gov_status
             or entity.parent_id is distinct from excluded.parent_id
             or entity.valid_from is distinct from excluded.valid_from
             or entity.valid_to is distinct from excluded.valid_to
             or entity.feed is distinct from excluded.feed
             or entity.source_set is distinct from excluded.source_set
             or entity.code_scheme is distinct from excluded.code_scheme
             or entity.code is distinct from excluded.code
             or entity.level is distinct from excluded.level
             or entity.type is distinct from excluded.type
             or entity.cog_pid6 is distinct from excluded.cog_pid6
             or entity.flags is distinct from excluded.flags
             or entity.source_record_id is distinct from excluded.source_record_id
             or entity.wikidata is distinct from excluded.wikidata
             or entity.iso_3166_2 is distinct from excluded.iso_3166_2
             or entity.constituent_qid is distinct from excluded.constituent_qid
             or entity.inception is distinct from excluded.inception
             or entity.inception_precision is distinct from excluded.inception_precision
             or 'feed_absent' = any(coalesce(entity.flags, '{}')))`,
      entities,
    );
    if (entities.length > 0) {
      await client.query(
        `update entity
         set flags = array_append(coalesce(flags, '{}'), 'feed_absent')
         where origin = 'inst'
           and feed is not null
           and not (entity_id = any($1::text[]))
           and not ('feed_absent' = any(coalesce(flags, '{}')))
           and (
             ($2::text = 'domestic' and (country is null or btrim(country) = 'us'))
             or ($2::text = 'foreign' and btrim(country) in ('fr', 'de', 'gb'))
           )`,
        [entities.map((row) => String(row.entity_id)), scope],
      );
    }
    if (aliases.length > 0) {
      await insertJsonChunks(
        client,
        `insert into entity_alias (alias, entity_id, kind)
         select alias, entity_id, 'alt'
         from jsonb_to_recordset($1::jsonb) as x(alias text, entity_id text)
         on conflict (alias, entity_id) where entity_id is not null do nothing`,
        aliases,
      );
    }
    if (succession.length > 0) {
      await insertJsonChunks(
        client,
        `insert into entity_succession (predecessor_id, successor_id)
         select predecessor_id, successor_id
         from jsonb_to_recordset($1::jsonb) as x(predecessor_id text, successor_id text)
         on conflict (predecessor_id, successor_id) do nothing`,
        succession,
      );
    }
    const relationWrites = mappedRelations.relations.length
      ? await insertJsonChunks(client, RELATION_INSERT, mappedRelations.relations)
      : 0;
    const imageWrites = await writeImageRows(client, readyImages);
    await client.query("delete from entity_image_text");
    await client.query("delete from entity_image_source");
    await client.query("delete from entity_extra");
    const geoidWrites = geoids.length
      ? await insertJsonChunks(
          client,
          `insert into entity_geoid (
             entity_id, unit_layer, geoid, vintage, relation, boundary_set, overlap,
             share_of_geoid_in_entity, share_of_entity_in_geoid, source_record_id, source_set
           )
           select x.entity_id, x.unit_layer, x.geoid, x.vintage, x.relation, x.boundary_set, x.overlap,
                  x.share_of_geoid_in_entity, x.share_of_entity_in_geoid, x.source_record_id, x.source_set
           from jsonb_to_recordset($1::jsonb) as x(
             entity_id text, unit_layer text, geoid text, vintage smallint, relation text, boundary_set text,
             overlap text, share_of_geoid_in_entity numeric, share_of_entity_in_geoid numeric,
             source_record_id text, source_set text
           )
           join entity e on e.entity_id = x.entity_id
           on conflict (entity_id, unit_layer, geoid, vintage) do update
             set relation = excluded.relation, boundary_set = excluded.boundary_set, overlap = excluded.overlap,
                 share_of_geoid_in_entity = excluded.share_of_geoid_in_entity,
                 share_of_entity_in_geoid = excluded.share_of_entity_in_geoid,
                 source_record_id = excluded.source_record_id, source_set = excluded.source_set
             where entity_geoid.relation is distinct from excluded.relation
                or entity_geoid.boundary_set is distinct from excluded.boundary_set
                or entity_geoid.overlap is distinct from excluded.overlap
                or entity_geoid.source_set is distinct from excluded.source_set
                or entity_geoid.source_record_id is distinct from excluded.source_record_id`,
          geoids,
        )
      : 0;
    const bodyWrites = bodies.length
      ? await insertJsonChunks(
          client,
          `insert into body_entity (body_key, entity_id, role, source_record_id, source_set)
           select x.body_key, x.entity_id, x.role, x.source_record_id, x.source_set
           from jsonb_to_recordset($1::jsonb) as x(
             body_key text, entity_id text, role text, source_record_id text, source_set text
           )
           join entity e on e.entity_id = x.entity_id
           on conflict (body_key) do update
             set entity_id = excluded.entity_id, role = excluded.role,
                 source_record_id = excluded.source_record_id, source_set = excluded.source_set
             where body_entity.entity_id is distinct from excluded.entity_id
                or body_entity.role is distinct from excluded.role
                or body_entity.source_record_id is distinct from excluded.source_record_id
                or body_entity.source_set is distinct from excluded.source_set`,
          bodies,
        )
      : 0;
    for (const file of input.files) {
      const batch = await client.query<{ id: string }>(
        `insert into load_batch (file_name, file_sha256, git_commit, row_count, status, finished_at)
         values ($1, $2, $3, $4, 'applied', now())
         on conflict (file_sha256) do update
           set status = 'applied', finished_at = now(), row_count = excluded.row_count,
               git_commit = coalesce(excluded.git_commit, load_batch.git_commit)
         returning id`,
        [file.fileName, file.sha256, input.gitCommit, file.rows],
      );
      if (batch.rows[0]) await markSuperseded(client, file.fileName, batch.rows[0].id);
    }
    if (entityWrites + relationWrites + imageWrites + bodyWrites + geoidWrites > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query("commit");
    return {
      status: "applied",
      entities: entities.length,
      relations: mappedRelations.relations.length,
      images: readyImages.length,
      imagesSkipped,
      bodies: bodies.length,
      parents: parents.length,
      gitCommit: input.gitCommit,
    };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

export async function loadInstitutions(
  db: pg.Pool,
  opts: { root: string; currentBytes: number; allow: boolean; dryRun?: boolean; scope?: InstitutionScope },
): Promise<InstitutionLoadReport> {
  const scope = opts.scope ?? "domestic";
  const input = selectInstitutionScope(readInst(opts.root), scope);
  const label = scope === "foreign" ? "institutions-foreign" : "institutions";
  const applied = await db.query(
    `select file_sha256 from load_batch
     where status = 'applied' and file_sha256 = any($1::text[])`,
    [input.files.map((file) => file.sha256)],
  );
  const alreadyLoaded = input.files.length > 0 && applied.rowCount === input.files.length;
  const projected = projectInstitutionBytes(input, opts.currentBytes, alreadyLoaded);
  const { imagesSkipped, ...estimate } = projected;
  if (alreadyLoaded && estimate.projectedBytes != null) {
    const side = await sideTableBytes(db);
    estimate.projectedBytes = Math.max(0, opts.currentBytes - side);
    if (side > 0) {
      estimate.note += ` Side tables still occupy ${side} bytes. This reload deletes those rows, so the projected net change is ${estimate.projectedBytes - opts.currentBytes} bytes.`;
    }
  }
  const over = loadGrowthRefused(opts.currentBytes, estimate.projectedBytes, false);
  const shown = estimate.projectedBytes ?? opts.currentBytes;
  const net = shown - opts.currentBytes;
  const netLabel = `${net < 0 ? "-" : "+"}${formatMb(Math.abs(net))}`;
  const gap = over
    ? `${label}: projected ${formatMb(shown)} (${netLabel} net) against a live ${formatMb(opts.currentBytes)}, over ${formatMb(BUDGET_BYTES)}. ${estimate.note} Rows were not inserted.`
    : null;
  if (opts.dryRun) {
    return {
      status: "dry-run",
      entities: estimate.entities,
      relations: estimate.relations,
      images: estimate.images,
      imagesSkipped,
      bodies: estimate.bodies,
      parents: 0,
      estimate,
      gitCommit: input.gitCommit,
      gap,
    };
  }
  if (over && !opts.allow) {
    return {
      status: "refused",
      entities: 0,
      relations: 0,
      images: 0,
      imagesSkipped: 0,
      bodies: 0,
      parents: 0,
      estimate,
      gitCommit: input.gitCommit,
      gap,
    };
  }
  const loaded = await loadInstitutionTables(db, input, { packsDir: instPacksRoot(opts.root) });
  return { ...loaded, estimate, gap: null };
}
