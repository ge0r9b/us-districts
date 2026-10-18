import { openLoadDb, requireDatabaseUrl } from "../db/connect.ts";
import { formatMb } from "../ingest/budget.ts";
import { repoRoot } from "../ingest/load-all.ts";
import { buildPrecincts, dryRunPrecincts } from "../ingest/precincts.ts";

const state = process.argv.find((arg) => arg.startsWith("--state="))?.slice("--state=".length);
const dryRun = process.argv.includes("--dry-run");
const db = await openLoadDb(requireDatabaseUrl());
try {
  if (dryRun) {
    const estimate = await dryRunPrecincts(db, repoRoot(), { state });
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          ...estimate,
          database: formatMb(estimate.databaseBytes),
          estimated: estimate.estimatedBytes == null ? "partial" : formatMb(estimate.estimatedBytes),
          projected: estimate.projectedBytes == null ? "partial" : formatMb(estimate.projectedBytes),
        },
        null,
        2,
      ),
    );
  } else {
    const built = await buildPrecincts(db, repoRoot(), { state });
    console.log(JSON.stringify({ states: built.states, gaps: built.gaps.slice(0, 20), gapCount: built.gaps.length }, null, 2));
  }
} finally {
  await db.end();
}
