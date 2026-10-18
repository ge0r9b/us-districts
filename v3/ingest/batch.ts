import type pg from "pg";

/**
 * Multi-row insert stand-in for COPY. The Neon WebSocket driver has no COPY protocol,
 * and one statement per file would exceed a frame. Each call inserts one chunk.
 */
export async function insertJsonChunks(
  db: pg.Pool | pg.PoolClient,
  sql: string,
  rows: unknown[],
  paramsPrefix: unknown[] = [],
  chunkSize = 500,
): Promise<number> {
  let written = 0;
  for (let i = 0; i < rows.length; i += chunkSize) {
    const chunk = rows.slice(i, i + chunkSize);
    const res = await db.query(sql, [...paramsPrefix, JSON.stringify(chunk)]);
    written += res.rowCount ?? 0;
  }
  return written;
}
