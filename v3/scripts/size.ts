import { openLoadDb, requireDatabaseUrl } from "../db/connect.ts";
import { databaseSizeReport } from "../ingest/size-plan.ts";

const db = await openLoadDb(requireDatabaseUrl());
try {
  const report = await databaseSizeReport(db);
  console.log(JSON.stringify(report, null, 2));
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  console.error(message.replace(/postgres(?:ql)?:\/\/\S+/gi, "DATABASE_URL"));
  process.exitCode = 1;
} finally {
  await db.end();
}
