import type pg from "pg";
import { insertJsonChunks } from "./batch.ts";

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
  source_id?: string;
};

export type MappedRelation = {
  parent_id: string;
  child_id: string;
  relation: "parent" | "consolidated_with";
  source_id: string | null;
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
    if (relation === "parent") {
      relations.push({ parent_id: related, child_id: child, relation: "parent", source_id: sourceId });
      if (!seenParent.has(child)) {
        seenParent.add(child);
        parents.push({ entity_id: child, parent_id: related });
      }
      continue;
    }
    if (relation === "consolidated_with") {
      relations.push({ parent_id: child, child_id: related, relation: "consolidated_with", source_id: sourceId });
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
  fair_use: boolean;
  public: boolean;
  icon: boolean;
  usage_basis: string | null;
  attribution: string | null;
  source_url: string | null;
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
 * entity_images.csv at 1fde48d: `role`, `file`, `feed_id`, plus `public` and `icon`.
 * Older names (`image_kind`, `commons_file`, `feed_entity_id`) still map.
 * Fair-use rows are not public. An icon has to be public.
 */
export function mapInstImage(row: Record<string, string>): MappedImage | null {
  const role = (row.role ?? row.image_kind ?? "").trim();
  if (!ROLES.has(role)) return null;
  const entityId = orNull(row.entity_id);
  const feedId = orNull(row.feed_id ?? row.feed_entity_id);
  if (!entityId && !feedId) return null;
  const fairUse = yes(row.fair_use);
  const isPublic = row.public != null && row.public.trim() !== "" ? yes(row.public) && !fairUse : !fairUse;
  const icon = yes(row.icon) && isPublic;
  const license = (row.license ?? "").trim() || (fairUse ? "fair-use" : "unknown");
  return {
    entity_id: entityId,
    feed_entity_id: feedId,
    role: role as MappedImage["role"],
    file: orNull(row.file ?? row.commons_file),
    file_url: orNull(row.commons_url ?? row.file_url),
    license,
    fair_use: fairUse,
    public: isPublic,
    icon,
    usage_basis: orNull(row.usage_basis),
    attribution: orNull(row.attribution),
    source_url: orNull(row.source_url),
    wikidata: wikidataId(row.wikidata ?? row.wikidata_qid),
    retrieved_at: orNull(row.retrieved_at),
    source_ids: sourceList(row.source_id),
  };
}

async function ensureSources(db: pg.PoolClient, ids: string[]): Promise<void> {
  const unique = [...new Set(ids.filter(Boolean))];
  if (unique.length === 0) return;
  await insertJsonChunks(
    db,
    `insert into source (source_id, title)
     select source_id, 'inst-entities'
     from jsonb_to_recordset($1::jsonb) as x(source_id text)
     on conflict (source_id) do nothing`,
    unique.map((source_id) => ({ source_id })),
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
    const written = await insertJsonChunks(
      client,
      `insert into entity_relation (parent_id, child_id, relation, source_id, source_record_id)
       select parent_id, child_id, relation, source_id, child_id || '|' || relation || '|' || parent_id
       from jsonb_to_recordset($1::jsonb) as x(parent_id text, child_id text, relation text, source_id text)
       on conflict (parent_id, child_id, relation, valid_from) do nothing`,
      mapped.relations,
    );
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
  if (images.length === 0) return { images: 0, skipped };
  const client = await db.connect();
  try {
    await client.query("begin");
    await ensureSources(
      client,
      images.flatMap((row) => row.source_ids),
    );
    const written = await insertJsonChunks(
      client,
      `insert into entity_image (
         entity_id, feed_entity_id, role, file, file_url, license, fair_use, public, icon,
         usage_basis, attribution, source_url, wikidata, retrieved_at
       )
       select nullif(entity_id, ''), nullif(feed_entity_id, ''), role, file, file_url, license,
              fair_use, public, icon, usage_basis, attribution, source_url, wikidata, retrieved_at
       from jsonb_to_recordset($1::jsonb) as x(
         entity_id text, feed_entity_id text, role text, file text, file_url text, license text,
         fair_use boolean, public boolean, icon boolean, usage_basis text, attribution text,
         source_url text, wikidata text, retrieved_at timestamptz
       )
       on conflict (entity_id, feed_entity_id, role) do update
         set file = excluded.file, file_url = excluded.file_url, license = excluded.license,
             fair_use = excluded.fair_use, public = excluded.public, icon = excluded.icon,
             wikidata = excluded.wikidata, attribution = excluded.attribution`,
      images.map((row) => ({
        entity_id: row.entity_id ?? "",
        feed_entity_id: row.feed_entity_id ?? "",
        role: row.role,
        file: row.file,
        file_url: row.file_url,
        license: row.license,
        fair_use: row.fair_use,
        public: row.public,
        icon: row.icon,
        usage_basis: row.usage_basis,
        attribution: row.attribution,
        source_url: row.source_url,
        wikidata: row.wikidata,
        retrieved_at: row.retrieved_at,
      })),
    );
    const links = images.flatMap((row) =>
      row.source_ids.map((source_id, ord) => ({
        entity_id: row.entity_id ?? "",
        feed_entity_id: row.feed_entity_id ?? "",
        role: row.role,
        source_id,
        ord: ord + 1,
      })),
    );
    if (links.length > 0) {
      await insertJsonChunks(
        client,
        `insert into entity_image_source (image_id, source_id, ord)
         select i.id, x.source_id, x.ord
         from jsonb_to_recordset($1::jsonb) as x(
           entity_id text, feed_entity_id text, role text, source_id text, ord int
         )
         join entity_image i
           on i.role = x.role
          and i.entity_id is not distinct from nullif(x.entity_id, '')
          and i.feed_entity_id is not distinct from nullif(x.feed_entity_id, '')
         on conflict (image_id, source_id) do nothing`,
        links,
      );
    }
    await client.query("commit");
    return { images: written, skipped };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}
