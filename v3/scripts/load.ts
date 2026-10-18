import { createPool, databaseUrl } from "../ingest/db.ts";
import { loadAll } from "../ingest/load-all.ts";

const pool = createPool(databaseUrl());
try {
  const summary = await loadAll(pool);
  console.log(
    JSON.stringify(
      {
        boundaries: summary.boundaries,
        results: summary.results.map((row) => ({
          file: row.fileName,
          status: row.status,
          rows: row.rows,
          rejected: row.rejected,
          changed: row.changed,
        })),
        gaps: summary.gaps.length,
      },
      null,
      2,
    ),
  );
} finally {
  await pool.end();
}
