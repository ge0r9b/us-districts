import pg from "pg";

/** Admin URL. Tests never trust a process.env mutation from globalSetup. */
export function databaseUrl(): string {
  return process.env.DATABASE_URL ?? "postgresql://usd:usd@127.0.0.1:5432/usd_v3";
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
