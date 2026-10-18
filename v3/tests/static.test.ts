import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { PMTiles } from "pmtiles";
import {
  encodeEstBits,
  estBit,
  placeFromName,
  rowsFromPack,
  searchPlaceNames,
  statePlaceNames,
  staticPackKey,
  tileRangeOk,
  type ResultPack,
} from "@usd/core";
import { exportStaticSample, sampleContestKeys, STATIC_FILE_LIMIT } from "../ingest/static-export.ts";
import worker from "../worker/index.ts";
import { buildUnitArchive } from "../ingest/unit-tiles.ts";
import { createTestPool } from "./db.ts";

const root = fileURLToPath(new URL("..", import.meta.url));

describe("static packs", () => {
  it("treats Pages 200 and R2 206 as a readable tile range", () => {
    expect(tileRangeOk(200)).toBe(true);
    expect(tileRangeOk(206)).toBe(true);
    expect(tileRangeOk(404)).toBe(false);
    expect(tileRangeOk(416)).toBe(false);
  });

  it("reads a content-hash pack into the results row shape", () => {
    const flags = [false, true];
    const pack: ResultPack = {
      v: 3,
      contest: "2024|US|president|",
      unit_type: "state",
      boundary_set: "v2-2024",
      answers: ["dem_nominee", "rep_nominee", "other"],
      display_slots: { d: "dem_nominee", r: "rep_nominee" },
      ids: ["42", "11"],
      names: ["Pennsylvania", "District of Columbia"],
      legacy: ["Pennsylvania", "District of Columbia"],
      states: ["PA", "DC"],
      geoids: ["42", "11"],
      votes: [
        [100, 50, 10],
        [3, 1, 0],
      ],
      total: [160, 4],
      est: encodeEstBits(flags),
    };
    const rows = rowsFromPack(pack);
    expect(rows[0]?.share?.[0]).toBeCloseTo(100 / 160);
    expect(rows[0]?.gray).toBe(false);
    expect(rows[1]?.est).toBe(true);
    expect(estBit(pack.est, 0)).toBe(false);
    expect(rows[1]?.name).toBe("District of Columbia");
  });

  it("searches bundled place names without a geocoder", () => {
    const names = [
      ...statePlaceNames(),
      { name: "Erie County", state: "PA", kind: "county", unit: "42049" },
    ];
    expect(searchPlaceNames("GA", names)?.name).toBe("Georgia");
    expect(searchPlaceNames("erie", names)?.unit).toBe("42049");
    expect(placeFromName(searchPlaceNames("Pennsylvania", names)!).level).toBe("state");
    expect(searchPlaceNames("", names)).toBeNull();
    expect(staticPackKey("2024|US|president|", "county")).toBe("2024|US|president||county");
  });

  it("keeps Node builtins off the request path and secrets out of wrangler", () => {
    const files = [
      "api/src/app.ts",
      "api/src/geocode.ts",
      "api/src/precinct-results.ts",
      "api/src/fetch-packs.ts",
      "worker/index.ts",
    ];
    for (const file of files) {
      const text = readFileSync(join(root, file), "utf8");
      expect(text, file).not.toMatch(/from ["']node:/);
      expect(text, file).not.toMatch(/from ["']pg["']/);
    }
    const toml = readFileSync(join(root, "wrangler.toml"), "utf8");
    expect(toml).not.toMatch(/^\s*account_id\s*=/m);
    expect(toml).not.toMatch(/^\s*DATABASE_URL\s*=/m);
    expect(toml).toContain("worker/index.ts");
    const worker = readFileSync(join(root, "worker/index.ts"), "utf8");
    expect(worker).toContain("wrangler secret put DATABASE_URL");
    expect(worker).toContain(".dev.vars");
    expect(worker).not.toContain("postgres://");
    const ignore = readFileSync(join(root, ".gitignore"), "utf8");
    expect(ignore).toMatch(/^\.dev\.vars$/m);
    expect(readFileSync(join(root, "app/src/main.ts"), "utf8")).not.toContain("VITE_STATIC");
  });

  it("returns a config error when the Worker has no DATABASE_URL", async () => {
    const res = await worker.fetch(new Request("http://127.0.0.1/api/v1/manifest"), {
      DATABASE_URL: "",
      TILES_BASE: "",
      PACKS_BASE: "",
    });
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error: { code: string; message: string } };
    expect(body.error).toEqual({ code: "config", message: "DATABASE_URL is not set" });
    expect(JSON.stringify(body)).not.toContain("postgres");
  });

  it("fails a non-Neon DATABASE_URL before connecting and does not echo it", async () => {
    const secret = "postgresql://user:local-secret@127.0.0.1:5432/usd_v3";
    const res = await worker.fetch(new Request("http://127.0.0.1/api/v1/manifest"), {
      DATABASE_URL: secret,
      TILES_BASE: "",
      PACKS_BASE: "",
    });
    expect(res.status).toBe(502);
    const text = await res.text();
    expect(text).not.toContain("local-secret");
    expect(text).not.toContain("127.0.0.1");
    expect(text).toContain("Database request failed");
  });

  it("builds a state archive under 25 MiB", () => {
    const ring: [number, number][] = [
      [-80, 40],
      [-75, 40],
      [-75, 42],
      [-80, 42],
      [-80, 40],
    ];
    const bytes = buildUnitArchive([{ id: "42", name: "Pennsylvania", rings: [ring] }], "state", 3);
    expect(bytes.length).toBeLessThan(STATIC_FILE_LIMIT);
    expect(String.fromCharCode(...bytes.slice(0, 7))).toBe("PMTiles");
  });

  it("exports a 2016 presidential state pack the shell can read", async () => {
    const pool = createTestPool();
    const dir = mkdtempSync(join(tmpdir(), "usd-static-"));
    try {
      const { files } = await exportStaticSample(pool, {
        packsDir: dir,
        tilesDir: join(dir, "tiles"),
        contests: ["2016|US|president|"],
        unitTypes: ["state"],
        tiles: true,
      });
      expect(files.length).toBeGreaterThan(0);
      for (const file of files) expect(file.bytes).toBeLessThan(STATIC_FILE_LIMIT);
      const index = JSON.parse(readFileSync(join(dir, "index.json"), "utf8")) as {
        packs: Record<string, { file: string }>;
      };
      const hit = index.packs[staticPackKey("2016|US|president|", "state")];
      expect(hit?.file).toMatch(/^[0-9a-f]{12}\.json$/);
      const pack = JSON.parse(readFileSync(join(dir, hit!.file), "utf8")) as ResultPack;
      const dc = rowsFromPack(pack).find((row) => row.legacy === "District of Columbia");
      expect(dc?.votes?.[0]).toBeGreaterThan(0);
      const tile = files.find((file) => file.path.endsWith("state-2024@1.pmtiles"));
      expect(tile).toBeTruthy();
      const archive = new PMTiles({
        getKey: () => "state",
        getBytes: async (offset: number, length: number) => {
          const raw = readFileSync(tile!.path);
          const slice = raw.subarray(offset, Math.min(raw.length, offset + length));
          return { data: slice.buffer.slice(slice.byteOffset, slice.byteOffset + slice.byteLength) };
        },
      });
      const header = await archive.getHeader();
      expect(header.minZoom).toBe(3);
      const keys = await sampleContestKeys(pool);
      expect(keys).toEqual(expect.arrayContaining(["2016|US|president|", "2020|US|president|", "2024|US|president|"]));
      expect(keys.some((key) => key.toLowerCase().includes("senate"))).toBe(false);
    } finally {
      await pool.end();
    }
  });
});
