import pg from "pg";

/** Admin URL. Tests never trust a process.env mutation from globalSetup. */
export function databaseUrl(): string {
  const url = process.env.DATABASE_URL;
  if (!url?.trim()) throw new Error("DATABASE_URL is not set");
  let host: string;
  try {
    host = new URL(url).hostname.toLowerCase();
  } catch {
    throw new Error("DATABASE_URL is not a valid URL");
  }
  if (host === "neon.tech" || host.endsWith(".neon.tech")) {
    throw new Error("Refusing to run tests against a Neon host. Point DATABASE_URL at a local Postgres.");
  }
  return url;
}

export function testDatabaseUrl(): string {
  const url = new URL(databaseUrl());
  url.pathname = "/usd_v3_test";
  return url.toString();
}

export function createTestPool(): pg.Pool {
  return new pg.Pool({
    connectionString: testDatabaseUrl(),
    max: 4,
    options: "-c search_path=usd,public",
  });
}
