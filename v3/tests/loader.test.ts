import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, describe, expect, it } from "vitest";
import { parseCsv } from "../ingest/csv.ts";
import { loadAll } from "../ingest/load-all.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();
const root = fileURLToPath(new URL("../..", import.meta.url));

afterAll(async () => {
  await pool.end();
});

function csvCount(rel: string, pred?: (row: Record<string, string>) => boolean): number {
  const text = readFileSync(join(root, "v3/.cache/election", rel), "utf8");
  const rows = parseCsv(text).rows;
  return pred ? rows.filter(pred).length : rows.length;
}

describe("loaders", () => {
  it("loads v2-2024 states, counties, and congressional districts", async () => {
    const r = await pool.query<{ unit_type: string; n: string }>(
      `select u.unit_type, count(*)::text n
       from unit u join boundary_set b on b.id = u.boundary_set_id
       where b.slug = 'v2-2024'
       group by u.unit_type`,
    );
    const n = (t: string) => Number(r.rows.find((row) => row.unit_type === t)?.n ?? 0);
    expect(n("state")).toBe(51);
    expect(n("county")).toBe(3144);
    expect(n("ushouse")).toBe(436);
    const geoms = await pool.query<{ n: string }>(
      `select count(*)::text n from unit_geom g
       join unit u on u.id = g.unit_id
       where g.lod = 0 and u.unit_type = 'state'`,
    );
    expect(Number(geoms.rows[0]?.n)).toBeGreaterThanOrEqual(50);
  });

  it("loads every 2016 FEC state row and the Pennsylvania county files", async () => {
    const fec = csvCount("data-v3/results/2016/us_president_2016_state_fec.csv");
    const loaded = await pool.query<{ n: string }>(
      `select count(*)::text n
       from result r
       join contest c on c.id = r.contest_id
       join unit u on u.id = r.unit_id
       where c.contest_key = '2016|US|president|' and u.unit_type = 'state' and r.method = 'official'`,
    );
    expect(Number(loaded.rows[0]?.n)).toBe(fec);

    for (const [file, year] of [
      ["data-v3/results/PA/pa_president_county_official.csv", "2020"],
      ["data-v3/results/PA/pa_president_county_official.csv", "2024"],
    ] as const) {
      const expected = csvCount(file, (row) => row.year === year);
      const got = await pool.query<{ n: string }>(
        `select count(*)::text n
         from result r
         join contest c on c.id = r.contest_id
         join unit u on u.id = r.unit_id
         where c.contest_key = $1 and u.unit_type = 'county' and btrim(u.state_abbr) = 'PA' and r.method = 'official'`,
        [`${year}|US|president|`],
      );
      expect(Number(got.rows[0]?.n)).toBe(expected);
    }
  });

  it("keeps Alabama 2024 counties on the v2 import", async () => {
    const r = await pool.query<{ n: string; method: string }>(
      `select count(*)::text n, min(r.method) method
       from result r
       join contest c on c.id = r.contest_id
       join unit u on u.id = r.unit_id
       where c.contest_key = '2024|US|president|' and u.unit_key = '01001'`,
    );
    expect(Number(r.rows[0]?.n)).toBe(3);
    expect(r.rows[0]?.method).toBe("v2_import");
  });

  it("matches the Arizona 2024 Senate state file", async () => {
    const expected = csvCount(
      "data-v3/results/2024/senate/us_senate_2024_state.csv",
      (row) => row.state === "AZ" && row.office === "us_senate" && row.unit_type === "state",
    );
    const got = await pool.query<{ n: string }>(
      `select count(*)::text n
       from result r
       join contest c on c.id = r.contest_id
       join unit u on u.id = r.unit_id
       where c.contest_key = '2024|AZ|us_senate|' and u.unit_type = 'state'`,
    );
    expect(Number(got.rows[0]?.n)).toBe(expected);
  });

  it("assigns the v2 d/r slots from statewide totals", async () => {
    const slots = await pool.query<{ contest_key: string; slot: string; answer_key: string; rule: string }>(
      `select c.contest_key, s.slot, a.answer_key, s.rule
       from contest_display_slot s
       join contest c on c.id = s.contest_id
       join answer a on a.id = s.answer_id
       where c.contest_key = any($1::text[])`,
      [[
        "2024|ME|us_senate|",
        "2024|VT|us_senate|",
        "2024|NE|us_senate|",
        "2022|AK|us_senate|",
        "2022|UT|us_senate|",
        "2022|LA|us_senate|",
        "2022|ND|us_senate|",
      ]],
    );
    const pick = (key: string, slot: string) => slots.rows.find((row) => row.contest_key === key && row.slot === slot);
    expect(pick("2024|ME|us_senate|", "d")).toMatchObject({
      answer_key: "cand:king-angus-s-jr",
      rule: "independent_beat_dem",
    });
    expect(pick("2024|VT|us_senate|", "d")).toMatchObject({ answer_key: "cand:sanders-bernard", rule: "no_dem" });
    expect(pick("2024|NE|us_senate|", "d")).toMatchObject({ answer_key: "cand:osborn-dan", rule: "no_dem" });
    expect(pick("2022|AK|us_senate|", "r")).toMatchObject({ answer_key: "cand:murkowski-lisa", rule: "rep_nominee" });
    expect(pick("2022|UT|us_senate|", "d")).toMatchObject({ answer_key: "cand:mcmullin-evan", rule: "no_dem" });
    expect(pick("2022|LA|us_senate|", "d")).toMatchObject({ answer_key: "cand:chambers-gary-jr", rule: "dem_nominee" });
    expect(pick("2022|ND|us_senate|", "d")).toMatchObject({ answer_key: "dem_nominee", rule: "dem_nominee" });
  });

  it("does not bump the data version when the same files load again", async () => {
    const before = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    const summary = await loadAll(pool, root);
    const after = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
    expect(summary.boundaries.status).toBe("skipped");
    expect(summary.results.every((row) => row.status === "skipped")).toBe(true);
    expect(after.rows[0]?.dv).toBe(before.rows[0]?.dv);
  });
});
