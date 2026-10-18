import { afterAll, describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createApp } from "../api/src/app.ts";
import { nodePacks } from "../api/src/node-packs.ts";
import { applyResults, markSuperseded, sha256Hex } from "../ingest/apply.ts";
import { originCommit } from "../ingest/branch-cache.ts";
import { BUDGET_BYTES } from "../ingest/budget.ts";
import { instPacksRoot, readInstPack } from "../ingest/inst-pack.ts";
import { historyDate, mapInstImage, mapRelationMethod, loadInstitutionTables, loadInstitutions } from "../ingest/inst-entities.ts";
import { assignLocationUnits, isConnectionDrop } from "../ingest/locations.ts";
import { repoRoot } from "../ingest/load-all.ts";
import { dryRunPrecincts } from "../ingest/precincts.ts";
import { catalogRowBytes } from "../ingest/row-width.ts";
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
      `insert into entity_location (location_key, entity_nid, role, geom, country_code)
       select 'pip:inside', e.nid, 'establishment_at', st_pointonsurface(g.geom), 'US'
       from unit_geom g
       join unit u on u.id = g.unit_id
       join boundary_set b on b.id = u.boundary_set_id
       join entity e on e.entity_id = 'wikidata:Q1591889'
       where b.slug = 'v2-2024' and u.unit_type = 'county' and g.lod = 0
       limit 1
       on conflict (location_key) do nothing`,
    );
    await pool.query(
      `insert into entity_location (location_key, entity_nid, role, geom, country_code)
       select x.key, e.nid, 'establishment_at', x.geom, x.country_code
       from (values
         ('pip:outside', st_setsrid(st_makepoint(0, 0), 4326), 'US'),
         ('pip:pr', st_setsrid(st_makepoint(-66.5, 18.2), 4326), 'PR')
       ) as x(key, geom, country_code)
       join entity e on e.entity_id = 'wikidata:Q1591889'
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
    expect(estimate.note).toContain("PMTiles");
    expect(estimate.note).toContain("unit_crosswalk");
    expect(estimate.parts.find((part) => part.table === "unit")?.bytes).toBe(0);
    expect(estimate.parts.find((part) => part.table === "unit_crosswalk")?.bytes).toBe(0);
    const rollup = estimate.parts.find((part) => part.table === "precinct_rollup");
    expect(rollup?.bytes).toBeGreaterThan(0);
    expect(estimate.estimatedBytes).toBe(rollup?.bytes);
    const width = await catalogRowBytes(pool, "usd.precinct_rollup", {
      textBytes: { contest_key: 28 },
      indexBytes: 48,
    });
    expect(width).toBeGreaterThan(24);
    expect(width).toBeLessThan(400);
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

    const packsDir = instPacksRoot(root);
    const loaded = await loadInstitutionTables(pool, {
      entities: [
        row("state:48", { kind: "state", name: "Texas", state_fips: "48", state: "Texas" }),
        row("county:48001", {
          kind: "county",
          name: "Anderson County",
          state_fips: "48",
          state: "Texas",
          parent_id: "state:48",
          v2_key: "Texas|Anderson County",
          v2_layer: "v2:counties",
          alias: "Anderson",
        }),
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
          source_url: "https://commons.wikimedia.org/wiki/File:Flag_of_Texas.svg",
          commons_url: "https://commons.wikimedia.org/wiki/File:Flag_of_Texas.svg",
          licence_url: "https://creativecommons.org/publicdomain/zero/1.0/",
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
    }, { packsDir });
    expect(loaded.entities).toBe(3);
    expect(loaded.images).toBe(1);
    expect(loaded.imagesSkipped).toBe(1);
    expect(loaded.bodies).toBe(1);

    const parent = await pool.query<{ parent_id: string }>(
      `select parent_id from entity where entity_id = 'special_district:tx-tceq-101265'`,
    );
    expect(parent.rows[0]?.parent_id).toBe("state:48");
    const link = await pool.query<{ parent_id: string; child_id: string; method: string; source_record_id: string }>(
      `select p.entity_id parent_id, c.entity_id child_id, r.method, r.source_record_id
       from entity_relation r
       join entity p on p.nid = r.parent_nid
       join entity c on c.nid = r.child_nid
       where r.relation = 'in_county' and c.entity_id = 'special_district:tx-tceq-101265'`,
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
    const hot = await pool.query<{ attribution: string | null; file_url: string | null; state: string | null; v2_key: string[] | null }>(
      `select i.attribution, i.file_url, e.state, e.v2_key
       from entity_image i
       join entity e on e.entity_id = i.entity_id
       where i.entity_id = 'state:48' and i.role = 'flag'`,
    );
    expect(hot.rows[0]?.attribution).toBeNull();
    expect(hot.rows[0]?.file_url).toBeNull();
    expect(hot.rows[0]?.state).toBeNull();
    expect(hot.rows[0]?.v2_key).toBeNull();
    const stored = readInstPack(packsDir);
    expect(stored?.images["state:48||flag"]).toMatchObject({
      attribution: "State of Texas",
      source_url: "https://commons.wikimedia.org/wiki/File:Flag_of_Texas.svg",
      sources: ["wikidata_images"],
    });
    expect(stored?.extra["county:48001"]?.v2_key).toEqual(["Texas|Anderson County"]);
    const side = await pool.query<{ extras: string; texts: string; sources: string }>(
      `select
         (select count(*) from entity_extra)::text extras,
         (select count(*) from entity_image_text)::text texts,
         (select count(*) from entity_image_source)::text sources`,
    );
    expect(side.rows[0]).toEqual({ extras: "0", texts: "0", sources: "0" });
    const deed = await pool.query<{ url: string }>(
      `select url from license where code = 'LicenseRef-PublicDomain'`,
    );
    expect(deed.rows[0]?.url).toBe("https://creativecommons.org/publicdomain/zero/1.0/");
    const nid = await pool.query<{ nid: string }>(
      `select nid::text from entity where entity_id = 'county:48001'`,
    );
    expect(Number(nid.rows[0]?.nid)).toBeGreaterThan(0);
    const app = createApp({ sql: pool, packs: nodePacks(undefined, packsDir) });
    const redirect = await app.request("http://127.0.0.1/api/v1/packs/institutions");
    expect(redirect.status).toBe(302);
    expect(redirect.headers.get("location")).toMatch(/^\/packs\/inst\/[0-9a-f]{12}\.json$/);
    const alias = await pool.query<{ alias: string }>(
      `select alias from entity_alias where entity_id = 'county:48001'`,
    );
    expect(alias.rows[0]?.alias).toBe("Anderson");
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

  it("prices institutions from origin/data/inst-entities and writes nothing on a dry run", async () => {
    expect(isConnectionDrop(new Error("Connection terminated unexpectedly"))).toBe(true);
    expect(isConnectionDrop(new Error("syntax error"))).toBe(false);
    const before = await pool.query<{ n: string }>("select count(*)::text n from entity");
    const report = await loadInstitutions(pool, {
      root,
      currentBytes: 236 * 1024 * 1024,
      allow: false,
      dryRun: true,
    });
    const after = await pool.query<{ n: string }>("select count(*)::text n from entity");
    expect(after.rows[0]?.n).toBe(before.rows[0]?.n);
    expect(report.status).toBe("dry-run");
    expect(report.gitCommit).toBe(originCommit(root, "data/inst-entities"));
    expect(report.gitCommit).toMatch(/^[0-9a-f]{40}$/);
    expect(report.entities).toBeGreaterThan(50_000);
    expect(report.estimate.projectedBytes).not.toBeNull();
    const margin = (report.estimate.projectedBytes ?? 0) - 236 * 1024 * 1024;
    expect(margin).toBeGreaterThan(5 * 1024 * 1024);
    expect(margin).toBeLessThan(114 * 1024 * 1024);
    expect(report.estimate.projectedBytes!).toBeLessThan(350 * 1024 * 1024);
  });

  it("allows an institution reload whose projected net change is zero or negative", async () => {
    const live = 377_389_056;
    const growing = await loadInstitutions(pool, {
      root,
      currentBytes: BUDGET_BYTES - 1024 * 1024,
      allow: false,
      dryRun: true,
    });
    expect(growing.status).toBe("dry-run");
    expect(growing.gap).toMatch(/net/);
    expect(growing.estimate.projectedBytes!).toBeGreaterThan(BUDGET_BYTES);

    const files = [
      "data-v3/inst/entities.csv",
      "data-v3/inst/entity_relations.csv",
      "data-v3/inst/entity_images.csv",
      "data-v3/inst/body_entity.csv",
    ];
    const dir = join(root, "v3/.cache/inst-entities");
    const shas = files.map((rel) => ({
      file_name: rel,
      sha256: sha256Hex(readFileSync(join(dir, rel))),
    }));
    await pool.query(
      `insert into load_batch (file_name, file_sha256, status)
       select file_name, sha256, 'applied'
       from jsonb_to_recordset($1::jsonb) as x(file_name text, sha256 text)
       on conflict (file_sha256) do update set status = 'applied'`,
      [JSON.stringify(shas)],
    );
    try {
      const reload = await loadInstitutions(pool, {
        root,
        currentBytes: live,
        allow: false,
        dryRun: true,
      });
      expect(reload.status).toBe("dry-run");
      expect(reload.gap).toBeNull();
      expect(reload.estimate.projectedBytes).not.toBeNull();
      expect(reload.estimate.projectedBytes!).toBeLessThanOrEqual(live);
    } finally {
      await pool.query("delete from load_batch where file_sha256 = any($1::text[])", [
        shas.map((file) => file.sha256),
      ]);
    }
  });

  it("supersedes a rejected batch in the migration when a later applied batch exists", async () => {
    await pool.query(
      `insert into load_batch (file_name, file_sha256, status)
       values ('us_senate_2024_sldu.csv', 'sha-stale-rejected', 'rejected'),
              ('us_senate_2024_sldu.csv', 'sha-stale-applied', 'applied'),
              ('never-applied.csv', 'sha-stale-lonely', 'rejected')
       on conflict (file_sha256) do nothing`,
    );
    const sql = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../db/migrations/013_slim_load.sql"), "utf8");
    await pool.query(sql);
    const rows = await pool.query<{ file_sha256: string; status: string }>(
      `select file_sha256, status from load_batch
       where file_sha256 in ('sha-stale-rejected', 'sha-stale-applied', 'sha-stale-lonely')
       order by file_sha256`,
    );
    expect(rows.rows).toEqual([
      { file_sha256: "sha-stale-applied", status: "applied" },
      { file_sha256: "sha-stale-lonely", status: "rejected" },
      { file_sha256: "sha-stale-rejected", status: "superseded" },
    ]);
  });

  it("clears institution dates before 2016 and marks a missing feed row without reusing its id", async () => {
    expect(historyDate("")).toBeNull();
    expect(historyDate("2014")).toBeNull();
    expect(historyDate("2015-12-31")).toBeNull();
    expect(historyDate("2016-01-01")).toBe("2016-01-01");
    const absentId = "county:feed-absent-demo";
    await pool.query(
      `insert into entity (entity_id, kind, name, origin, feed)
       values ($1, 'county', 'Old County', 'inst', 'governments-bot')
       on conflict (entity_id) do update set origin = 'inst', feed = 'governments-bot', flags = null`,
      [absentId],
    );
    const before = await pool.query<{ nid: string }>(`select nid::text from entity where entity_id = $1`, [absentId]);
    const packsDir = instPacksRoot(root);
    const input = {
      relations: [],
      images: [],
      bodies: [],
      fileBytes: 40,
      gitCommit: "history",
    };
    await loadInstitutionTables(pool, {
      ...input,
      entities: [
        row("county:feed-present-demo", {
          kind: "county",
          name: "Present County",
          feed: "governments-bot",
          valid_from: "",
          inception: "2014",
        }),
        row("county:feed-cut-demo", {
          kind: "county",
          name: "Cut County",
          feed: "governments-bot",
          valid_from: "2015-06-01",
          inception: "2016-06-15",
        }),
      ],
      files: [{ fileName: "fixture-history.csv", sha256: "fixture-history-sha", rows: 2 }],
    }, { packsDir });
    const absent = await pool.query<{ nid: string; flags: string[] | null }>(
      `select nid::text, flags from entity where entity_id = $1`,
      [absentId],
    );
    expect(absent.rows[0]?.nid).toBe(before.rows[0]?.nid);
    expect(absent.rows[0]?.flags).toContain("feed_absent");
    const present = await pool.query<{ valid_from: string | null; inception: string | null; flags: string[] | null }>(
      `select valid_from::text, inception::text, flags from entity where entity_id = 'county:feed-present-demo'`,
    );
    expect(present.rows[0]?.valid_from).toBeNull();
    expect(present.rows[0]?.inception).toBeNull();
    expect(present.rows[0]?.flags ?? []).not.toContain("feed_absent");
    const cut = await pool.query<{ valid_from: string | null; inception: string | null }>(
      `select valid_from::text, inception::text from entity where entity_id = 'county:feed-cut-demo'`,
    );
    expect(cut.rows[0]).toEqual({ valid_from: null, inception: "2016-06-15" });
    await loadInstitutionTables(pool, {
      ...input,
      entities: [
        row(absentId, { kind: "county", name: "Old County", feed: "governments-bot", valid_from: "", inception: "" }),
        row("county:feed-present-demo", { kind: "county", name: "Present County", feed: "governments-bot" }),
        row("county:feed-cut-demo", { kind: "county", name: "Cut County", feed: "governments-bot" }),
      ],
      files: [{ fileName: "fixture-history.csv", sha256: "fixture-history-sha-2", rows: 3 }],
    }, { packsDir });
    const restored = await pool.query<{ nid: string; flags: string[] | null }>(
      `select nid::text, flags from entity where entity_id = $1`,
      [absentId],
    );
    expect(restored.rows[0]?.nid).toBe(before.rows[0]?.nid);
    expect(restored.rows[0]?.flags ?? []).not.toContain("feed_absent");
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
