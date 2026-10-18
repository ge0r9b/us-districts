import { afterAll, describe, expect, it } from "vitest";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { PMTiles, TileType } from "pmtiles";
import { createApp } from "../api/src/app.ts";
import { cachedCommit, needsRefresh, stampCommit } from "../ingest/branch-cache.ts";
import { buildClusterArchive, lonLatToTile } from "../ingest/cluster-tiles.ts";
import { companyEstimateBytes, loadCompanyRows } from "../ingest/companies.ts";
import { DISTRICT_FILES, ensureDataCache, loadAll, loadElectionFile, repoRoot } from "../ingest/load-all.ts";
import { applyInstImages, applyInstRelations, mapInstImage, wikidataId } from "../ingest/inst-entities.ts";
import { buildPrecinctArchive } from "../ingest/precinct-tiles.ts";
import { loadPrecinctState } from "../ingest/precinct-source.ts";
import { buildPrecinctState, locatePack, tilesPath } from "../ingest/precincts.ts";
import { formatRejectRules } from "../ingest/validate.ts";
import { ensureUnits, unitsFromGeoCsv } from "../ingest/units.ts";
import { parseCsv, readFileText } from "../ingest/csv.ts";
import { databaseUrl, createTestPool } from "./db.ts";

const pool = createTestPool();
const root = repoRoot();

afterAll(async () => {
  await pool.end();
});

describe("alpha.2 load and API", () => {
  it("refuses a neon.tech host", () => {
    const prev = process.env.DATABASE_URL;
    process.env.DATABASE_URL = "postgresql://user:secret@ep-example.aws.neon.tech/neondb";
    try {
      expect(() => databaseUrl()).toThrow(/Neon host/);
    } finally {
      process.env.DATABASE_URL = prev;
    }
  });

  it("keeps a precinct file out of the result table", async () => {
    const path = `${root}/v3/.cache/election/data-v3/results/2024/senate/precincts/CT.csv.gz`;
    const report = await loadElectionFile(pool, path, {
      fileName: "data-v3/results/2024/senate/precincts/CT.csv.gz",
    });
    expect(report.status).toBe("skipped");
    expect(report.rows).toBe(0);
    const facts = await pool.query<{ n: string }>(
      `select count(*)::text n from result r join unit u on u.id = r.unit_id where u.unit_type = 'precinct'`,
    );
    expect(facts.rows[0]?.n).toBe("0");
  });

  it("refreshes a data cache when the stamped commit differs", () => {
    const dir = mkdtempSync(join(tmpdir(), "usd-cache-"));
    writeFileSync(join(dir, "marker.csv"), "ok\n");
    expect(needsRefresh(dir, "abc", ["marker.csv"])).toBe(true);
    stampCommit(dir, "abc");
    expect(cachedCommit(dir)).toBe("abc");
    expect(needsRefresh(dir, "abc", ["marker.csv"])).toBe(false);
    expect(needsRefresh(dir, "def", ["marker.csv"])).toBe(true);
    expect(needsRefresh(dir, "abc", ["missing.csv"])).toBe(true);
  });

  it("loads the clean US House Senate files and records the election commit", async () => {
    const geo = unitsFromGeoCsv(readFileText(`${root}/v3/.cache/geo/data-v3/geo/senate.csv`).text);
    expect(geo.units.length).toBeGreaterThan(1000);
    await ensureUnits(pool, geo.units);
    const before = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    const again = await ensureUnits(pool, geo.units);
    const after = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    expect(again).toBe(0);
    expect(after.rows[0]?.dv).toBe(before.rows[0]?.dv);

    const cache = ensureDataCache(root);
    expect(cache.electionCommit).toMatch(/^[0-9a-f]{40}$/);
    expect(readFileSync(join(cache.election, ".commit"), "utf8").trim()).toBe(cache.electionCommit);
    expect(readFileSync(join(cache.geo, ".commit"), "utf8").trim()).toBe(cache.geoCommit);
    for (const rel of [
      "data-v3/results/2022/senate/us_senate_2022_ushouse.csv",
      "data-v3/results/2024/senate/us_senate_2024_ushouse.csv",
    ]) {
      expect(DISTRICT_FILES).toContain(rel);
      const parsed = parseCsv(readFileText(join(cache.election, rel)).text);
      expect(parsed.rows).toHaveLength(1023);
      expect(parsed.rows.some((row) => Number(row.votes) < 0)).toBe(false);
    }
    const rel = "data-v3/results/2024/senate/us_senate_2024_ushouse.csv";
    const first = await loadElectionFile(pool, join(cache.election, rel), {
      fileName: rel,
      gitCommit: cache.electionCommit,
    });
    expect(first.rejected).toBe(0);
    expect(["applied", "skipped"]).toContain(first.status);
    const stored = await pool.query<{ git_commit: string; status: string }>(
      `select git_commit, status from load_batch where file_name = $1 order by id desc limit 1`,
      [rel],
    );
    expect(stored.rows[0]).toMatchObject({ git_commit: cache.electionCommit, status: "applied" });
    const second = await loadElectionFile(pool, join(cache.election, rel), {
      fileName: rel,
      gitCommit: cache.electionCommit,
    });
    expect(second.status).toBe("skipped");
    expect(second.rejected).toBe(0);
  });

  it("labels every reject rule on its own", () => {
    const label = formatRejectRules(
      { R07_unit: 210, R03_votes: 114 },
      [{ lineNo: 88, detail: "-79" }],
    );
    expect(label).toContain("R03_votes 114");
    expect(label).toContain("R07_unit 210");
    expect(label.indexOf("R03_votes")).toBeLessThan(label.indexOf("R07_unit"));
    expect(label).toContain("line 88 votes=-79");
  });

  it("writes a parent relation onto entity.parent_id and keeps a prefixed wikidata id", async () => {
    expect(wikidataId("wikidata:Q228")).toBe("wikidata:Q228");
    expect(wikidataId("Q228")).toBe("wikidata:Q228");
    expect(mapInstImage({
      entity_id: "",
      role: "seal",
      file: "Great seal.svg",
      feed_id: "bia:cherokee-nation",
      license: "LicenseRef-PublicDomain",
      fair_use: "no",
      public: "yes",
      icon: "yes",
      attribution: "Cherokee Nation",
      wikidata_qid: "Q14708404",
      source_id: "repo-governments-e4797d09",
    })?.wikidata).toBe("wikidata:Q14708404");
    await pool.query(
      `insert into entity (entity_id, kind, name) values
         ('state:02', 'state', 'Alaska'),
         ('court:ak-supreme', 'court', 'Alaska Supreme Court')
       on conflict (entity_id) do nothing`,
    );
    const applied = await applyInstRelations(pool, [
      {
        entity_id: "court:ak-supreme",
        relation: "parent",
        related_entity_id: "state:02",
        source_id: "repo-bodies-test;other",
      },
      {
        entity_id: "state:02",
        relation: "consolidated_with",
        related_entity_id: "court:ak-supreme",
        source_id: "census-test",
      },
    ]);
    expect(applied.parents).toBe(1);
    const links = await pool.query<{ relation: string; parent_id: string; child_id: string }>(
      `select relation, parent_id, child_id from entity_relation
       where (child_id = 'court:ak-supreme' and relation = 'parent')
          or (parent_id = 'state:02' and child_id = 'court:ak-supreme' and relation = 'consolidated_with')
       order by relation`,
    );
    expect(links.rows).toEqual([
      { relation: "consolidated_with", parent_id: "state:02", child_id: "court:ak-supreme" },
      { relation: "parent", parent_id: "state:02", child_id: "court:ak-supreme" },
    ]);
    const parent = await pool.query<{ parent_id: string }>(
      `select parent_id from entity where entity_id = 'court:ak-supreme'`,
    );
    expect(parent.rows[0]?.parent_id).toBe("state:02");
    const untouched = await pool.query<{ parent_id: string | null }>(
      `select parent_id from entity where entity_id = 'state:02'`,
    );
    expect(untouched.rows[0]?.parent_id).toBeNull();
    const images = await applyInstImages(pool, [
      {
        entity_id: "state:02",
        role: "flag",
        file: "Flag of Alaska.svg",
        feed_id: "state:02",
        license: "LicenseRef-PublicDomain",
        fair_use: "no",
        public: "yes",
        icon: "yes",
        attribution: "State of Alaska",
        wikidata_qid: "wikidata:Q797",
        source_id: "wikidata_images",
      },
      {
        entity_id: "",
        role: "seal",
        file: "",
        feed_id: "bia:cherokee-nation",
        license: "fair-use",
        fair_use: "yes",
        public: "no",
        icon: "no",
        attribution: "Cherokee Nation",
        source_url: "https://example.test/cherokee-seal",
        wikidata_qid: "Q5330004",
        source_id: "repo-governments-e4797d09",
      },
    ]);
    expect(images.images).toBe(2);
    const icon = await pool.query<{ wikidata: string; icon: boolean; public: boolean }>(
      `select wikidata, icon, public from entity_image where entity_id = 'state:02' and role = 'flag'`,
    );
    expect(icon.rows[0]).toEqual({ wikidata: "wikidata:Q797", icon: true, public: true });
    const fair = await pool.query<{ feed_entity_id: string; public: boolean; wikidata: string }>(
      `select feed_entity_id, public, wikidata from entity_image where feed_entity_id = 'bia:cherokee-nation'`,
    );
    expect(fair.rows[0]).toEqual({
      feed_entity_id: "bia:cherokee-nation",
      public: false,
      wikidata: "wikidata:Q5330004",
    });
  });

  it("does not put precincts in Postgres", async () => {
    const summary = await loadAll(pool, root, { include: ["precincts"] });
    const gap = summary.gaps.find((line) => line.startsWith("precincts:"));
    expect(gap).toContain("npm run precincts");
    expect(gap).not.toContain("--allow-over-budget=precincts");
    expect(summary.results.some((row) => row.fileName.includes("/precincts/"))).toBe(false);
    expect(companyEstimateBytes()).toBe(212_439 * 520);
  });

  it("refuses governments even when the override is set", async () => {
    const before = await pool.query<{ n: string }>("select count(*)::text n from entity");
    const summary = await loadAll(pool, root, { include: ["governments"], allowOverBudget: ["governments"] });
    expect(summary.gaps.some((line) => line.includes("not reviewed") && line.includes("not inserted"))).toBe(true);
    const after = await pool.query<{ n: string }>("select count(*)::text n from entity");
    expect(after.rows[0]?.n).toBe(before.rows[0]?.n);
  });

  it("serves a company location by bbox and writes a clustered PMTiles archive", async () => {
    const loaded = await loadCompanyRows(pool, [
      {
        location_id: "walgreens:177",
        entity_id: "wikidata:Q1591889",
        role: "establishment_at",
        name: "Walgreens #177",
        lat: "18.40901",
        lon: "-67.153303",
        country_code: "PR",
        source_id: "walgreens-test",
        retrieved_at: "2026-10-12",
        brand_name: "Walgreens",
      },
      { location_id: "skip-me", entity_id: "not-a-qid", lat: "1", lon: "2" },
    ]);
    expect(loaded.locations).toBe(1);
    const sub = await loadCompanyRows(
      pool,
      [
        {
          location_id: "walgreens:duane",
          entity_id: "wikidata:Q1591889",
          sub_entity_id: "wikidata:Q5310380",
          role: "establishment_at",
          name: "Duane Reade #1",
          lat: "40.7",
          lon: "-74.0",
          country_code: "US",
          brand_name: "Walgreens",
        },
      ],
      new Map([["wikidata:Q5310380", { name: "Duane Reade", brand_name: "Duane Reade", kind: "brand" }]]),
    );
    expect(sub.relations).toBe(1);
    const linked = await pool.query<{ parent_id: string; child_id: string; name: string }>(
      `select r.parent_id, r.child_id, e.name
       from entity_relation r join entity e on e.entity_id = r.child_id
       where r.relation = 'brand_of' and r.child_id = 'wikidata:Q5310380'`,
    );
    expect(linked.rows[0]).toEqual({
      parent_id: "wikidata:Q1591889",
      child_id: "wikidata:Q5310380",
      name: "Duane Reade",
    });
    const row = await pool.query<{ country_code: string; source_record_id: string }>(
      `select btrim(country_code) country_code, source_record_id
       from entity_location where location_key = 'walgreens:177'`,
    );
    expect(row.rows[0]).toEqual({ country_code: "PR", source_record_id: "walgreens:177" });

    const app = createApp({ pool });
    const res = await app.request("http://127.0.0.1/api/v1/locations?bbox=-68,18,-67,19");
    expect(res.status).toBe(200);
    expect(res.headers.get("cache-control")).toContain("public");
    const body = (await res.json()) as { locations: { location_key: string; country_code: string }[] };
    expect(body.locations.map((item) => item.location_key)).toContain("walgreens:177");
    const clusters = await app.request("http://127.0.0.1/api/v1/locations/clusters?bbox=-68,18,-67,19&z=2");
    const clustered = (await clusters.json()) as { clusters: { n: number }[] };
    expect(clustered.clusters.reduce((sum, item) => sum + item.n, 0)).toBeGreaterThanOrEqual(1);
    const missing = await app.request("http://127.0.0.1/api/v1/locations");
    expect(missing.status).toBe(400);

    const bytes = buildClusterArchive([
      { lon: -67.15, lat: 18.41 },
      { lon: -67.16, lat: 18.42 },
    ]);
    const archive = new PMTiles({
      getKey: () => "mem",
      getBytes: async (offset: number, length: number) => {
        const slice = bytes.slice(offset, Math.min(bytes.length, offset + length));
        return { data: slice.buffer.slice(slice.byteOffset, slice.byteOffset + slice.byteLength) };
      },
    });
    const header = await archive.getHeader();
    expect(header.tileType).toBe(TileType.Mvt);
    expect(header.specVersion).toBe(3);
    expect(header.clustered).toBe(true);
    const tile = lonLatToTile(-67.15, 18.41, 4);
    const found = await archive.getZxy(4, tile.x, tile.y);
    expect(found?.data.byteLength ?? 0).toBeGreaterThan(0);
  });

  it("builds Vermont precinct packs, membership, and a PMTiles archive", async () => {
    const first = await buildPrecinctState(pool, root, "Vermont");
    expect(first.features).toBeGreaterThan(200);
    expect(first.gaps).toEqual([]);
    const dv = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    await buildPrecinctState(pool, root, "Vermont");
    const again = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    expect(again.rows[0]?.dv).toBe(dv.rows[0]?.dv);

    const facts = await pool.query<{ n: string }>(
      `select count(*)::text n from result r join unit u on u.id = r.unit_id where u.unit_type = 'precinct'`,
    );
    expect(facts.rows[0]?.n).toBe("0");
    const members = await pool.query<{ n: string }>(
      `select count(*)::text n
       from unit_crosswalk x
       join unit p on p.id = x.from_unit_id
       join unit c on c.id = x.to_unit_id
       where p.unit_type = 'precinct' and c.unit_type = 'county' and x.method = 'exact' and btrim(p.state_abbr) = 'VT'`,
    );
    expect(Number(members.rows[0]?.n)).toBe(first.features);
    const rollup = await pool.query<{ total: string }>(
      `select coalesce(sum(r.total_votes), 0)::text total
       from precinct_rollup r
       join unit u on u.id = r.parent_unit_id
       where r.contest_key = '2024|US|president|' and u.unit_type = 'county' and btrim(u.state_abbr) = 'VT'`,
    );
    const pack = locatePack(`${root}/v3/app/public/packs/precinct`, "VT", 2024, "president");
    expect(pack?.publicPath).toMatch(/\/packs\/precinct\/VT\/2024\/president\/[0-9a-f]{12}\.json$/);
    const body = JSON.parse(readFileSync(pack!.file, "utf8")) as { total: (number | null)[]; ids: string[]; names: string[] };
    const packTotal = body.total.reduce((sum: number, value) => sum + (value ?? 0), 0);
    expect(rollup.rows[0]?.total).toBe(String(packTotal));
    expect(body.names[body.ids.indexOf("VT:0")]).toBe("017-Chelsea");

    const app = createApp({ pool, packsDir: `${root}/v3/app/public/packs/precinct` });
    const res = await app.request("http://127.0.0.1/api/v1/results?contest=2024%7CUS%7Cpresident%7C&unit_type=precinct&state=VT");
    expect(res.status).toBe(200);
    const listed = (await res.json()) as { rows: { unit: string; name: string; votes: number[] }[] };
    const chelsea = listed.rows.find((row) => row.unit === "VT:0");
    expect(chelsea?.name).toBe("017-Chelsea");
    expect(chelsea?.votes?.[0]).toBe(372);
    const redirect = await app.request("http://127.0.0.1/api/v1/packs/precinct/VT/2024/president");
    expect(redirect.status).toBe(302);
    expect(redirect.headers.get("location")).toBe(pack!.publicPath);

    const bytes = readFileSync(tilesPath(root, "VT"));
    const archive = new PMTiles({
      getKey: () => "vt",
      getBytes: async (offset: number, length: number) => {
        const slice = bytes.subarray(offset, Math.min(bytes.length, offset + length));
        return { data: slice.buffer.slice(slice.byteOffset, slice.byteOffset + slice.byteLength) };
      },
    });
    const header = await archive.getHeader();
    expect(header.tileType).toBe(TileType.Mvt);
    expect(header.clustered).toBe(false);
    const vt = loadPrecinctState(root, "Vermont");
    const tile = lonLatToTile(vt.features[0]!.lon, vt.features[0]!.lat, 8);
    const found = await archive.getZxy(8, tile.x, tile.y);
    expect(found?.data.byteLength ?? 0).toBeGreaterThan(20);
    expect(buildPrecinctArchive(vt.features).length).toBeGreaterThan(1000);
  });
});
