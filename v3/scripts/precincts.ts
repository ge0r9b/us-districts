import { openLoadDb, requireDatabaseUrl } from "../db/connect.ts";
import { repoRoot } from "../ingest/load-all.ts";
import { buildPrecincts } from "../ingest/precincts.ts";

const state = process.argv.find((arg) => arg.startsWith("--state="))?.slice("--state=".length);
const db = await openLoadDb(requireDatabaseUrl());
try {
  const built = await buildPrecincts(db, repoRoot(), { state });
  console.log(JSON.stringify({ states: built.states, gaps: built.gaps.slice(0, 20), gapCount: built.gaps.length }, null, 2));
} finally {
  await db.end();
}
