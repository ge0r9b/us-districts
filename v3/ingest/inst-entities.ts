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

const RELATION_INSERT = `insert into entity_relation (parent_nid, child_nid, relation, method, source_id, source_record_id)
 select p.nid, c.nid, x.relation, x.method, x.source_id, x.source_record_id
 from jsonb_to_recordset($1::jsonb) as x(
   parent_id text, child_id text, relation text, method text, source_id text, source_record_id text
 )
 join entity p on p.entity_id = x.parent_id
 join entity c on c.entity_id = x.child_id
 on conflict (parent_nid, child_nid, relation, valid_from) do update
   set method = excluded.method, source_record_id = excluded.source_record_id
   where entity_relation.method is distinct from excluded.method
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
    const sourceId = firstSource(row.source_id);
    const mappedMethod = mapRelationMethod(row.method);
    const record = (parentId: string, childId: string, name: MappedRelation["relation"]) => {
      const token = mappedMethod.token ? `|method:${mappedMethod.token}` : "";
      relations.push({
        parent_id: parentId,
        child_id: childId,
        relation: name,
        method: mappedMethod.method,
        source_id: sourceId,
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
       entity_id, feed_entity_id, role, file, file_url, license, fair_use, public, icon, wikidata, retrieved_at
     )
     select nullif(entity_id, ''), nullif(feed_entity_id, ''), role, file, file_url, license,
            fair_use, public, icon, wikidata, retrieved_at
     from jsonb_to_recordset($1::jsonb) as x(
       entity_id text, feed_entity_id text, role text, file text, file_url text, license text,
       fair_use boolean, public boolean, icon boolean, wikidata text, retrieved_at timestamptz
     )
     on conflict (entity_id, feed_entity_id, role) do update
       set file = excluded.file, file_url = excluded.file_url, license = excluded.license,
           fair_use = excluded.fair_use, public = excluded.public, icon = excluded.icon,
           wikidata = excluded.wikidata, attribution = null, source_url = null, usage_basis = null`,
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

/** Postgres batch identity. A changed sha re-prices the insert. Pack files are not in this list. */
export const INST_BATCH_FILES = [
  "data-v3/inst/entities.csv",
  "data-v3/inst/entity_relations.csv",
  "data-v3/inst/entity_images.csv",
  "data-v3/inst/body_entity.csv",
  "data-v3/inst/source_sets.csv",
  "data-v3/inst/sources.csv",
] as const;

const INST_PACK_FILES = [
  "data-v3/inst/pack/entity_feed_map.csv",
  "data-v3/inst/entity_v2_rows.csv",
  "data-v3/inst/enum_feed.csv",
  "data-v3/inst/enum_feed_map_status.csv",
] as const;

const INST_FILES = [...INST_BATCH_FILES, ...INST_PACK_FILES] as const;

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
  sourceSets?: Record<string, string>[];
  sources?: Record<string, string>[];
  feedMap?: Record<string, string>[];
  feedEnums?: Record<string, string>[];
  statusEnums?: Record<string, string>[];
  v2Rows?: Record<string, string>[];
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

export function indexSourceSets(rows: Record<string, string>[]): Map<string, string[]> {
  const grouped = new Map<string, { ord: number; id: string }[]>();
  for (const row of rows) {
    const key = (row.source_set ?? "").trim();
    const id = (row.source_id ?? "").trim();
    if (!key || !id) continue;
    const ord = Number(row.ord ?? "");
    const list = grouped.get(key) ?? [];
    list.push({ ord: Number.isFinite(ord) ? ord : list.length + 1, id });
    grouped.set(key, list);
  }
  const out = new Map<string, string[]>();
  for (const [key, list] of grouped) {
    list.sort((a, b) => a.ord - b.ord);
    out.set(key, [...new Set(list.map((item) => item.id))]);
  }
  return out;
}

export function sourceIdsFor(row: Record<string, string>, sets: Map<string, string[]>): string[] {
  const key = (row.source_set ?? "").trim();
  if (key && sets.has(key)) return sets.get(key) ?? [];
  return sourceList(row.source_id);
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

function v2PackKey(row: Record<string, string>): string | null {
  const state = (row.state ?? "").trim();
  const layer = (row.v2_layer ?? "").trim();
  const name = (row.v2_name ?? "").trim();
  const v2Row = (row.v2_row ?? "").trim();
  if (!state) return null;
  if (layer === "v2:parts" || layer.startsWith("v2:towns")) return v2Row ? `${state}|${v2Row}` : null;
  return name ? `${state}|${name}` : null;
}

type ExtraDraft = {
  entity_id: string;
  v2_layer: string[] | null;
  v2_key: string[] | null;
  v2_row: string[] | null;
  valid_from_source: string | null;
  inception_source: string | null;
  sources: string[] | null;
  v2FromRow: boolean;
};

function addUnique(list: string[] | null, value: string): string[] {
  const next = list ? [...list] : [];
  if (!next.includes(value)) next.push(value);
  return next;
}

function applyV2Rows(extras: Map<string, ExtraDraft>, rows: Record<string, string>[], ids: Set<string>): void {
  for (const row of rows) {
    const id = (row.entity_id ?? "").trim();
    if (!id || !ids.has(id)) continue;
    if ((row.resolved ?? "").trim() === "no") continue;
    const layer = (row.v2_layer ?? "").trim();
    const key = v2PackKey(row);
    const rowToken = layer && (row.v2_row ?? "").trim() ? `${layer}#${row.v2_row.trim()}` : "";
    if (!layer && !key && !rowToken) continue;
    const extra = extras.get(id) ?? {
      entity_id: id,
      v2_layer: null,
      v2_key: null,
      v2_row: null,
      valid_from_source: null,
      inception_source: null,
      sources: null,
      v2FromRow: false,
    };
    if (layer) extra.v2_layer = addUnique(extra.v2_layer, layer);
    if (!extra.v2FromRow) {
      if (key) extra.v2_key = addUnique(extra.v2_key, key);
      if (rowToken) extra.v2_row = addUnique(extra.v2_row, rowToken);
    }
    extras.set(id, extra);
  }
}

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
  const counts = {
    entities,
    relations: relations.relations.length,
    images,
    aliases: aliasRows,
    bodies,
  };
  const entityRate = input.scope === "foreign" ? FOREIGN_GOVERNMENT_BYTES_PER_ROW : SLIM_ENTITY_BYTES_PER_ROW;
  const slim =
    slimInstitutionBytes({ ...counts, entities: 0 }) + entities * entityRate;
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

export function ensureInstCache(root: string): { dir: string; commit: string } {
  const dest = join(root, "v3/.cache/inst-entities");
  fetchOrigin(root, ["data/inst-entities"]);
  const head = originCommit(root, "data/inst-entities");
  if (!needsRefresh(dest, head, [...INST_FILES])) return { dir: dest, commit: head };
  mkdirSync(dest, { recursive: true });
  const tar = execFileSync("git", ["archive", "origin/data/inst-entities", ...INST_FILES], {
    cwd: root,
    encoding: "buffer",
    maxBuffer: 120 * 1024 * 1024,
  });
  execFileSync("tar", ["-x", "-C", dest], { input: tar });
  stampCommit(dest, head);
  return { dir: dest, commit: head };
}

let readCache: { key: string; input: InstInputs } | null = null;

function readInst(root: string): InstInputs {
  const { dir, commit } = ensureInstCache(root);
  const key = `${dir}\0${commit}`;
  if (readCache?.key === key) return readCache.input;
  const loaded = new Map(
    INST_FILES.map((rel) => {
      const file = readFileText(join(dir, rel));
      return [rel, { rel, buffer: file.bytes, rows: parseCsv(file.text).rows }] as const;
    }),
  );
  const table = (rel: (typeof INST_FILES)[number]) => loaded.get(rel)?.rows ?? [];
  const batch = INST_BATCH_FILES.map((rel) => loaded.get(rel)!);
  const input: InstInputs = {
    entities: table("data-v3/inst/entities.csv"),
    relations: table("data-v3/inst/entity_relations.csv"),
    images: table("data-v3/inst/entity_images.csv"),
    bodies: table("data-v3/inst/body_entity.csv"),
    sourceSets: table("data-v3/inst/source_sets.csv"),
    sources: table("data-v3/inst/sources.csv"),
    feedMap: table("data-v3/inst/pack/entity_feed_map.csv"),
    feedEnums: table("data-v3/inst/enum_feed.csv"),
    statusEnums: table("data-v3/inst/enum_feed_map_status.csv"),
    v2Rows: table("data-v3/inst/entity_v2_rows.csv"),
    files: batch.map((file) => ({
      fileName: file.rel,
      sha256: sha256Hex(file.buffer),
      rows: file.rows.length,
    })),
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
  const sets = indexSourceSets(input.sourceSets ?? []);
  const titles = sourceTitles(input.sources ?? []);
  const entityIds = new Set(input.entities.map((row) => row.entity_id.trim()).filter(Boolean));
  const entities: Record<string, unknown>[] = [];
  const extras = new Map<string, ExtraDraft>();
  const aliases: { alias: string; entity_id: string }[] = [];
  const parents: { entity_id: string; parent_id: string }[] = [];
  const succession: { predecessor_id: string; successor_id: string }[] = [];
  const sourceIds: string[] = [];
  for (const row of input.entities) {
    const entityId = (row.entity_id ?? "").trim();
    const kind = (row.kind ?? "").trim();
    const name = (row.name ?? "").trim();
    if (!entityId || !name || !ENTITY_KINDS.has(kind)) continue;
    const cited = sourceIdsFor(row, sets);
    sourceIds.push(...cited);
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
      feed: blank(row.feed),
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
    const v2Layer = textList(row.v2_layer);
    const v2Key = textList(row.v2_key);
    const v2Row = textList(row.v2_row);
    const validFromSource = blank(row.valid_from_source);
    const inceptionSource = blank(row.inception_source);
    if (v2Layer || v2Key || v2Row || validFromSource || inceptionSource || cited.length) {
      extras.set(entityId, {
        entity_id: entityId,
        v2_layer: v2Layer,
        v2_key: v2Key,
        v2_row: v2Row,
        valid_from_source: validFromSource,
        inception_source: inceptionSource,
        sources: cited.length ? cited : null,
        v2FromRow: Boolean(v2Key || v2Row),
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
  applyV2Rows(extras, input.v2Rows ?? [], entityIds);
  const mappedRelations = mapInstRelations(
    input.relations.map((row) => ({
      entity_id: row.entity_id ?? "",
      relation: row.relation ?? "",
      related_entity_id: row.related_entity_id ?? "",
      method: row.method,
      source_id: sourceIdsFor(row, sets)[0] ?? "",
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
    if (mapped.source_ids.length === 0) mapped.source_ids = sourceIdsFor(row, sets);
    images.push(mapped);
  }
  const readyImages = dedupeIcons(images);
  sourceIds.push(...readyImages.flatMap((row) => row.source_ids));
  const bodies = input.bodies.flatMap((row) => {
    const role = (row.role ?? "").trim();
    const entityId = (row.entity_id ?? "").trim();
    const bodyKey = (row.body_key ?? "").trim();
    if (!bodyKey || !entityId || !BODY_ROLES.has(role)) return [];
    sourceIds.push(...sourceIdsFor(row, sets));
    return [{ body_key: bodyKey, entity_id: entityId, role, source_record_id: blank(row.source_record_id) }];
  });
  const parentOf = new Map(parents.map((row) => [row.entity_id, row.parent_id]));
  for (const row of mappedRelations.parents) parentOf.set(row.entity_id, row.parent_id);
  for (const entity of entities) entity.parent_id = parentOf.get(String(entity.entity_id)) ?? null;
  const pack: InstPack = { v: 3, extra: {}, images: {} };
  for (const extra of extras.values()) {
    pack.extra[extra.entity_id] = {
      v2_layer: extra.v2_layer,
      v2_key: extra.v2_key,
      v2_row: extra.v2_row,
      valid_from_source: extra.valid_from_source,
      inception_source: extra.inception_source,
      sources: extra.sources,
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
  writeInstPack(opts.packsDir, mergeInstPack(readInstPack(opts.packsDir), pack));
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
    await ensureSources(client, sourceIds, titles);
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
         feed, level, type, cog_pid6, flags, origin,
         source_record_id, wikidata, iso_3166_2, constituent_qid,
         inception, inception_precision, code_scheme, code
       )
       select entity_id, kind, state_fips, state, country, name, label, gov_status, parent_id, valid_from, valid_to,
              feed, level, type, cog_pid6, flags, 'inst',
              source_record_id, wikidata, iso_3166_2, constituent_qid,
              inception, inception_precision, code_scheme, code
       from jsonb_to_recordset($1::jsonb) as x(
         entity_id text, kind text, state_fips text, state text, country text, name text, label text, gov_status text,
         parent_id text, valid_from date, valid_to date,
         feed text, level text, type text, cog_pid6 text, flags text[], source_record_id text,
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
             feed = excluded.feed, level = excluded.level, type = excluded.type, cog_pid6 = excluded.cog_pid6,
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
    const bodyWrites = bodies.length
      ? await insertJsonChunks(
          client,
          `insert into body_entity (body_key, entity_id, role, source_record_id)
           select body_key, entity_id, role, source_record_id
           from jsonb_to_recordset($1::jsonb) as x(body_key text, entity_id text, role text, source_record_id text)
           on conflict (body_key) do update
             set entity_id = excluded.entity_id, role = excluded.role, source_record_id = excluded.source_record_id
             where body_entity.entity_id is distinct from excluded.entity_id
                or body_entity.role is distinct from excluded.role
                or body_entity.source_record_id is distinct from excluded.source_record_id`,
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
    if (entityWrites + relationWrites + imageWrites + bodyWrites > 0) {
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
