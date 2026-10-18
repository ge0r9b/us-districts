import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  countyPresOverlay,
  readPresTable,
  statePresTotals,
  type VoteTriple,
} from "../ingest/legacy.ts";

const root = fileURLToPath(new URL("../..", import.meta.url));

function v2(name: string): string {
  return readFileSync(join(root, "v2/data", name), "utf8");
}

function add(rows: VoteTriple[]): VoteTriple {
  return rows.reduce<VoteTriple>((sum, triple) => [sum[0] + triple[0], sum[1] + triple[1], sum[2] + triple[2]], [0, 0, 0]);
}

describe("2020 and 2024 president supplements", () => {
  const ak = v2("ak.js");
  const dc = v2("dc.js");
  const election2016 = v2("election2016.js");
  const election2020 = v2("election2020.js");
  const election2024 = v2("election2024.js");

  it("keeps 2016 counties on election2016.js, including Alaska and Kalawao", () => {
    const table = readPresTable(election2016);
    expect(Object.keys(table).filter((key) => key.startsWith("Alaska|"))).toHaveLength(30);
    expect(table["District of Columbia|District of Columbia"]).toEqual([282830, 12723, 311268]);
    expect(table["Hawaii|Kalawao County"]).toEqual([14, 1, 20]);
    const later = readPresTable(election2020);
    expect(Object.keys(later).some((key) => key.startsWith("Alaska|"))).toBe(false);
    expect(later["Hawaii|Kalawao County"]).toBeUndefined();
    expect(later["District of Columbia|District of Columbia"]).toBeUndefined();
  });

  it("adds 30 Alaska boroughs and the DC city triple for 2020 and 2024", () => {
    const overlay2020 = countyPresOverlay(2020, ak, dc);
    const overlay2024 = countyPresOverlay(2024, ak, dc);
    expect(Object.keys(overlay2020).filter((key) => key.startsWith("Alaska|"))).toHaveLength(30);
    expect(Object.keys(overlay2024).filter((key) => key.startsWith("Alaska|"))).toHaveLength(30);
    expect(overlay2020["District of Columbia|District of Columbia"]).toEqual([317323, 18586, 344356]);
    expect(overlay2024["District of Columbia|District of Columbia"]).toEqual([294185, 21076, 325869]);
    expect(overlay2020["Alaska|Anchorage Municipality"]).toEqual([71114, 68015, 144262]);
    expect(overlay2024["Alaska|Anchorage Municipality"]).toEqual([64780, 62922, 132898]);
  });

  it("uses the official Alaska state total and the DC city total as the state rows", () => {
    for (const [year, election] of [
      [2020, election2020],
      [2024, election2024],
    ] as const) {
      const overlay = countyPresOverlay(year, ak, dc);
      const totals = statePresTotals(election, year, ak, dc);
      const boroughSum = add(Object.entries(overlay).filter(([key]) => key.startsWith("Alaska|")).map(([, triple]) => triple));
      expect(Object.keys(totals)).toHaveLength(51);
      expect(totals["District of Columbia"]).toEqual(overlay["District of Columbia|District of Columbia"]);
      if (year === 2020) expect(totals.Alaska).toEqual([153778, 189951, 357569]);
      if (year === 2024) expect(totals.Alaska).toEqual([140026, 184458, 338177]);
      expect(totals.Alaska).not.toEqual(boroughSum);
      const california = add(
        Object.entries(readPresTable(election))
          .filter(([key]) => key.startsWith("California|"))
          .map(([, triple]) => triple),
      );
      expect(totals.California).toEqual(california);
    }
  });
});
