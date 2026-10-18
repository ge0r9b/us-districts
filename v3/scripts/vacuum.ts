import { openLoadDb, requireDatabaseUrl } from "../db/connect.ts";
import { VACUUM_FULL } from "../db/vacuum.ts";

const db = await openLoadDb(requireDatabaseUrl());
try {
  for (const statement of VACUUM_FULL) {
    await db.query(statement);
    console.log(statement);
  }
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  console.error(message.replace(/postgres(?:ql)?:\/\/\S+/gi, "DATABASE_URL"));
  process.exitCode = 1;
} finally {
  await db.end();
}
