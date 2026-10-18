import type pg from "pg";
import { BUDGET_BYTES } from "./budget.ts";

/**
 * Neon `pg_database_size` around the cc8f628 institution load.
 * The user's 77.0 MB is decimal (bytes / 1e6): 351,633,408 − 274,595,840.
 * A local load of the same f0f1f6d files grew an empty database by 77,268,472.
 */
export const NEON_BEFORE_INSTITUTIONS_BYTES = 274_595_840;
export const NEON_AFTER_INSTITUTIONS_BYTES = 351_633_408;
export const MEASURED_INSTITUTION_DELTA_BYTES =
  NEON_AFTER_INSTITUTIONS_BYTES - NEON_BEFORE_INSTITUTIONS_BYTES;
export const LOCAL_INSTITUTION_DELTA_BYTES = 77_268_472;

/** Decimal megabytes, matching the box report. The load gate stays 350 MiB. */
export const DECIMAL_BUDGET_BYTES = 350_000_000;

/**
 * `pg_total_relation_size` after that local load, before VACUUM.
 * Toast was 8,192 bytes on every one of these tables. The growth is heap,
 * indexes, and dead tuples, not toasted text.
 */
export const MEASURED_RELATION_BYTES = {
  entity: 49_987_584,
  entity_extra: 18_030_592,
  entity_image_source: 3_063_808,
  entity_image: 2_932_736,
  entity_image_text: 1_949_696,
  entity_relation: 1_318_912,
  entity_alias: 147_456,
  body_entity: 90_112,
} as const;

export const MEASURED_ENTITY_INDEX_BYTES = 24_485_888;
export const MEASURED_ENTITY_HEAP_BYTES = 25_468_928;
export const MEASURED_ENTITY_DEAD_TUPLES = 58_023;
export const MEASURED_TOAST_BYTES = 8_192;

/** VACUUM FULL on `entity` after that load: database 96,771,095 → 69,008,407. */
export const VACUUM_ENTITY_BYTES = 27_762_688;

/** Side tables whose payload moves to the institution pack. */
export const SIDE_PACK_BYTES =
  MEASURED_RELATION_BYTES.entity_extra +
  MEASURED_RELATION_BYTES.entity_image_text +
  MEASURED_RELATION_BYTES.entity_image_source;

/**
 * After VACUUM FULL, dropping `entity_v2` and indexing wikidata / iso_3166_2
 * only where the column is set. Measured from the rebuilt index sizes.
 */
export const PARTIAL_INDEX_BYTES = 1_038_112;

/**
 * `entity.nid` replaces repeated text ids on `entity_location` and `entity_relation`.
 * Net of the new unique index on `entity`. The 212,439 company locations are the bulk.
 */
export const SURROGATE_NET_BYTES = 3_000_000;

/**
 * Post-shrink bytes per stored row, including the tuple header, alignment,
 * page overhead, and the row's index share. Calibrated so 58,219 institution
 * entities land near the post-VACUUM FULL entity total (about 383 B) minus the
 * partial-index savings (about 365 B).
 */
export const SLIM_ENTITY_BYTES_PER_ROW = 365;
export const SLIM_RELATION_BYTES_PER_ROW = 180;
export const SLIM_IMAGE_BYTES_PER_ROW = 250;
export const SLIM_ALIAS_BYTES_PER_ROW = 96;
export const SLIM_BODY_BYTES_PER_ROW = 240;

/** Full-US dry run at cc8f628: 10,740 county and US House rollup rows. */
export const PRECINCT_ROLLUP_ROWS = 10_740;
export const PRECINCT_ROLLUP_BYTES_PER_ROW = 160;

export const FOREIGN_GOVERNMENT_ROWS = 62_939;
export const FOREIGN_GOVERNMENT_KINDS = [
  "county",
  "municipality",
  "local_authority",
  "regional_authority",
  "intermunicipal",
  "submunicipal",
  "parish",
] as const;

/**
 * Slim entity row, plus a longer frozen id (`municipality:de-091620000000` is
 * 28 characters against an 18-character US average), `code_scheme`, `code`,
 * and the `entity_code` index share.
 */
export const FOREIGN_GOVERNMENT_BYTES_PER_ROW = 463;

export type SlimCounts = {
  entities: number;
  relations: number;
  images: number;
  aliases: number;
  bodies: number;
};

export function measuredRelationBytes(): number {
  return Object.values(MEASURED_RELATION_BYTES).reduce((sum, bytes) => sum + bytes, 0);
}

/** What the shrunk institution load writes. Toast is one 8 KiB allowance, not a per-row charge. */
export function slimInstitutionBytes(counts: SlimCounts): number {
  return (
    counts.entities * SLIM_ENTITY_BYTES_PER_ROW +
    counts.relations * SLIM_RELATION_BYTES_PER_ROW +
    counts.images * SLIM_IMAGE_BYTES_PER_ROW +
    counts.aliases * SLIM_ALIAS_BYTES_PER_ROW +
    counts.bodies * SLIM_BODY_BYTES_PER_ROW +
    MEASURED_TOAST_BYTES
  );
}

export type SizePlan = {
  neonBeforeInstitutionsBytes: number;
  neonAfterInstitutionsBytes: number;
  measuredInstitutionDeltaBytes: number;
  localInstitutionDeltaBytes: number;
  measuredRelationBytes: number;
  vacuumEntityBytes: number;
  sidePackBytes: number;
  partialIndexBytes: number;
  surrogateNetBytes: number;
  shrinkBytes: number;
  afterShrinkBytes: number;
  precinctRollupRows: number;
  precinctRollupBytes: number;
  foreignGovernmentRows: number;
  foreignGovernmentKinds: readonly string[];
  foreignGovernmentBytesPerRow: number;
  foreignGovernmentBytes: number;
  finalBytes: number;
  decimalBudgetBytes: number;
  gateBytes: number;
  underDecimalBudget: boolean;
  underGate: boolean;
  note: string;
};

export function sizePlan(): SizePlan {
  const shrinkBytes = VACUUM_ENTITY_BYTES + SIDE_PACK_BYTES + PARTIAL_INDEX_BYTES + SURROGATE_NET_BYTES;
  const afterShrinkBytes = NEON_AFTER_INSTITUTIONS_BYTES - shrinkBytes;
  const precinctRollupBytes = PRECINCT_ROLLUP_ROWS * PRECINCT_ROLLUP_BYTES_PER_ROW;
  const foreignGovernmentBytes = FOREIGN_GOVERNMENT_ROWS * FOREIGN_GOVERNMENT_BYTES_PER_ROW;
  const finalBytes = afterShrinkBytes + precinctRollupBytes + foreignGovernmentBytes;
  return {
    neonBeforeInstitutionsBytes: NEON_BEFORE_INSTITUTIONS_BYTES,
    neonAfterInstitutionsBytes: NEON_AFTER_INSTITUTIONS_BYTES,
    measuredInstitutionDeltaBytes: MEASURED_INSTITUTION_DELTA_BYTES,
    localInstitutionDeltaBytes: LOCAL_INSTITUTION_DELTA_BYTES,
    measuredRelationBytes: measuredRelationBytes(),
    vacuumEntityBytes: VACUUM_ENTITY_BYTES,
    sidePackBytes: SIDE_PACK_BYTES,
    partialIndexBytes: PARTIAL_INDEX_BYTES,
    surrogateNetBytes: SURROGATE_NET_BYTES,
    shrinkBytes,
    afterShrinkBytes,
    precinctRollupRows: PRECINCT_ROLLUP_ROWS,
    precinctRollupBytes,
    foreignGovernmentRows: FOREIGN_GOVERNMENT_ROWS,
    foreignGovernmentKinds: FOREIGN_GOVERNMENT_KINDS,
    foreignGovernmentBytesPerRow: FOREIGN_GOVERNMENT_BYTES_PER_ROW,
    foreignGovernmentBytes,
    finalBytes,
    decimalBudgetBytes: DECIMAL_BUDGET_BYTES,
    gateBytes: BUDGET_BYTES,
    underDecimalBudget: finalBytes < DECIMAL_BUDGET_BYTES,
    underGate: finalBytes < BUDGET_BYTES,
    note: [
      `The cc8f628 institution load grew Neon by ${MEASURED_INSTITUTION_DELTA_BYTES} bytes (${NEON_BEFORE_INSTITUTIONS_BYTES} to ${NEON_AFTER_INSTITUTIONS_BYTES}).`,
      `A local load of the same files grew ${LOCAL_INSTITUTION_DELTA_BYTES} bytes. Toast was ${MEASURED_TOAST_BYTES} bytes.`,
      `Entity held ${MEASURED_ENTITY_HEAP_BYTES} bytes of heap, ${MEASURED_ENTITY_INDEX_BYTES} bytes of indexes, and ${MEASURED_ENTITY_DEAD_TUPLES} dead tuples from the parent_id update.`,
      `VACUUM FULL entity reclaims ${VACUUM_ENTITY_BYTES} bytes. The pack moves entity_extra, entity_image_text, and entity_image_source (${SIDE_PACK_BYTES} bytes).`,
      `Partial unique indexes drop ${PARTIAL_INDEX_BYTES} bytes. The int surrogate nets ${SURROGATE_NET_BYTES} bytes.`,
      `Precinct units and unit_crosswalk stay out of Postgres; precinct_rollup is ${precinctRollupBytes} bytes for ${PRECINCT_ROLLUP_ROWS} rows.`,
      `${FOREIGN_GOVERNMENT_ROWS} foreign governments at ${FOREIGN_GOVERNMENT_BYTES_PER_ROW} bytes is ${foreignGovernmentBytes} bytes.`,
      `Planned total ${finalBytes} bytes, under ${DECIMAL_BUDGET_BYTES} decimal bytes and under the ${BUDGET_BYTES}-byte gate.`,
      "entity_location_unit dead space from the rolled-back assignment is reclaimed by VACUUM FULL and is not counted here.",
    ].join(" "),
  };
}

export type TableSize = {
  table: string;
  heap: number;
  indexes: number;
  toast: number;
  total: number;
  live: number;
  dead: number;
};

export type DatabaseSizeReport = {
  databaseBytes: number;
  tables: TableSize[];
  plan: SizePlan;
};

/** Read-only. Heap, indexes, toast, and dead tuples for every usd table. */
export async function databaseSizeReport(db: pg.Pool): Promise<DatabaseSizeReport> {
  const sized = await db.query<{
    table: string;
    heap: string;
    indexes: string;
    toast: string;
    total: string;
    live: string;
    dead: string;
  }>(
    `select c.relname as table,
            pg_relation_size(c.oid)::text as heap,
            pg_indexes_size(c.oid)::text as indexes,
            case when c.reltoastrelid = 0 then '0'
                 else pg_total_relation_size(c.reltoastrelid)::text end as toast,
            pg_total_relation_size(c.oid)::text as total,
            coalesce(s.n_live_tup, 0)::text as live,
            coalesce(s.n_dead_tup, 0)::text as dead
     from pg_class c
     join pg_namespace n on n.oid = c.relnamespace
     left join pg_stat_user_tables s on s.relid = c.oid
     where n.nspname = 'usd' and c.relkind = 'r'
     order by pg_total_relation_size(c.oid) desc, c.relname`,
  );
  const database = await db.query<{ bytes: string }>(
    "select pg_database_size(current_database())::text as bytes",
  );
  return {
    databaseBytes: Number(database.rows[0]?.bytes ?? 0),
    tables: sized.rows.map((row) => ({
      table: row.table,
      heap: Number(row.heap),
      indexes: Number(row.indexes),
      toast: Number(row.toast),
      total: Number(row.total),
      live: Number(row.live),
      dead: Number(row.dead),
    })),
    plan: sizePlan(),
  };
}
