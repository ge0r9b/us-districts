import pg from "pg";
import { createPool } from "../ingest/db.ts";
import { loadAll } from "../ingest/load-all.ts";
import { migrate, seed } from "../ingest/migrate.ts";
import { databaseUrl, testDatabaseUrl } from "./db.ts";

export async function setup(): Promise<void> {
  const admin = new URL(databaseUrl());
  admin.pathname = "/postgres";
  const client = new pg.Client({ connectionString: admin.toString() });
  await client.connect();
  await client.query(
    `select pg_terminate_backend(pid) from pg_stat_activity where datname = 'usd_v3_test' and pid <> pg_backend_pid()`,
  );
  await client.query("drop database if exists usd_v3_test");
  await client.query("create database usd_v3_test");
  await client.end();

  const url = testDatabaseUrl();
  await migrate(url);
  await seed(url);
  const pool = createPool(url);
  try {
    const summary = await loadAll(pool);
    const rejected = summary.results.filter((row) => row.status === "rejected");
    if (rejected.length > 0) {
      const sample = rejected
        .map((row) => `${row.fileName} ${row.rejected}/${row.rows} ${row.rejects[0]?.rule ?? ""}`)
        .join("; ");
      throw new Error(`loader rejected a batch: ${sample}`);
    }
  } finally {
    await pool.end();
  }
}
