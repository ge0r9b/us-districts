import { afterAll, describe, expect, it } from "vitest";
import { BUDGET_BYTES } from "../ingest/budget.ts";
import { databaseSizeReport, measuredRelationBytes, sizePlan, slimInstitutionBytes } from "../ingest/size-plan.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();

afterAll(async () => {
  await pool.end();
});

describe("database size", () => {
  it("prices the shrunk plan under 350 MB decimal and under the load gate", () => {
    const plan = sizePlan();
    expect(plan.measuredInstitutionDeltaBytes).toBe(77_037_568);
    expect(plan.neonAfterInstitutionsBytes - plan.neonBeforeInstitutionsBytes).toBe(77_037_568);
    expect(measuredRelationBytes()).toBeGreaterThan(77_000_000);
    expect(measuredRelationBytes()).toBeLessThan(78_500_000);
    expect(plan.localInstitutionDeltaBytes).toBeGreaterThan(77_000_000);
    expect(plan.shrinkBytes).toBe(
      plan.vacuumEntityBytes + plan.sidePackBytes + plan.partialIndexBytes + plan.surrogateNetBytes,
    );
    expect(plan.finalBytes).toBe(plan.afterShrinkBytes + plan.precinctRollupBytes + plan.foreignGovernmentBytes);
    expect(plan.foreignGovernmentRows).toBe(62_939);
    expect(plan.foreignGovernmentKinds).toEqual([
      "county",
      "municipality",
      "local_authority",
      "regional_authority",
      "intermunicipal",
      "submunicipal",
      "parish",
    ]);
    expect(plan.precinctRollupBytes).toBeLessThan(3_000_000);
    expect(plan.finalBytes).toBeLessThan(350_000_000);
    expect(plan.finalBytes).toBeLessThan(BUDGET_BYTES);
    expect(plan.underDecimalBudget).toBe(true);
    expect(plan.underGate).toBe(true);
    const slim = slimInstitutionBytes({
      entities: 58_219,
      relations: 4_153,
      images: 9_846,
      aliases: 0,
      bodies: 198,
    });
    expect(slim).toBeGreaterThan(15_000_000);
    expect(slim).toBeLessThan(40_000_000);
  });

  it("reports heap, indexes, toast, and dead tuples without writing", async () => {
    const before = await pool.query<{ n: string }>("select count(*)::text n from entity");
    const report = await databaseSizeReport(pool);
    const after = await pool.query<{ n: string }>("select count(*)::text n from entity");
    expect(after.rows[0]?.n).toBe(before.rows[0]?.n);
    expect(report.databaseBytes).toBeGreaterThan(0);
    expect(report.tables.length).toBeGreaterThan(10);
    const entity = report.tables.find((row) => row.table === "entity");
    expect(entity).toBeDefined();
    expect(entity!.heap).toBeGreaterThan(0);
    expect(entity!.indexes).toBeGreaterThan(0);
    expect(entity!.toast).toBeGreaterThanOrEqual(0);
    expect(entity!.total).toBeGreaterThanOrEqual(entity!.heap);
    expect(report.plan.finalBytes).toBeLessThan(350_000_000);
  });
});
