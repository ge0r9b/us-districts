import { execFileSync } from "node:child_process";
import { afterAll, describe, expect, it } from "vitest";
import { loadCompanyRows } from "../ingest/companies.ts";
import { parseCsv } from "../ingest/csv.ts";
import { repoRoot } from "../ingest/load-all.ts";
import {
  AIRLINE_HQ_ROWS,
  AIRLINE_ROWS,
  COLLEGE_IPEDS_ROWS,
  COLLEGE_ROWS,
  ORG_REL,
  TELECOM_HQ_ROWS,
  TELECOM_ROWS,
  boundaryForCountry,
  ipedsUnit,
  mapAirline,
  mapCollege,
  mapOrgLocation,
  mapOrgLogo,
  mapTelecom,
  orgDate,
  planIdMerge,
  writeOrganizationEntities,
} from "../ingest/organizations.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();
const root = repoRoot();

afterAll(async () => {
  await pool.end();
});

function show(rel: string): string {
  return execFileSync("git", ["show", `origin/data/companies:${rel}`], {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
}

describe("organization ids and locations", () => {
  it("plans ipeds_to_qid the same way as usd_to_qid and keeps pre-2016 company dates", () => {
    expect(planIdMerge("usd:3f2c1a00-0000-4000-8000-000000000001", "wikidata:Q1046951")).toEqual({
      from_id: "usd:3f2c1a00-0000-4000-8000-000000000001",
      into_id: "wikidata:Q1046951",
      match_rule: "usd_to_qid",
    });
    expect(planIdMerge("ipeds:442523", "wikidata:Q4708506")).toEqual({
      from_id: "ipeds:442523",
      into_id: "wikidata:Q4708506",
      match_rule: "ipeds_to_qid",
    });
    expect(planIdMerge("ipeds:442523", "ipeds:442523")).toBeNull();
    expect(ipedsUnit("ipeds:442523", "")).toBe("442523");
    expect(orgDate("1955-01-27")).toEqual({ date: "1955-01-27", precision: "day" });
    expect(orgDate("2014")).toEqual({ date: "2014-01-01", precision: "year" });
    expect(orgDate("")).toEqual({ date: null, precision: null });
    const college = mapCollege({
      entity_id: "ipeds:442523",
      kind: "company",
      name: "Example College",
      unitid: "442523",
      country_code: "US",
      wikidata_qid: "wikidata:Q4708506",
      system_entity_id: "wikidata:Q4708506",
    });
    expect(college?.aliases).toEqual([
      { alias: "442523", entity_id: "ipeds:442523", kind: "external_id", scheme: "ipeds" },
    ]);
    expect(college?.merge?.match_rule).toBe("ipeds_to_qid");
    expect(college?.parents).toEqual(["wikidata:Q4708506"]);
    const airline = mapAirline({
      entity_id: "wikidata:Q151581",
      kind: "company",
      name: "Example Air",
      country_code: "FO",
      inception: "2014",
      parent_entity_id: "wikidata:Q999",
      logo_file: "example.svg",
      logo_license: "CC0",
      logo_attribution: "Example",
    });
    expect(airline?.inception).toBe("2014-01-01");
    expect(airline?.inception_precision).toBe("year");
    expect(airline?.country).toBe("fo");
    expect(mapOrgLogo({ logo_file: "a.svg", logo_license: "fair-use", logo_attribution: "Ex" })).toBeNull();
    expect(mapOrgLogo({
      logo_file: "a.svg",
      logo_license: "fair-use",
      logo_attribution: "Ex",
      logo_source_url: "https://example.test/logo",
    })?.public).toBe(false);
    const abroad = mapOrgLocation({
      location_id: "airlines_world:hq:Q151581",
      entity_id: "wikidata:Q151581",
      role: "hq_in",
      country_code: "RU",
      boundary_set: "v2-2024",
      lat: "55.75",
      lon: "37.62",
    });
    expect(abroad?.boundary_set).toBe("");
    expect(boundaryForCountry("US", "v2-2024")).toBe("v2-2024");
    expect(mapTelecom({
      entity_id: "wikidata:Q999001",
      kind: "brand",
      brand_name: "Example Mobile",
      country_code: "US",
      corporate_qid: "wikidata:Q999002",
    })?.parents).toEqual(["wikidata:Q999002"]);
  });

  it("inserts an ipeds college, a null non-US boundary, and a US hq boundary", async () => {
    const college = mapCollege({
      entity_id: "ipeds:442523",
      kind: "company",
      name: "Example College",
      unitid: "442523",
      country_code: "US",
      wikidata_qid: "wikidata:Q4708506",
      system_entity_id: "wikidata:Q4708506",
      logo_file: "example.svg",
      logo_license: "CC0",
      logo_attribution: "Example College",
      logo_source_url: "https://example.test/college",
    });
    const system = mapCollege({
      entity_id: "wikidata:Q4708506",
      kind: "nonprofit",
      name: "Example System",
      unitid: "102580",
      country_code: "US",
    });
    expect(college && system).toBeTruthy();
    const written = await writeOrganizationEntities(pool, [system!, college!]);
    expect(written.entities).toBe(2);
    expect(written.merges).toBe(1);
    expect(written.images).toBe(1);
    const logo = await pool.query<{ public: boolean; attribution: string; source_url: string }>(
      `select public, attribution, source_url from entity_image where entity_id = 'ipeds:442523' and role = 'logo'`,
    );
    expect(logo.rows[0]).toEqual({
      public: true,
      attribution: "Example College",
      source_url: "https://example.test/college",
    });
    const alias = await pool.query<{ scheme: string; kind: string }>(
      `select scheme, kind from entity_alias where entity_id = 'ipeds:442523' and alias = '442523'`,
    );
    expect(alias.rows[0]).toEqual({ scheme: "ipeds", kind: "external_id" });
    const merge = await pool.query<{ match_rule: string; into_id: string }>(
      `select match_rule, into_id from entity_merge where from_id = 'ipeds:442523'`,
    );
    expect(merge.rows[0]).toEqual({ match_rule: "ipeds_to_qid", into_id: "wikidata:Q4708506" });
    const still = await pool.query<{ n: string }>(`select count(*)::text n from entity where entity_id = 'ipeds:442523'`);
    expect(still.rows[0]?.n).toBe("1");
    await loadCompanyRows(pool, [
      {
        location_id: "airlines_world:hq:Q151581",
        entity_id: "wikidata:Q151581",
        role: "hq_in",
        name: "Example Air",
        country_code: "RU",
        boundary_set: "v2-2024",
        lat: "55.75",
        lon: "37.62",
      },
      {
        location_id: "telecoms_world:hq:Q999001",
        entity_id: "wikidata:Q999001",
        role: "hq_in",
        name: "Example Mobile",
        country_code: "US",
        boundary_set: "v2-2024",
        lat: "37.77",
        lon: "-122.42",
        geoid: "06075",
      },
    ]);
    const points = await pool.query<{ location_key: string; boundary_set: string | null; has_geom: boolean }>(
      `select location_key, boundary_set, geom is not null as has_geom
       from entity_location
       where location_key in ('airlines_world:hq:Q151581', 'telecoms_world:hq:Q999001')
       order by location_key`,
    );
    expect(points.rows).toEqual([
      { location_key: "airlines_world:hq:Q151581", boundary_set: null, has_geom: true },
      { location_key: "telecoms_world:hq:Q999001", boundary_set: "v2-2024", has_geom: true },
    ]);
  });

  it("counts the published organization files", () => {
    const colleges = parseCsv(show(ORG_REL.colleges));
    const ipeds = colleges.rows.filter((row) => (row.entity_id ?? "").startsWith("ipeds:")).length;
    expect(colleges.rows.length).toBe(COLLEGE_ROWS);
    expect(ipeds).toBe(COLLEGE_IPEDS_ROWS);
    expect(parseCsv(show(ORG_REL.airlines)).rows.length).toBe(AIRLINE_ROWS);
    expect(parseCsv(show(ORG_REL.airlineLocations)).rows.length).toBe(AIRLINE_HQ_ROWS);
    expect(parseCsv(show(ORG_REL.telecoms)).rows.length).toBe(TELECOM_ROWS);
    expect(parseCsv(show(ORG_REL.telecomLocations)).rows.length).toBe(TELECOM_HQ_ROWS);
  });
});
