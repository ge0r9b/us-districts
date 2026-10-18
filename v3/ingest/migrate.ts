import pg from "pg";
import { applyMigrations, applySeed, type MigrationReport, type Queryable } from "../db/apply.ts";

async function withClient<T>(connectionString: string, fn: (db: Queryable) => Promise<T>): Promise<T> {
  const client = new pg.Client({ connectionString });
  await client.connect();
  try {
    return await fn(client);
  } finally {
    await client.end();
  }
}

/** Apply v3/db/migrations over TCP. Tests and CI use this. npm run db:migrate picks the driver. */
export function migrate(connectionString: string): Promise<MigrationReport> {
  return withClient(connectionString, applyMigrations);
}

/** Apply v3/db/seed.sql over TCP. Reference rows, safe to repeat. */
export function seed(connectionString: string): Promise<void> {
  return withClient(connectionString, applySeed);
}
