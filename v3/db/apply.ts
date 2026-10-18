import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { splitSql } from "./sql.ts";

const root = dirname(fileURLToPath(import.meta.url));
const migrationsDir = join(root, "migrations");
const seedPath = join(root, "seed.sql");

export type Queryable = {
  query(text: string, params?: unknown[]): Promise<{ rows: Array<Record<string, unknown>> }>;
};

export type MigrationReport = {
  applied: string[];
  skipped: string[];
};

export function migrationPaths(): string[] {
  return readdirSync(migrationsDir)
    .filter((name) => name.endsWith(".sql"))
    .sort()
    .map((name) => join(migrationsDir, name));
}

const bookkeeping = `
create schema if not exists usd;
create table if not exists usd.schema_migration (
  filename text primary key,
  checksum text not null,
  applied_at timestamptz not null default now()
);
`;

/** Apply v3/db/migrations in order. An unchanged file is skipped. An edited applied file throws. */
export async function applyMigrations(db: Queryable): Promise<MigrationReport> {
  for (const statement of splitSql(bookkeeping)) {
    await db.query(statement);
  }
  const applied: string[] = [];
  const skipped: string[] = [];
  for (const path of migrationPaths()) {
    const filename = basename(path);
    const sql = readFileSync(path, "utf8");
    const checksum = createHash("sha256").update(sql).digest("hex");
    const existing = await db.query("select checksum from usd.schema_migration where filename = $1", [filename]);
    const previous = existing.rows[0]?.checksum;
    if (typeof previous === "string") {
      if (previous !== checksum) {
        throw new Error(
          `${filename} changed after it was applied. Add a new numbered file instead of editing an applied migration.`,
        );
      }
      skipped.push(filename);
      continue;
    }
    await db.query("begin");
    try {
      for (const statement of splitSql(sql)) {
        await db.query(statement);
      }
      await db.query("insert into usd.schema_migration (filename, checksum) values ($1, $2)", [filename, checksum]);
      await db.query("commit");
    } catch (err) {
      await rollback(db);
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(`${filename}: ${message}`);
    }
    applied.push(filename);
  }
  return { applied, skipped };
}

/** Apply v3/db/seed.sql. Reference inserts are idempotent, so this is not checksum-locked. */
export async function applySeed(db: Queryable): Promise<void> {
  const sql = readFileSync(seedPath, "utf8");
  await db.query("begin");
  try {
    for (const statement of splitSql(sql)) {
      await db.query(statement);
    }
    await db.query("commit");
  } catch (err) {
    await rollback(db);
    throw err;
  }
}

async function rollback(db: Queryable): Promise<void> {
  try {
    await db.query("rollback");
  } catch {
    // The connection may already be aborted.
  }
}
