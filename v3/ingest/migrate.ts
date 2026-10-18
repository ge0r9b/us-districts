import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import pg from "pg";

const schemaPath = fileURLToPath(new URL("../../docs/v3/SCHEMA.sql", import.meta.url));

export function schemaSql(): { sql: string; checksum: string } {
  const sql = readFileSync(schemaPath, "utf8");
  const checksum = createHash("sha256").update(sql).digest("hex");
  return { sql, checksum };
}

/** Apply docs/v3/SCHEMA.sql once. A second call is a no-op. A changed file errors. */
export async function migrate(connectionString: string): Promise<{ applied: boolean; checksum: string }> {
  const { sql, checksum } = schemaSql();
  const client = new pg.Client({ connectionString });
  await client.connect();
  try {
    await client.query("create schema if not exists usd");
    await client.query(
      `create table if not exists usd.schema_migration (
         filename text primary key,
         checksum text not null,
         applied_at timestamptz not null default now()
       )`,
    );
    const existing = await client.query<{ checksum: string }>(
      "select checksum from usd.schema_migration where filename = 'SCHEMA.sql'",
    );
    if (existing.rows[0]) {
      if (existing.rows[0].checksum !== checksum) {
        throw new Error(
          "docs/v3/SCHEMA.sql changed after it was applied. Add a new migration file instead of editing the applied checksum in place.",
        );
      }
      return { applied: false, checksum };
    }
    await client.query("begin");
    try {
      await client.query(sql);
      await client.query("insert into usd.schema_migration (filename, checksum) values ('SCHEMA.sql', $1)", [checksum]);
      await client.query("commit");
    } catch (err) {
      await client.query("rollback");
      throw err;
    }
    return { applied: true, checksum };
  } finally {
    await client.end();
  }
}
