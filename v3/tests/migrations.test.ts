import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { isNeonHost } from "../db/connect.ts";
import { splitSql, stripComments } from "../db/sql.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const migrationsDir = join(root, "db", "migrations");
const schemaPath = join(root, "..", "docs", "v3", "SCHEMA.sql");

const expected = [
  "001_extensions.sql",
  "002_tenancy.sql",
  "003_geography.sql",
  "004_entities.sql",
  "005_contests_results.sql",
  "006_people.sql",
  "007_aggregates.sql",
  "008_ingest.sql",
  "009_load_columns.sql",
  "010_precinct_rollup.sql",
  "011_inst_entities.sql",
  "012_location_units.sql",
];

describe("migration files", () => {
  const names = readdirSync(migrationsDir).filter((name) => name.endsWith(".sql")).sort();
  const sql = names.map((name) => readFileSync(join(migrationsDir, name), "utf8")).join("\n");
  const seed = readFileSync(join(root, "db", "seed.sql"), "utf8");
  const schema = readFileSync(schemaPath, "utf8");

  it("lists the ordered files and no connection string", () => {
    expect(names).toEqual(expected);
    expect(sql + seed).not.toMatch(/postgres(ql)?:\/\//);
    expect(sql).toContain("create extension if not exists postgis");
    for (const name of names) {
      expect(readFileSync(join(migrationsDir, name), "utf8")).toContain("set search_path = usd, public");
    }
  });

  it("keeps every table, index, and matview from SCHEMA.sql, and moves inserts to the seed", () => {
    const tables = [...schema.matchAll(/^create (unlogged )?table (\w+)/gim)];
    for (const match of tables) {
      const needle = match[1]
        ? `create unlogged table if not exists ${match[2]}`
        : `create table if not exists ${match[2]}`;
      expect(sql).toContain(needle);
    }
    for (const match of schema.matchAll(/^create (?:unique )?index (\w+)/gim)) {
      expect(sql).toContain(`index if not exists ${match[1]}`);
    }
    for (const match of schema.matchAll(/^create materialized view (\w+)/gim)) {
      expect(sql).toContain(`relname = '${match[1]}'`);
      expect(sql).toContain(`create materialized view ${match[1]}`);
    }
    expect(sql.toLowerCase()).not.toContain("insert into");
    const inserts = [...schema.matchAll(/^insert into (\w+)/gim)].map((match) => match[1]);
    expect(inserts.length).toBeGreaterThan(0);
    for (const table of inserts) {
      expect(seed).toContain(`insert into ${table}`);
    }
    for (const statement of splitSql(seed)) {
      const body = stripComments(statement).trim();
      if (/^insert\s+into\b/i.test(body)) expect(body.toLowerCase()).toContain("on conflict");
    }
  });

  it("uses the WebSocket driver only for a neon.tech host", () => {
    expect(isNeonHost("postgresql://user:secret@ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require")).toBe(true);
    expect(isNeonHost("postgresql://usd:usd@127.0.0.1:5432/usd_v3")).toBe(false);
  });

  it("does not split a dollar-quoted do block on an inner semicolon", () => {
    const parts = splitSql(`
      -- keep; this comment
      do $mv$
      begin
        execute $sql$select 1;$sql$;
      end
      $mv$;
      select 2;
    `);
    expect(parts).toHaveLength(2);
    expect(parts[0]).toContain("do $mv$");
    expect(stripComments(parts[1])).toBe("select 2");
  });
});
