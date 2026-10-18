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
