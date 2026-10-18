import { afterAll, describe, expect, it } from "vitest";
import { createApp } from "../api/src/app.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();
const app = createApp({ pool, fetchImpl: fetch, sleep: async () => {} });

afterAll(async () => {
  await pool.end();
});

async function get(path: string, init?: RequestInit) {
  return app.request(`http://127.0.0.1${path}`, init);
}

describe("/api/v1", () => {
  it("serves a versioned manifest and pins cache headers", async () => {
    const res = await get("/api/v1/manifest");
    expect(res.status).toBe(200);
    expect(res.headers.get("cache-control")).toContain("max-age=60");
    const body = (await res.json()) as { dv: number; tiles: Record<string, string> };
    expect(body.dv).toBeGreaterThanOrEqual(1);
    expect(body.tiles["state-2024"]).toContain(".pmtiles");

    const pinned = await get(`/api/v1/contests?year=2016&office=president&dv=${body.dv}`);
    expect(pinned.headers.get("cache-control")).toContain("immutable");
    const gone = await get("/api/v1/contests?dv=999999");
    expect(gone.status).toBe(410);
    const bad = await get("/api/v1/contests?dv=nope");
    expect(bad.status).toBe(400);
  });

  it("returns 2016 presidential states sorted high to low, with both values until fmt is set", async () => {
    const res = await get("/api/v1/results?contest=2016|US|president|&unit_type=state");
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      answers: string[];
      rows: { name: string; votes: number[]; share: number[]; gray: boolean; unit: string; legacy: string }[];
      display_slots: { d: string; r: string };
    };
    expect(body.answers.slice(0, 3)).toEqual(["dem_nominee", "rep_nominee", "other"]);
    expect(body.display_slots.d).toBe("dem_nominee");
    expect(body.rows.length).toBe(51);
    const colored = body.rows.filter((row) => !row.gray);
    for (let i = 1; i < colored.length; i++) {
      expect(colored[i - 1]!.share[0]).toBeGreaterThanOrEqual(colored[i]!.share[0]!);
    }
    const dc = body.rows.find((row) => row.legacy === "District of Columbia");
    expect(dc?.unit).toBe("11");
    expect(dc?.votes[0]).toBeGreaterThan(0);

    const pct = await get("/api/v1/results?contest=2016|US|president|&unit_type=state&fmt=pct&state=DC");
    const pctBody = (await pct.json()) as { rows: Record<string, unknown>[] };
    expect(pctBody.rows[0]).not.toHaveProperty("votes");
    expect(pctBody.rows[0]).toHaveProperty("share");
    const num = await get("/api/v1/results?contest=2016|US|president|&unit_type=state&fmt=num&state=DC");
    const numBody = (await num.json()) as { rows: Record<string, unknown>[] };
    expect(numBody.rows[0]).not.toHaveProperty("share");
  });

  it("returns one contest flat and two contests as series", async () => {
    const one = await get("/api/v1/results?contest=2024|AZ|us_senate|&unit_type=state");
    const oneBody = (await one.json()) as { rows: { votes?: number[] }[]; series?: unknown };
    expect(oneBody.rows[0]?.votes?.length).toBeGreaterThan(0);
    expect(oneBody).not.toHaveProperty("series");

    const two = await get(
      "/api/v1/results?contest=2016|US|president|&contest=2020|US|president|&unit_type=state&state=AL",
    );
    const twoBody = (await two.json()) as { rows: { series: { contest: string }[] }[] };
    expect(twoBody.rows[0]?.series.map((cell) => cell.contest)).toEqual([
      "2016|US|president|",
      "2020|US|president|",
    ]);
  });

  it("looks up a unit by GEOID or legacy name", async () => {
    const byGeoid = await get("/api/v1/units/42?unit_type=state&contest=2016|US|president|");
    expect(byGeoid.status).toBe(200);
    const body = (await byGeoid.json()) as { unit: string; legacy: string; result: { unit: string } };
    expect(body.unit).toBe("42");
    expect(body.legacy).toBe("Pennsylvania");
    expect(body.result.unit).toBe("42");
    const byName = await get("/api/v1/units/Pennsylvania?unit_type=state");
    expect(byName.status).toBe(200);
  });

  it("allows bearer CORS and does not set a cookie", async () => {
    const res = await get("/api/v1/manifest", { method: "OPTIONS", headers: { origin: "https://example.test" } });
    expect(res.headers.get("access-control-allow-origin")).toBe("*");
    expect(res.headers.get("access-control-allow-headers")?.toLowerCase()).toContain("authorization");
    expect(res.headers.get("set-cookie")).toBeNull();
  });

  it("locates a point inside a loaded state", async () => {
    const point = await pool.query<{ lon: number; lat: number; unit_key: string }>(
      `select st_x(st_pointonsurface(g.geom)) lon, st_y(st_pointonsurface(g.geom)) lat, u.unit_key
       from unit_geom g
       join unit u on u.id = g.unit_id
       where u.unit_type = 'state' and u.unit_key = '42' and g.lod = 0`,
    );
    const row = point.rows[0]!;
    const res = await get(`/api/v1/locate?lon=${row.lon}&lat=${row.lat}`);
    const body = (await res.json()) as { units: Record<string, string> };
    expect(body.units.state).toBe("42");
  });

  it("geocodes through an injected fetch and never calls a provider for a ZIP", async () => {
    const calls: string[] = [];
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input);
      calls.push(url);
      if (url.includes("onelineaddress")) {
        return new Response(JSON.stringify({ result: { addressMatches: [{ coordinates: { x: -77.03, y: 38.9 } }] } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response("[]", { status: 200 });
    };
    const local = createApp({ pool, fetchImpl, sleep: async () => {} });
    const first = await local.request("http://127.0.0.1/api/v1/geocode?q=1600%20Pennsylvania%20Ave%20NW");
    expect(first.status).toBe(200);
    const hit = (await first.json()) as { provider: string; point: { lon: number } };
    expect(hit.provider).toBe("census");
    expect(hit.point.lon).toBeCloseTo(-77.03);
    const before = calls.length;
    const second = await local.request("http://127.0.0.1/api/v1/geocode?q=1600%20Pennsylvania%20Ave%20NW");
    expect(second.status).toBe(200);
    expect(calls.length).toBe(before);

    const zipCalls: string[] = [];
    const zipApp = createApp({
      pool,
      fetchImpl: async (input) => {
        zipCalls.push(String(input));
        return new Response("{}", { status: 200 });
      },
    });
    const zip = await zipApp.request("http://127.0.0.1/api/v1/geocode?q=16501");
    expect(zip.status).toBe(404);
    const zipBody = (await zip.json()) as { error: { code: string } };
    expect(zipBody.error.code).toBe("no_zcta");
    expect(zipCalls).toEqual([]);
    expect(zip.headers.get("cache-control")).toContain("private");
  });

  it("falls through Census to Nominatim", async () => {
    const calls: string[] = [];
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input);
      calls.push(url);
      if (url.includes("nominatim")) {
        return new Response(JSON.stringify([{ lon: "-75.0", lat: "40.0" }]), { status: 200 });
      }
      return new Response(JSON.stringify({ result: { addressMatches: [] } }), { status: 200 });
    };
    const local = createApp({ pool, fetchImpl, sleep: async () => {} });
    const res = await local.request("http://127.0.0.1/api/v1/geocode?q=Somewhere%20Unknown%20Lane");
    expect(res.status).toBe(200);
    const body = (await res.json()) as { provider: string };
    expect(body.provider).toBe("nominatim");
    expect(calls.some((url) => url.includes("census"))).toBe(true);
    expect(calls.some((url) => url.includes("nominatim"))).toBe(true);
  });
});
