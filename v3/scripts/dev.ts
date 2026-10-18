import { serve } from "@hono/node-server";
import { createServer } from "vite";
import { createApp } from "../api/src/app.ts";
import { nodePacks } from "../api/src/node-packs.ts";
import { createPool, databaseUrl } from "../ingest/db.ts";

const pool = createPool(databaseUrl());
const api = createApp({ sql: pool, packs: nodePacks() });
serve({ fetch: api.fetch, hostname: "127.0.0.1", port: 8861 });
const vite = await createServer();
await vite.listen();
console.log("api http://127.0.0.1:8861  app http://127.0.0.1:8860");
