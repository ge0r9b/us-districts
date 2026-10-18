import { afterAll, describe, expect, it } from "vitest";
import { createApp } from "../api/src/app.ts";
import { createTestPool } from "./db.ts";

const pool = createTestPool();
const app = createApp({ pool });

afterAll(async () => {
  await pool.end();
});

describe("results latency", () => {
  it("answers a county contest inside the origin budget", async () => {
    const path = "http://127.0.0.1/api/v1/results?contest=2024|US|president|&unit_type=county&state=PA";
    await app.request(path);
    const samples: number[] = [];
    for (let i = 0; i < 7; i++) {
      const start = performance.now();
      const res = await app.request(path);
      await res.arrayBuffer();
      samples.push(performance.now() - start);
    }
    samples.sort((a, b) => a - b);
    const median = samples[Math.floor(samples.length / 2)]!;
    console.log(`PA 2024 county results median ${median.toFixed(1)} ms`);
    expect(median).toBeLessThan(150);
  });
});
