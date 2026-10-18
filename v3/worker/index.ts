import { Client, neonConfig } from "@neondatabase/serverless";
import { createApp } from "../api/src/app.ts";
import { fetchPacks } from "../api/src/fetch-packs.ts";

export type WorkerEnv = {
  DATABASE_URL: string;
  TILES_BASE?: string;
  PACKS_BASE?: string;
};

neonConfig.webSocketConstructor = WebSocket;

/**
 * Cloudflare Worker for /api/v1.
 * DATABASE_URL is a secret (`wrangler secret put DATABASE_URL`), never a var in wrangler.toml.
 * One Neon client per request so `search_path` applies to the queries in that request.
 */
export default {
  async fetch(request: Request, env: WorkerEnv): Promise<Response> {
    if (!env.DATABASE_URL) {
      return Response.json({ error: { code: "config", message: "DATABASE_URL is not set" } }, { status: 500 });
    }
    const client = new Client(env.DATABASE_URL);
    try {
      await client.connect();
      await client.query("set search_path = usd, public");
      const app = createApp({
        sql: client,
        tilesBase: env.TILES_BASE ?? "",
        packs: fetchPacks(env.PACKS_BASE ?? ""),
      });
      return await app.fetch(request);
    } catch {
      return Response.json({ error: { code: "upstream", message: "Database request failed" } }, { status: 502 });
    } finally {
      try {
        await client.end();
      } catch {
        /* the response is already decided */
      }
    }
  },
};
