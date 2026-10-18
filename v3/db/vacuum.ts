import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * VACUUM FULL rewrites a table so pg_database_size shrinks.
 * Regular VACUUM only marks dead tuples reusable.
 *
 * 014_shrink.sql drops entity_location.entity_id / sub_entity_id and
 * entity_relation.parent_id / child_id after backfilling the bigint ids.
 * The file is already applied on Neon, so this note lives here: editing that
 * migration would change its checksum. DROP COLUMN sets attisdropped and
 * leaves the old bytes in the heap. Those catalog flags stay after VACUUM FULL,
 * so a dropped column by itself is not a reason to vacuum again.
 *
 * A local 200,000-row entity_location (PostGIS, migrations 001–013, then 014):
 * heap 60,686,336 → 127,033,344 with 210,000 dead tuples (200,000 entity_nid
 * updates plus 10,000 sub_entity_nid updates). information_schema kept only
 * entity_nid and sub_entity_nid. Regular VACUUM set dead tuples to 0 and left
 * the heap at 127,033,344. VACUUM FULL returned the heap to 60,579,840 and the
 * indexes from 46,817,280 to 23,314,432. Average pg_column_size went 294 → 305 → 288.
 */

const migrationsDir = join(dirname(fileURLToPath(import.meta.url)), "migrations");

/** Side tables the institution reload empties after the pack is on disk. */
export const SIDE_TABLES = ["entity_extra", "entity_image_text", "entity_image_source"] as const;

const SIDE = new Set<string>(SIDE_TABLES);

/** Heap waste below this is not worth an exclusive lock. */
const MIN_WASTE_BYTES = 1_048_576;

/** Live heap must exceed the tuple estimate by this much. */
const BLOAT_RATIO = 1.4;

/** 24 bytes covers the aligned heap tuple header. Calibrated on the rewrite probe. */
const TUPLE_HEADER = 24;

const IDENT = /^[a-z_][a-z0-9_]*$/;

export type Sql = {
  query(text: string, params?: unknown[]): Promise<{ rows: Array<Record<string, unknown>> }>;
};

export type RelationSize = {
  table: string;
  heapBytes: number;
  indexBytes: number;
  toastBytes: number;
  totalBytes: number;
  liveTuples: number;
  deadTuples: number;
  relTuples: number;
  avgWidth: number;
  droppedColumns: number;
  /** True when a side table's count(*) is 0 while its file is still large. */
  empty: boolean;
};

export type RewriteNote = {
  filename: string;
  tables: { table: string; columns: string[] }[];
};

const DROP_COLUMN =
  /alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?([a-z_][a-z0-9_]*)\s+drop\s+column\s+(?:if\s+exists\s+)?([a-z_][a-z0-9_]*)/gi;

export function isVacuumStatement(sql: string): boolean {
  return /^\s*vacuum\b/i.test(sql);
}

export function quoteIdent(name: string): string {
  if (!IDENT.test(name)) throw new Error(`Refusing to vacuum ${name}`);
  return `"${name}"`;
}

/** Bytes the live rows should occupy. 0 when the planner has no width yet. */
export function expectedHeapBytes(relTuples: number, avgWidth: number): number {
  if (relTuples <= 0 || avgWidth <= 0) return 0;
  return relTuples * (avgWidth + TUPLE_HEADER);
}

/**
 * Significant bloat: a heap well past its live rows, a large dead-tuple count,
 * or a side table whose rows are gone and whose file is still at least 1 MB.
 * Dropped-column flags stay after VACUUM FULL, so they do not select a table.
 */
export function needsVacuumFull(row: RelationSize): boolean {
  if (row.empty && SIDE.has(row.table) && row.totalBytes >= MIN_WASTE_BYTES) return true;
  const tuples = row.relTuples > 0 ? row.relTuples : row.liveTuples;
  const expected = expectedHeapBytes(tuples, row.avgWidth);
  if (expected > 0 && row.heapBytes - expected >= MIN_WASTE_BYTES && row.heapBytes > expected * BLOAT_RATIO) {
    return true;
  }
  return (
    row.deadTuples >= 1000 &&
    row.totalBytes >= MIN_WASTE_BYTES &&
    row.deadTuples >= Math.max(1000, tuples * 0.2)
  );
}

export function rewriteNotes(files: { filename: string; sql: string }[]): RewriteNote[] {
  const notes: RewriteNote[] = [];
  for (const file of files) {
    const byTable = new Map<string, string[]>();
    for (const match of file.sql.matchAll(DROP_COLUMN)) {
      const table = match[1]!.toLowerCase();
      const column = match[2]!.toLowerCase();
      const columns = byTable.get(table) ?? [];
      if (!columns.includes(column)) columns.push(column);
      byTable.set(table, columns);
    }
    if (byTable.size === 0) continue;
    notes.push({
      filename: file.filename,
      tables: [...byTable.entries()].map(([table, columns]) => ({ table, columns })),
    });
  }
  return notes;
}

export function migrationRewriteNotes(): RewriteNote[] {
  const files = readdirSync(migrationsDir)
    .filter((name) => name.endsWith(".sql"))
    .sort()
    .map((name) => ({
      filename: name,
      sql: readFileSync(join(migrationsDir, name), "utf8"),
    }));
  return rewriteNotes(files);
}

/** Printed by db:migrate while rewritten or emptied tables still hold space. */
export function vacuumReminder(notes: RewriteNote[], targets: RelationSize[]): string | null {
  if (targets.length === 0) return null;
  const names = new Set(targets.map((row) => row.table));
  const lines = ["VACUUM FULL is required before pg_database_size shrinks."];
  for (const note of notes) {
    const relevant = note.tables.filter((table) => names.has(table.table));
    if (relevant.length === 0) continue;
    const detail = relevant
      .map((table) => `${table.table} (${table.columns.join(", ")})`)
      .join(" and ");
    lines.push(
      `${note.filename} drops columns on ${detail}. Those bytes stay in the heap until VACUUM FULL.`,
    );
  }
  if (lines.length === 1) {
    lines.push("These usd tables are still larger than their live rows.");
  }
  for (const row of targets) {
    lines.push(
      `${row.table} heap ${row.heapBytes} indexes ${row.indexBytes} total ${row.totalBytes} dead ${row.deadTuples}`,
    );
  }
  lines.push("Run: npm run db:vacuum");
  return lines.join("\n");
}

export async function databaseBytes(db: Sql): Promise<number> {
  const result = await db.query("select pg_database_size(current_database())::text as bytes");
  return Number(result.rows[0]?.bytes ?? 0);
}

export async function sideTableBytes(db: Sql): Promise<number> {
  const result = await db.query(
    `select coalesce(sum(pg_total_relation_size(c.oid)), 0)::text as bytes
     from pg_class c
     join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'usd' and c.relname = any($1::text[])`,
    [SIDE_TABLES],
  );
  return Number(result.rows[0]?.bytes ?? 0);
}

export async function measureRelations(db: Sql): Promise<RelationSize[]> {
  const result = await db.query(
    `select c.relname as table,
            pg_relation_size(c.oid)::text as heap,
            pg_indexes_size(c.oid)::text as indexes,
            case when c.reltoastrelid = 0 then '0'
                 else pg_relation_size(c.reltoastrelid)::text end as toast,
            pg_total_relation_size(c.oid)::text as total,
            coalesce(s.n_live_tup, 0)::text as live,
            coalesce(s.n_dead_tup, 0)::text as dead,
            c.reltuples::text as reltuples,
            coalesce((
              select sum(st.avg_width) from pg_stats st
              where st.schemaname = n.nspname and st.tablename = c.relname
            ), 0)::text as avg_width,
            (select count(*) from pg_attribute a
              where a.attrelid = c.oid and a.attnum > 0 and a.attisdropped)::text as dropped
     from pg_class c
     join pg_namespace n on n.oid = c.relnamespace
     left join pg_stat_user_tables s on s.relid = c.oid
     where n.nspname = 'usd' and c.relkind = 'r'
     order by pg_total_relation_size(c.oid) desc, c.relname`,
  );
  return result.rows.map((row) => ({
    table: String(row.table),
    heapBytes: Number(row.heap),
    indexBytes: Number(row.indexes),
    toastBytes: Number(row.toast),
    totalBytes: Number(row.total),
    liveTuples: Number(row.live),
    deadTuples: Number(row.dead),
    relTuples: Number(row.reltuples),
    avgWidth: Number(row.avg_width),
    droppedColumns: Number(row.dropped),
    empty: false,
  }));
}

async function withEmptiedSideTables(db: Sql, rows: RelationSize[]): Promise<RelationSize[]> {
  const out: RelationSize[] = [];
  for (const row of rows) {
    if (!SIDE.has(row.table) || row.totalBytes < MIN_WASTE_BYTES) {
      out.push(row);
      continue;
    }
    const count = await db.query(`select count(*)::text as n from usd.${quoteIdent(row.table)}`);
    out.push({ ...row, empty: Number(count.rows[0]?.n ?? 1) === 0 });
  }
  return out;
}

export async function listVacuumTargets(db: Sql): Promise<RelationSize[]> {
  const measured = await withEmptiedSideTables(db, await measureRelations(db));
  return measured
    .filter(needsVacuumFull)
    .sort((a, b) => b.totalBytes - a.totalBytes || a.table.localeCompare(b.table));
}

export function formatRelation(prefix: string, row: RelationSize): string {
  return `${row.table} ${prefix} heap ${row.heapBytes} indexes ${row.indexBytes} total ${row.totalBytes} dead ${row.deadTuples}`;
}

export async function vacuumFullTable(db: Sql, table: string): Promise<void> {
  await db.query(`vacuum (full, analyze) usd.${quoteIdent(table)}`);
}

export type VacuumRun = {
  databaseBefore: number;
  databaseAfter: number;
  lines: string[];
};

/** VACUUM FULL each bloated usd table. Prints bytes before and after. Not inside a transaction. */
export async function vacuumBloated(db: Sql): Promise<VacuumRun> {
  const targets = await listVacuumTargets(db);
  const databaseBefore = await databaseBytes(db);
  const lines = [`database ${databaseBefore}`];
  if (targets.length === 0) {
    lines.push("no usd table has significant bloat");
    return { databaseBefore, databaseAfter: databaseBefore, lines };
  }
  for (const before of targets) {
    lines.push(formatRelation("before", before));
    const statement = `vacuum (full, analyze) usd.${quoteIdent(before.table)}`;
    lines.push(statement);
    await db.query(statement);
    const after = (await measureRelations(db)).find((row) => row.table === before.table);
    if (after) lines.push(formatRelation("after", after));
  }
  const databaseAfter = await databaseBytes(db);
  lines.push(`database ${databaseAfter}`);
  return { databaseBefore, databaseAfter, lines };
}
