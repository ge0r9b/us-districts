import { openLoadDb, requireDatabaseUrl } from "../db/connect.ts";
import { vacuumBloated } from "../db/vacuum.ts";

const db = await openLoadDb(requireDatabaseUrl());
try {
  const run = await vacuumBloated(db);
  for (const line of run.lines) console.log(line);
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  console.error(message.replace(/postgres(?:ql)?:\/\/\S+/gi, "DATABASE_URL"));
  process.exitCode = 1;
} finally {
  await db.end();
}
