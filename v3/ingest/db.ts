import pg from "pg";

const { Pool } = pg;

export function createPool(connectionString: string): pg.Pool {
  return new Pool({
    connectionString,
    max: 8,
    options: "-c search_path=usd,public",
  });
}

export function databaseUrl(): string {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  return url;
}

export async function currentDv(pool: pg.Pool | pg.PoolClient): Promise<number> {
  const r = await pool.query<{ dv: number }>("select dv from data_version where id = 1");
  return r.rows[0]?.dv ?? 1;
}
