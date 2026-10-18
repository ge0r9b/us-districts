import { describe, expect, it } from "vitest";
import {
  applyFormat,
  assignAnswerKeys,
  contestKey,
  displaySlots,
  GEOGRAPHY_LEVELS,
  geographyLevel,
  INSTITUTIONS,
  matchesInstitution,
  methodRank,
  sortRows,
} from "@usd/core";

describe("display slots", () => {
  it("puts King ahead of the Democrat in Maine", () => {
    const slots = displaySlots([
      { answerKey: "cand:kouzounas-demi", party: "rep", votes: 284338 },
      { answerKey: "dem_nominee", party: "dem", votes: 88891 },
      { answerKey: "cand:king-angus-s-jr", party: "ind", votes: 427331 },
      { answerKey: "cand:cherry-jason-s", party: "ind", votes: 20222 },
    ]);
    expect(slots.d).toEqual({ answerKey: "cand:king-angus-s-jr", rule: "independent_beat_dem" });
    expect(slots.r?.answerKey).toBe("cand:kouzounas-demi");
  });

  it("fills d with Sanders when there is no Democrat", () => {
    const slots = displaySlots([
      { answerKey: "rep_nominee", party: "rep", votes: 116512 },
      { answerKey: "cand:sanders-bernard", party: "ind", votes: 229429 },
      { answerKey: "other", party: "oth", votes: 100, aggregate: true },
    ]);
    expect(slots.d).toEqual({ answerKey: "cand:sanders-bernard", rule: "no_dem" });
  });

  it("does not let a write-in take the empty Democratic slot", () => {
    const slots = displaySlots([
      { answerKey: "rep_nominee", party: "rep", votes: 499124 },
      { answerKey: "cand:osborn-dan", party: "ind", votes: 436493 },
      { answerKey: "cand:write-ins", party: "wri", votes: 2719 },
    ]);
    expect(slots.d).toEqual({ answerKey: "cand:osborn-dan", rule: "no_dem" });
  });

  it("keeps the leading Republican when several Republicans run", () => {
    const slots = displaySlots([
      { answerKey: "cand:murkowski-lisa", party: "rep", votes: 113495 },
      { answerKey: "cand:tshibaka-kelly-c", party: "rep", votes: 111480 },
      { answerKey: "dem_nominee", party: "dem", votes: 27145 },
    ]);
    expect(slots.r).toEqual({ answerKey: "cand:murkowski-lisa", rule: "rep_nominee" });
    expect(slots.d?.answerKey).toBe("dem_nominee");
  });
});

describe("answer keys and sort", () => {
  it("uses dem_nominee only when one Democrat is on the ballot", () => {
    const one = assignAnswerKeys([
      { candidateId: "a", party: "DEM" },
      { candidateId: "b", party: "REP" },
    ]);
    expect(one.map((row) => row.answerKey)).toEqual(["dem_nominee", "rep_nominee"]);
    const repeated = assignAnswerKeys([
      { candidateId: "a", party: "DEM" },
      { candidateId: "a", party: "DEM" },
      { candidateId: "b", party: "REP" },
    ]);
    expect(repeated.map((row) => row.answerKey)).toEqual(["dem_nominee", "dem_nominee", "rep_nominee"]);
    const two = assignAnswerKeys([
      { candidateId: "a", party: "DEM" },
      { candidateId: "c", party: "DEM" },
      { candidateId: "b", party: "REP" },
    ]);
    expect(two.map((row) => row.answerKey)).toEqual(["cand:a", "cand:c", "rep_nominee"]);
  });

  it("builds a national presidential contest key", () => {
    expect(contestKey({ year: 2016, office: "president", state: "AL" })).toBe("2016|US|president|");
    expect(contestKey({ year: 2024, office: "us_senate_special", state: "ne" })).toBe("2024|NE|us_senate_special|");
  });

  it("ranks official above a v2 import", () => {
    expect(methodRank("official")).toBeGreaterThan(methodRank("v2_import"));
    expect(methodRank("retabulated")).toBeGreaterThan(methodRank("v2_import"));
  });

  it("sorts high to low and keeps missing rows last, A to Z", () => {
    const desc = sortRows(
      [
        { name: "Zed", share: null, votes: null, gray: true },
        { name: "Ada", share: 0.2, votes: 2, gray: false },
        { name: "Bea", share: 0.8, votes: 8, gray: false },
        { name: "Amy", share: null, votes: null, gray: true },
      ],
      "share",
      "desc",
    );
    expect(desc.map((row) => row.name)).toEqual(["Bea", "Ada", "Amy", "Zed"]);
    const asc = sortRows(
      [
        { name: "Bea", share: 0.8, votes: 8 },
        { name: "Ada", share: 0.2, votes: 2 },
        { name: "Zed", share: null, votes: null, gray: true },
      ],
      "votes",
      "asc",
    );
    expect(asc.map((row) => row.name)).toEqual(["Ada", "Bea", "Zed"]);
  });

  it("drops shares in number mode and counts in percent mode", () => {
    const row = { votes: [1], share: [0.5], total: 2, name: "Ada" };
    expect(applyFormat(row, "pct")).toEqual({ share: [0.5], name: "Ada" });
    expect(applyFormat(row, "num")).toEqual({ votes: [1], total: 2, name: "Ada" });
  });

  it("keeps institution and geography filters apart", () => {
    expect(INSTITUTIONS.map((item) => item.key)).toEqual(["president"]);
    expect(matchesInstitution("president", "president")).toBe(true);
    expect(matchesInstitution("sldu", "president")).toBe(false);
    expect(GEOGRAPHY_LEVELS.map((item) => item.key)).toEqual(["state", "county", "precinct"]);
    expect(geographyLevel("precinct")).toBe("precinct");
    expect(geographyLevel("president")).toBeNull();
  });
});
