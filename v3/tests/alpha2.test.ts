import { afterAll, describe, expect, it } from "vitest";
import { PMTiles, TileType } from "pmtiles";
import { createApp } from "../api/src/app.ts";
import { buildClusterArchive, lonLatToTile } from "../ingest/cluster-tiles.ts";
import { loadCompanyRows } from "../ingest/companies.ts";
import { loadAll, loadElectionFile, repoRoot } from "../ingest/load-all.ts";
import { ensureUnits, unitsFromGeoCsv } from "../ingest/units.ts";
import { readFileText } from "../ingest/csv.ts";
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

  it("loads one precinct file, records the line, and skips the same sha", async () => {
    const path = `${root}/v3/.cache/election/data-v3/results/2024/senate/precincts/CT.csv.gz`;
    const first = await loadElectionFile(pool, path, {
      fileName: "data-v3/results/2024/senate/precincts/CT.csv.gz",
      unitsFromRows: true,
    });
    expect(first.status).toBe("applied");
    const unit = await pool.query<{ n: string; source_record_id: string }>(
      `select count(*)::text n, min(u.source_record_id) source_record_id
       from unit u join boundary_set b on b.id = u.boundary_set_id
       where b.slug = 'v2-2024' and u.unit_type = 'precinct' and btrim(u.state_abbr) = 'CT'`,
    );
    expect(Number(unit.rows[0]?.n)).toBeGreaterThan(0);
    expect(unit.rows[0]?.source_record_id).toContain("CT|");
    const line = await pool.query<{ source_record_id: string }>(
      `select r.source_record_id
       from result r
       join unit u on u.id = r.unit_id
       where u.unit_type = 'precinct' and btrim(u.state_abbr) = 'CT'
       limit 1`,
    );
    expect(line.rows[0]?.source_record_id).toMatch(/^\d+$/);
    const second = await loadElectionFile(pool, path, {
      fileName: "data-v3/results/2024/senate/precincts/CT.csv.gz",
      unitsFromRows: true,
    });
    expect(second.status).toBe("skipped");
  });

  it("rejects the 2024 state-senate file and then skips that sha", async () => {
    const geo = unitsFromGeoCsv(readFileText(`${root}/v3/.cache/geo/data-v3/geo/senate.csv`).text);
    expect(geo.units.length).toBeGreaterThan(1000);
    await ensureUnits(pool, geo.units);
    const before = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    const again = await ensureUnits(pool, geo.units);
    const after = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    expect(again).toBe(0);
    expect(after.rows[0]?.dv).toBe(before.rows[0]?.dv);
    const path = `${root}/v3/.cache/election/data-v3/results/2024/senate/us_senate_2024_sldu.csv`;
    const first = await loadElectionFile(pool, path, { fileName: "data-v3/results/2024/senate/us_senate_2024_sldu.csv" });
    expect(first.status).toBe("rejected");
    const rules = await pool.query<{ n: string }>(
      `select count(*)::text n from stg_reject s
       join load_batch b on b.id = s.load_batch_id
       where b.file_name = 'data-v3/results/2024/senate/us_senate_2024_sldu.csv' and s.rule = 'R03_votes'`,
    );
    expect(Number(rules.rows[0]?.n)).toBeGreaterThan(0);
    const facts = await pool.query<{ n: string }>(
      `select count(*)::text n from result r
       join unit u on u.id = r.unit_id
       where u.unit_type = 'sldu'`,
    );
    expect(facts.rows[0]?.n).toBe("0");
    const second = await loadElectionFile(pool, path, { fileName: "data-v3/results/2024/senate/us_senate_2024_sldu.csv" });
    expect(second.status).toBe("skipped");
  });

  it("does not load precincts that would pass 350 MB unless the flag is set", async () => {
    const summary = await loadAll(pool, root, { include: ["precincts"] });
    const gap = summary.gaps.find((line) => line.startsWith("precincts:"));
    expect(gap).toContain("--allow-over-budget=precincts");
    expect(summary.results.some((row) => row.fileName.includes("/precincts/"))).toBe(false);
  });

  it("refuses institutions even when the override is set", async () => {
    const summary = await loadAll(pool, root, { include: ["institutions"], allowOverBudget: ["institutions"] });
    expect(summary.gaps.some((line) => line.includes("not reviewed") && line.includes("not inserted"))).toBe(true);
    const entities = await pool.query<{ n: string }>("select count(*)::text n from entity");
    expect(entities.rows[0]?.n).toBe("0");
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
});
