import { describe, expect, it } from "vitest";
import {
  BUDGET_BYTES,
  EST_RESULT_BYTES,
  companyLoadAllowed,
  estimateRowsFromGzip,
  fitsBudget,
  formatMb,
  overMeasuredBudget,
} from "../ingest/budget.ts";
import { companyEstimateBytes } from "../ingest/companies.ts";
import { unitsFromGeoCsv } from "../ingest/units.ts";

describe("load budget", () => {
  it("keeps a group under 350 MB and flags the rest", () => {
    expect(fitsBudget(0, BUDGET_BYTES)).toBe(true);
    expect(fitsBudget(BUDGET_BYTES, 1)).toBe(false);
    expect(overMeasuredBudget(BUDGET_BYTES)).toBe(false);
    expect(overMeasuredBudget(BUDGET_BYTES + 1)).toBe(true);
    // 300 MB plus the old 105 MB company guess would have been refused. The gate uses the live size only.
    expect(fitsBudget(300 * 1024 * 1024, companyEstimateBytes())).toBe(false);
    expect(companyLoadAllowed(300 * 1024 * 1024, false)).toBe(true);
    expect(companyLoadAllowed(BUDGET_BYTES + 1, false)).toBe(false);
    expect(companyLoadAllowed(BUDGET_BYTES + 1, true)).toBe(true);
    expect(formatMb(BUDGET_BYTES)).toBe("350 MB");
    const rows = estimateRowsFromGzip(3_957_915);
    expect(rows).toBe(Math.ceil(3_957_915 * 0.17));
    expect(rows * EST_RESULT_BYTES).toBeGreaterThan(BUDGET_BYTES);
  });

  it("maps TIGER school and legislative sets onto unit types", () => {
    const text = [
      "layer,state,row,v2_name,geoid,tiger_name,tiger_set,match",
      "schools,Alabama,0,Fort Rucker,0100001,Fort Rucker School District,unsd,name",
      "schools,Alabama,1,Example,0100002,Example Elementary,elsd,name",
      "senate,Arizona,2,001,04001,State Senate District 1,sldu,code",
    ].join("\n");
    const built = unitsFromGeoCsv(text);
    expect(built.gaps).toEqual([]);
    expect(built.units.map((unit) => [unit.unit_type, unit.unit_key, unit.source_record_id])).toEqual([
      ["school_unified", "0100001", "0"],
      ["school_elementary", "0100002", "1"],
      ["sldu", "04001", "2"],
    ]);
    const house = unitsFromGeoCsv(
      "layer,state,row,v2_name,geoid,tiger_name,tiger_set,match\nstatehouse,Nebraska,9,007,31007,State Senate District 7,sldu,code\nstatehouse,Nebraska,10,001,31001,State House District 1,sldl,code\n",
      ["sldl"],
    );
    expect(house.units.map((unit) => unit.unit_type)).toEqual(["sldl"]);
  });
});
