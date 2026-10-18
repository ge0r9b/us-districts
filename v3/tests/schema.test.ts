import { afterAll, describe, expect, it } from "vitest";
import { migrate, seed } from "../ingest/migrate.ts";
import { createTestPool, testDatabaseUrl } from "./db.ts";

const pool = createTestPool();

afterAll(async () => {
  await pool.end();
});

describe("schema", () => {
  it("applies PostGIS, the public tenant, boundary sets, and data_version", async () => {
    const postgis = await pool.query<{ ext: string }>("select postgis_version() as ext");
    expect(postgis.rows[0]?.ext).toMatch(/^3\./);
    const tenant = await pool.query<{ id: string; slug: string }>(
      "select id::text, slug from tenant where slug = 'public'",
    );
    expect(tenant.rows[0]).toEqual({ id: "1", slug: "public" });
    const sets = await pool.query<{ n: string; current: string }>(
      "select count(*)::text n, count(*) filter (where is_current)::text as current from boundary_set",
    );
    expect(Number(sets.rows[0]?.n)).toBeGreaterThanOrEqual(42);
    expect(Number(sets.rows[0]?.current)).toBeGreaterThanOrEqual(33);
    const types = await pool.query<{ n: string }>("select count(*)::text n from unit_type_def");
    expect(Number(types.rows[0]?.n)).toBeGreaterThanOrEqual(21);
    const dv = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    expect(dv.rows[0]?.dv).toBeGreaterThanOrEqual(1);
  });

  it("skips migration files that are already applied", async () => {
    const again = await migrate(testDatabaseUrl());
    expect(again.applied).toEqual([]);
    expect(again.skipped).toHaveLength(8);
  });

  it("seeds again without duplicating reference rows", async () => {
    const before = await pool.query<{ tenants: string; sets: string }>(
      `select (select count(*) from tenant)::text as tenants,
              (select count(*) from boundary_set)::text as sets`,
    );
    await seed(testDatabaseUrl());
    const after = await pool.query<{ tenants: string; sets: string; id: string }>(
      `select (select count(*) from tenant)::text as tenants,
              (select count(*) from boundary_set)::text as sets,
              (select id::text from tenant where slug = 'public') as id`,
    );
    expect(after.rows[0]?.tenants).toBe(before.rows[0]?.tenants);
    expect(after.rows[0]?.sets).toBe(before.rows[0]?.sets);
    expect(after.rows[0]?.id).toBe("1");
  });
});
