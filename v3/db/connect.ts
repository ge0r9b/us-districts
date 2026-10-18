import { Client, neonConfig } from "@neondatabase/serverless";
import pg from "pg";
import ws from "ws";
import type { Queryable } from "./apply.ts";

// Node has no built-in WebSocket. The Neon client tunnels Postgres over wss,
// which is how migrate and seed run where TCP 5432 is blocked.
neonConfig.webSocketConstructor = ws;

export function requireDatabaseUrl(): string {
  const url = process.env.DATABASE_URL;
  if (!url?.trim()) throw new Error("DATABASE_URL is not set");
  return url;
}

export function isNeonHost(connectionString: string): boolean {
  let host: string;
  try {
    host = new URL(connectionString).hostname.toLowerCase();
  } catch {
    throw new Error("DATABASE_URL is not a valid URL");
  }
  return host === "neon.tech" || host.endsWith(".neon.tech");
}

/**
 * Neon hosts use the serverless WebSocket client. Any other host (local Postgres,
 * CI) uses node-pg over TCP. Both run the same SQL. The URL is never logged.
 */
/**
 * One connection for db:load. A neon.tech host uses the WebSocket client, which
 * does not open TCP 5432. Other hosts use a pg pool. Queries on a Neon connection
 * must stay sequential: the wrapper hands back that single client.
 */
export async function openLoadDb(connectionString: string): Promise<pg.Pool> {
  if (!isNeonHost(connectionString)) {
    return new pg.Pool({
      connectionString,
      max: 4,
      options: "-c search_path=usd,public",
    });
  }
  let client: Client;
  const open = async () => {
    client = new Client(connectionString);
    await client.connect();
    await client.query("set search_path = usd, public");
  };
  await open();
  const query = (text: string, params?: unknown[]) => client.query(text, params);
  const session = { query, release: () => {} };
  // connect() returns this same socket. A dropped WebSocket has to open a new client.
  const reconnect = async () => {
    try {
      await client.end();
    } catch {
      /* already closed */
    }
    await open();
  };
  return {
    query,
    connect: async () => session,
    end: () => client.end(),
    reconnect,
  } as unknown as pg.Pool;
}

export async function withDatabase<T>(connectionString: string, fn: (db: Queryable) => Promise<T>): Promise<T> {
  if (isNeonHost(connectionString)) {
    const client = new Client(connectionString);
    await client.connect();
    try {
      return await fn(client);
    } finally {
      await client.end();
    }
  }
  const client = new pg.Client({ connectionString });
  await client.connect();
  try {
    return await fn(client);
  } finally {
    await client.end();
  }
}
