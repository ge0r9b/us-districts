import { afterAll, describe, expect, it } from "vitest";
import { applyResults, markSuperseded } from "../ingest/apply.ts";
import { mapInstImage, mapRelationMethod, loadInstitutionTables } from "../ingest/inst-entities.ts";
import { assignLocationUnits } from "../ingest/locations.ts";
import { repoRoot } from "../ingest/load-all.ts";
import { dryRunPrecincts } from "../ingest/precincts.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();
const root = repoRoot();

afterAll(async () => {
  await pool.end();
});

describe("neon follow-up", () => {
  it("assigns US locations to county, state, and ushouse, and flags points outside every unit", async () => {
    await pool.query(
      `insert into entity (entity_id, kind, name, origin)
       values ('wikidata:Q1591889', 'brand', 'Walgreens', 'companies_bot')
       on conflict (entity_id) do nothing`,
    );
    await pool.query(
      `insert into entity_location (location_key, entity_id, role, geom, country_code)
       select 'pip:inside', 'wikidata:Q1591889', 'establishment_at', st_pointonsurface(g.geom), 'US'
       from unit_geom g
       join unit u on u.id = g.unit_id
       join boundary_set b on b.id = u.boundary_set_id
       where b.slug = 'v2-2024' and u.unit_type = 'county' and g.lod = 0
       limit 1
       on conflict (location_key) do nothing`,
    );
    await pool.query(
      `insert into entity_location (location_key, entity_id, role, geom, country_code)
       values
         ('pip:outside', 'wikidata:Q1591889', 'establishment_at', st_setsrid(st_makepoint(0, 0), 4326), 'US'),
         ('pip:pr', 'wikidata:Q1591889', 'establishment_at', st_setsrid(st_makepoint(-66.5, 18.2), 4326), 'PR')
       on conflict (location_key) do nothing`,
    );
    const first = await assignLocationUnits(pool);
    expect(first.outside).toBeGreaterThanOrEqual(1);
    const dv = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    const second = await assignLocationUnits(pool);
    const again = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    expect(second.changed).toBe(0);
    expect(again.rows[0]?.dv).toBe(dv.rows[0]?.dv);

    const inside = await pool.query<{ unit_type: string; n: string; county_matches: boolean }>(
      `select elu.unit_type, count(*)::text n,
              bool_or(elu.unit_type = 'county' and elu.unit_id = l.unit_id) county_matches
       from entity_location l
       join entity_location_unit elu on elu.location_id = l.location_id
       where l.location_key = 'pip:inside'
       group by elu.unit_type
       order by elu.unit_type`,
    );
    expect(inside.rows.map((row) => row.unit_type)).toEqual(["county", "state", "ushouse"]);
    expect(inside.rows.every((row) => row.n === "1")).toBe(true);
    expect(inside.rows.find((row) => row.unit_type === "county")?.county_matches).toBe(true);

    const outside = await pool.query<{ unit_id: string | null; flags: string[] | null }>(
      `select unit_id::text, flags from entity_location where location_key = 'pip:outside'`,
    );
    expect(outside.rows[0]?.unit_id).toBeNull();
    expect(outside.rows[0]?.flags).toEqual(["no_unit_resolved"]);

    const pr = await pool.query<{ unit_id: string | null; flags: string[] | null; links: string }>(
      `select l.unit_id::text, l.flags, count(elu.location_id)::text links
       from entity_location l
       left join entity_location_unit elu on elu.location_id = l.location_id
       where l.location_key = 'pip:pr'
       group by l.unit_id, l.flags`,
    );
    expect(pr.rows[0]?.unit_id).toBeNull();
    expect(pr.rows[0]?.flags ?? []).not.toContain("no_unit_resolved");
    expect(pr.rows[0]?.links).toBe("0");
  });

  it("prices a precinct dry run without writing units, crosswalk, rollup, or result facts", async () => {
    const before = await pool.query<{ units: string; links: string; facts: string }>(
      `select
         (select count(*) from unit where unit_type = 'precinct')::text units,
         (select count(*) from unit_crosswalk)::text links,
         (select count(*) from result r join unit u on u.id = r.unit_id where u.unit_type = 'precinct')::text facts`,
    );
    const estimate = await dryRunPrecincts(pool, root, { state: "Vermont" });
    const after = await pool.query<{ units: string; links: string; facts: string }>(
      `select
         (select count(*) from unit where unit_type = 'precinct')::text units,
         (select count(*) from unit_crosswalk)::text links,
         (select count(*) from result r join unit u on u.id = r.unit_id where u.unit_type = 'precinct')::text facts`,
    );
    expect(after.rows[0]).toEqual(before.rows[0]);
    expect(estimate.states).toBe(1);
    expect(estimate.units).toBeGreaterThan(200);
    expect(estimate.crosswalk).toBe(estimate.units * 2);
    expect(estimate.rollup).toBeGreaterThan(0);
    expect(estimate.databaseBytes).toBeGreaterThan(0);
    expect(estimate.note).toContain("Precinct result facts stay out of Postgres");
    expect(estimate.parts.find((part) => part.table === "unit")?.bytes).not.toBeNull();
  });

  it("loads institution entities, relations, image metadata, and bodies", async () => {
    expect(mapInstImage({
      entity_id: "state:48",
      role: "flag",
      public: "yes",
      license: "LicenseRef-PublicDomain",
      fair_use: "no",
    })).toBeNull();
    expect(mapRelationMethod("tceq_wdd_primary_county")).toEqual({ method: "sourced", token: "tceq_wdd_primary_county" });
    expect(mapRelationMethod("")).toEqual({ method: null, token: null });

    const loaded = await loadInstitutionTables(pool, {
      entities: [
        row("state:48", { kind: "state", name: "Texas", state_fips: "48", state: "Texas" }),
        row("county:48001", { kind: "county", name: "Anderson County", state_fips: "48", parent_id: "state:48" }),
        row("special_district:tx-tceq-101265", {
          kind: "special_district",
          name: "Example WCID",
          state_fips: "48",
          parent_id: "state:48",
        }),
      ],
      relations: [
        {
          entity_id: "special_district:tx-tceq-101265",
          relation: "in_county",
          related_entity_id: "county:48001",
          method: "tceq_wdd_primary_county",
          source_id: "tceq-test",
        },
        {
          entity_id: "special_district:tx-tceq-101265",
          relation: "parent",
          related_entity_id: "state:48",
          method: "",
          source_id: "tceq-test",
        },
      ],
      images: [
        {
          entity_id: "state:48",
          role: "flag",
          file: "Flag of Texas.svg",
          license: "LicenseRef-PublicDomain",
          fair_use: "no",
          public: "yes",
          icon: "yes",
          attribution: "State of Texas",
          source_id: "wikidata_images",
        },
        {
          entity_id: "state:48",
          role: "seal",
          public: "yes",
          license: "LicenseRef-PublicDomain",
          fair_use: "no",
        },
      ],
      bodies: [
        { body_key: "us-tx-house", entity_id: "state:48", role: "chamber", source_record_id: "us-tx-house" },
      ],
      files: [{ fileName: "fixture-inst.csv", sha256: "fixture-inst-sha", rows: 3 }],
      fileBytes: 120,
      gitCommit: "4215fab",
    });
    expect(loaded.entities).toBe(3);
    expect(loaded.images).toBe(1);
    expect(loaded.imagesSkipped).toBe(1);
    expect(loaded.bodies).toBe(1);

    const parent = await pool.query<{ parent_id: string }>(
      `select parent_id from entity where entity_id = 'special_district:tx-tceq-101265'`,
    );
    expect(parent.rows[0]?.parent_id).toBe("state:48");
    const link = await pool.query<{ parent_id: string; child_id: string; method: string; source_record_id: string }>(
      `select parent_id, child_id, method, source_record_id
       from entity_relation
       where relation = 'in_county' and child_id = 'special_district:tx-tceq-101265'`,
    );
    expect(link.rows[0]).toMatchObject({
      parent_id: "county:48001",
      child_id: "special_district:tx-tceq-101265",
      method: "sourced",
    });
    expect(link.rows[0]?.source_record_id).toContain("method:tceq_wdd_primary_county");
    const image = await pool.query<{ public: boolean; icon: boolean; served_path: string | null }>(
      `select public, icon, served_path from entity_image where entity_id = 'state:48' and role = 'flag'`,
    );
    expect(image.rows[0]).toEqual({ public: true, icon: true, served_path: null });
    const body = await pool.query<{ entity_id: string; role: string }>(
      `select entity_id, role from body_entity where body_key = 'us-tx-house'`,
    );
    expect(body.rows[0]).toEqual({ entity_id: "state:48", role: "chamber" });
  });

  it("marks an older rejected batch superseded when a later batch for that file applies", async () => {
    await pool.query(
      `insert into load_batch (file_name, file_sha256, status)
       values ('supersede-test.csv', 'sha-old-rejected', 'rejected'),
              ('other-file.csv', 'sha-other-rejected', 'rejected')`,
    );
    const report = await applyResults(
      pool,
      { fileName: "supersede-test.csv", sha256: "sha-new-applied", gitCommit: "abc" },
      [
        {
          lineNo: 2,
          state: "AL",
          year: "2099",
          office: "probe_office",
          district: "statewide",
          unitId: "01",
          unitType: "state",
          candidateId: "supersede-probe",
          answer: "Probe",
          party: "green",
          votes: "1",
          weight: "",
          sourceUrl: "https://example.test/supersede",
          retrievedAt: "2024-01-01T00:00:00Z",
          method: "official",
          boundarySet: "v2-2024",
        },
      ],
    );
    expect(report.status).toBe("applied");
    const rows = await pool.query<{ file_sha256: string; status: string }>(
      `select file_sha256, status from load_batch
       where file_sha256 in ('sha-old-rejected', 'sha-other-rejected', 'sha-new-applied')
       order by file_sha256`,
    );
    expect(rows.rows).toEqual([
      { file_sha256: "sha-new-applied", status: "applied" },
      { file_sha256: "sha-old-rejected", status: "superseded" },
      { file_sha256: "sha-other-rejected", status: "rejected" },
    ]);
    await pool.query(
      `insert into load_batch (file_name, file_sha256, status)
       values ('supersede-test.csv', 'sha-still-rejected', 'rejected')`,
    );
    const skipped = await applyResults(
      pool,
      { fileName: "supersede-test.csv", sha256: "sha-new-applied" },
      [],
    );
    expect(skipped.status).toBe("skipped");
    const still = await pool.query<{ status: string }>(
      `select status from load_batch where file_sha256 = 'sha-still-rejected'`,
    );
    expect(still.rows[0]?.status).toBe("rejected");
    const applied = await pool.query<{ id: string }>(
      `select id::text from load_batch where file_sha256 = 'sha-new-applied'`,
    );
    expect(await markSuperseded(pool, "supersede-test.csv", applied.rows[0]!.id)).toBe(1);
    const after = await pool.query<{ status: string }>(
      `select status from load_batch where file_sha256 = 'sha-still-rejected'`,
    );
    expect(after.rows[0]?.status).toBe("superseded");
  });
});

function row(entityId: string, extra: Record<string, string>): Record<string, string> {
  return {
    entity_id: entityId,
    kind: "state",
    state_fips: "",
    state: "",
    name: entityId,
    alias: "",
    label: "",
    gov_status: "",
    parent_id: "",
    valid_from: "",
    valid_to: "",
    predecessor_id: "",
    successor_id: "",
    v2_layer: "",
    v2_row: "",
    v2_key: "",
    source_id: "",
    feed: "",
    level: "",
    type: "",
    cog_pid6: "",
    flags: "",
    source_record_id: entityId,
    wikidata: "",
    iso_3166_2: "",
    constituent_qid: "",
    inception: "",
    inception_precision: "",
    inception_source: "",
    ...extra,
  };
}
