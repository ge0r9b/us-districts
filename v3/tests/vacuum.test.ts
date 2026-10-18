import { afterAll, describe, expect, it } from "vitest";
import {
  expectedHeapBytes,
  listVacuumTargets,
  migrationRewriteNotes,
  needsVacuumFull,
  vacuumFullTable,
  vacuumReminder,
  type RelationSize,
} from "../db/vacuum.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();

afterAll(async () => {
  await pool.end();
});

function row(patch: Partial<RelationSize> & Pick<RelationSize, "table" | "heapBytes">): RelationSize {
  return {
    indexBytes: 0,
    toastBytes: 0,
    totalBytes: patch.heapBytes,
    liveTuples: 0,
    deadTuples: 0,
    relTuples: 0,
    avgWidth: 0,
    droppedColumns: 0,
    empty: false,
    ...patch,
  };
}

/** Local 013→014 probe: 200,000 entity_location rows. Dropped columns remain after VACUUM FULL. */
const afterRewrite = row({
  table: "entity_location",
  heapBytes: 127_033_344,
  indexBytes: 46_817_280,
  totalBytes: 173_907_968,
  liveTuples: 200_000,
  deadTuples: 210_000,
  relTuples: 200_000,
  avgWidth: 285,
  droppedColumns: 2,
});

const afterFull = row({
  table: "entity_location",
  heapBytes: 60_579_840,
  indexBytes: 23_314_432,
  totalBytes: 83_902_464,
  liveTuples: 200_000,
  deadTuples: 0,
  relTuples: 200_000,
  avgWidth: 285,
  droppedColumns: 2,
});

describe("vacuum full", () => {
  it("selects rewrite bloat and skips a table whose dropped columns are already rewritten", () => {
    expect(expectedHeapBytes(200_000, 285)).toBe(200_000 * (285 + 24));
    expect(needsVacuumFull(afterRewrite)).toBe(true);
    expect(needsVacuumFull({ ...afterRewrite, deadTuples: 0 })).toBe(true);
    expect(needsVacuumFull(afterFull)).toBe(false);
    expect(
      needsVacuumFull(
        row({
          table: "entity_extra",
          heapBytes: 18_030_592,
          totalBytes: 18_030_592,
          empty: true,
        }),
      ),
    ).toBe(true);
    expect(
      needsVacuumFull(
        row({
          table: "unit_geom",
          heapBytes: 80_000_000,
          indexBytes: 90_000_000,
          totalBytes: 170_000_000,
          liveTuples: 300_000,
          relTuples: 300_000,
          avgWidth: 240,
        }),
      ),
    ).toBe(false);
  });

  it("reminds the operator that 014 still needs VACUUM FULL", () => {
    const notes = migrationRewriteNotes();
    const location = notes.find((note) => note.filename === "014_shrink.sql");
    expect(location?.tables).toEqual(
      expect.arrayContaining([
        { table: "entity_location", columns: ["entity_id", "sub_entity_id"] },
        { table: "entity_relation", columns: ["parent_id", "child_id"] },
      ]),
    );
    const reminder = vacuumReminder(notes, [afterRewrite]);
    expect(reminder).toContain("VACUUM FULL is required before pg_database_size shrinks.");
    expect(reminder).toContain("014_shrink.sql drops columns on entity_location (entity_id, sub_entity_id).");
    expect(reminder).toContain("heap 127033344");
    expect(reminder).toContain("Run: npm run db:vacuum");
    expect(vacuumReminder(notes, [])).toBeNull();
    expect(needsVacuumFull(afterFull)).toBe(false);
  });

  it("rewrites a bloated probe and leaves it off the next list", async () => {
    await pool.query("drop table if exists usd.vacuum_probe");
    await pool.query("create table usd.vacuum_probe (id int primary key, payload text)");
    await pool.query("alter table usd.vacuum_probe set (autovacuum_enabled = false)");
    try {
      await pool.query(
        `insert into usd.vacuum_probe select i, repeat('x', 500) from generate_series(1, 8000) s(i)`,
      );
      await pool.query("update usd.vacuum_probe set payload = payload || 'y'");
      await pool.query("analyze usd.vacuum_probe");
      const bloated = await listVacuumTargets(pool);
      const probe = bloated.find((item) => item.table === "vacuum_probe");
      expect(probe).toBeTruthy();
      const before = probe!.heapBytes;

      await pool.query("vacuum (analyze) usd.vacuum_probe");
      const still = (await listVacuumTargets(pool)).find((item) => item.table === "vacuum_probe");
      expect(still).toBeTruthy();
      expect(still!.heapBytes).toBeGreaterThan(before * 0.9);
      expect(still!.deadTuples).toBe(0);

      await vacuumFullTable(pool, "vacuum_probe");
      const after = (await listVacuumTargets(pool)).find((item) => item.table === "vacuum_probe");
      expect(after).toBeUndefined();
      const size = await pool.query<{ heap: string }>(
        `select pg_relation_size('usd.vacuum_probe'::regclass)::text as heap`,
      );
      expect(Number(size.rows[0]?.heap)).toBeLessThan(before);
    } finally {
      await pool.query("drop table if exists usd.vacuum_probe");
    }
  });
});
