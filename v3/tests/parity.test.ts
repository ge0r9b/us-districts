import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  CANADA_PROVINCES,
  chartMenu,
  institutionField,
  legendText,
  lineYears,
  marginColor,
  MARGIN_MAX,
  pickUnit,
  placeChain,
  pointerTap,
  precinctLabel,
  rangeStartVotes,
  resolveChart,
  searchInstitutions,
  segmentChanges,
  sliderFrame,
  sliderLabelXs,
  thumbnailBox,
  THUMB_PX,
  topInstitutionHit,
  twinKey,
} from "@usd/core";

const tokens = JSON.parse(readFileSync(new URL("../design/tokens.json", import.meta.url), "utf8")) as {
  thumbPx: number;
  margin: { max: number };
  marginScale: { demStop: number; repStop: number; max: number };
};

describe("margin scale", () => {
  it("is linear to ±90 and does not clamp at ±60", () => {
    expect(MARGIN_MAX).toBe(0.9);
    expect(tokens.margin.max).toBe(90);
    expect(tokens.marginScale.max).toBe(0.9);
    expect(tokens.marginScale.demStop).toBe(-0.9);
    expect(tokens.marginScale.repStop).toBe(0.9);
    expect(marginColor(-0.9)).toBe("#2563eb");
    expect(marginColor(-1)).toBe("#2563eb");
    expect(marginColor(0)).toBe("#f5f5f4");
    expect(marginColor(0.9)).toBe("#dc2626");
    expect(marginColor(1)).toBe("#dc2626");
    expect(marginColor(-0.6)).not.toBe("#2563eb");
    expect(marginColor(0.7)).not.toBe("#dc2626");
    expect(legendText(2016, false)).toContain("Clinton");
    expect(legendText(2016, false)).toContain("+90");
    expect(legendText(2016, true)).toContain("+90");
    expect(legendText(2020, false)).toContain("Biden");
    expect(legendText(2024, true)).toContain("Harris");
    expect(legendText(2024, true)).toContain("+90");
  });
});

describe("chart menu", () => {
  it("offers pie and bar for one year, line and bar for a range", () => {
    expect(chartMenu([2016])).toEqual(["pie", "bar"]);
    expect(chartMenu([2016, 2020, 2024])).toEqual(["line", "bar"]);
    expect(resolveChart("pie", [2024])).toBe("pie");
    expect(resolveChart("line", [2024])).toBe("bar");
    expect(resolveChart("pie", [2016, 2020, 2024])).toBe("bar");
    expect(resolveChart("line", [2016, 2024])).toBe("line");
    expect(resolveChart("nope", [2016])).toBe("bar");
    expect(lineYears(2016, 2024)).toEqual([2016, 2020, 2024]);
    expect(lineYears(2016, 2020)).toEqual([2016, 2020]);
    const changes = segmentChanges([2016, 2020, 2024], [-0.02, 0.01, 0.04]);
    expect(changes.map((item) => item.label)).toEqual(["'16>'20 +3.0", "'20>'24 +3.0"]);
  });
});

describe("institution field", () => {
  it("searches every level, stays filled, and enters the top match", () => {
    expect(CANADA_PROVINCES).toHaveLength(13);
    expect(institutionField("", "")).toBe("United States");
    expect(institutionField("   ", "Canada")).toBe("Canada");
    expect(institutionField("  pa ", "Canada")).toBe("pa");
    const empty = searchInstitutions("  ");
    expect(empty.message).toBeNull();
    expect(empty.groups[0]?.hits[0]?.label).toBe("United States");
    expect(searchInstitutions("usa").groups[0]?.hits[0]?.label).toBe("United States");
    expect(searchInstitutions("america").groups.flatMap((g) => g.hits).some((h) => h.label === "United States")).toBe(true);
    expect(topInstitutionHit("PA")?.label).toBe("Pennsylvania");
    expect(topInstitutionHit("DC")?.label).toBe("District of Columbia");
    const counties = searchInstitutions("jefferson", [{ id: "county:42065", label: "Jefferson County" }]);
    expect(counties.groups.some((g) => g.name === "Counties" && g.hits[0]?.label === "Jefferson County")).toBe(true);
    const ontario = searchInstitutions("Ontario").groups.flatMap((g) => g.hits).find((h) => h.label === "Ontario");
    expect(ontario?.gray).toBe(true);
    expect(ontario?.note).toBe("Canada units load in v3.1");
    expect(topInstitutionHit("ON")?.label).toBe("Ontario");
    const miss = searchInstitutions("zzzz-no-such");
    expect(miss.message).toBe("No institutions match");
    expect(miss.groups).toEqual([]);
    expect(topInstitutionHit("zzzz-no-such")).toBeNull();
  });
});

describe("address place chain", () => {
  it("moves state, county, and precinct together and skips a county for DC", () => {
    const pa = placeChain([
      { unit_type: "state", unit_key: "42", state_abbr: "PA", name: "Pennsylvania" },
      { unit_type: "county", unit_key: "42101", state_abbr: "PA", name: "Philadelphia County" },
      { unit_type: "precinct", unit_key: "42101-1", state_abbr: "PA", name: "Philadelphia County|Ward 1 Division 1" },
    ]);
    expect(pa.dc).toBe(false);
    expect(pa.stateAbbr).toBe("PA");
    expect(pa.countyKey).toBe("42101");
    expect(pa.precinctLabel).toBe("Ward 1 Division 1");
    expect(pa.crumbs).toEqual(["Pennsylvania", "Philadelphia County", "Ward 1 Division 1"]);
    expect(pa.level).toBe("precinct");
    const dc = placeChain([
      { unit_type: "state", unit_key: "11", state_abbr: "DC", name: "District of Columbia" },
      { unit_type: "county", unit_key: "11001", state_abbr: "DC", name: "District of Columbia" },
      { unit_type: "precinct", unit_key: "DC|1", state_abbr: "DC", name: "Precinct 12" },
    ]);
    expect(dc.dc).toBe(true);
    expect(dc.countyKey).toBeNull();
    expect(dc.countyName).toBeNull();
    expect(dc.crumbs).toEqual(["District of Columbia", "Precinct 12"]);
    expect(dc.level).toBe("precinct");
    expect(placeChain([{ unit_type: "state", unit_key: "11", state_abbr: "DC", name: "District of Columbia" }]).level).toBe(
      "state",
    );
    expect(precinctLabel("Philadelphia County Ward 5")).toBe("Ward 5");
  });
});

describe("2016 precinct twins", () => {
  it("reads a stored twin for a 2016 range and never invents one", () => {
    const twins = new Map([["42101-ward-1-div-1", "2016:42101-ward-1-div-1"]]);
    expect(twinKey(twins, "42101-ward-1-div-1")).toBe("2016:42101-ward-1-div-1");
    expect(twinKey(twins, "missing")).toBeNull();
    const votes = new Map<string, number>([
      ["2016|2016:42101-ward-1-div-1", 40],
      ["2024|42101-ward-1-div-1", 55],
      ["2016|42", 100],
    ]);
    const at = (year: number, key: string) => votes.get(`${year}|${key}`) ?? null;
    expect(
      rangeStartVotes({ years: [2016, 2024], unitKey: "42101-ward-1-div-1", unitType: "precinct", twins, votesAt: at }),
    ).toBe(40);
    expect(rangeStartVotes({ years: [2016, 2024], unitKey: "no-twin", unitType: "precinct", twins, votesAt: at })).toBeNull();
    expect(rangeStartVotes({ years: [2016, 2024], unitKey: "42", unitType: "state", twins, votesAt: at })).toBe(100);
    expect(
      rangeStartVotes({
        years: [2020, 2024],
        unitKey: "42101-ward-1-div-1",
        unitType: "precinct",
        twins,
        votesAt: () => 7,
      }),
    ).toBe(7);
  });
});

describe("slider and thumbnails", () => {
  it("keeps the clock fixed and reserves a 30 px thumbnail slot", () => {
    expect(sliderFrame(true).clockTop).toBe(sliderFrame(false).clockTop);
    expect(sliderFrame(false).rowVisibility).toBe("hidden");
    expect(sliderFrame(true).rowVisibility).toBe("visible");
    expect(sliderLabelXs([{ left: 10, width: 30 }, { left: 48, width: 30 }, { left: 86, width: 30 }])).toEqual([25, 63, 101]);
    expect(THUMB_PX).toBe(30);
    expect(tokens.thumbPx).toBe(30);
    expect(thumbnailBox(false)).toEqual({ size: 30, visibility: "hidden" });
    expect(thumbnailBox(true).visibility).toBe("visible");
  });
});

describe("pointer tap", () => {
  it("acts on pointerup and ignores the follow-up click", () => {
    const down = pointerTap("pointerup", false, 0);
    expect(down).toEqual({ act: true, handled: true });
    expect(pointerTap("click", down.handled, 0)).toEqual({ act: false, handled: false });
    expect(pointerTap("click", false, 0)).toEqual({ act: true, handled: false });
    expect(pointerTap("pointerup", false, 2).act).toBe(false);
  });
});

describe("pick latency", () => {
  it("looks up a US House sized index well under 100 ms", () => {
    const index = new Map<string, number>();
    for (let i = 0; i < 435; i++) index.set(`ushouse:${i}`, i);
    const start = performance.now();
    let sink = 0;
    for (let i = 0; i < 20_000; i++) sink += pickUnit(index, `ushouse:${i % 435}`) ?? 0;
    expect(performance.now() - start).toBeLessThan(100);
    expect(sink).toBeGreaterThan(0);
    expect(pickUnit(index, "ushouse:10")).toBe(10);
  });
});
