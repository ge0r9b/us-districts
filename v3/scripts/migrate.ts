import { applyMigrations } from "../db/apply.ts";
import { requireDatabaseUrl, withDatabase } from "../db/connect.ts";
import { listVacuumTargets, migrationRewriteNotes, vacuumReminder } from "../db/vacuum.ts";

try {
  await withDatabase(requireDatabaseUrl(), async (db) => {
    const result = await applyMigrations(db);
    if (result.applied.length === 0) {
      console.log(`already applied (${result.skipped.length} files)`);
    } else {
      console.log(`applied ${result.applied.join(", ")}`);
      if (result.skipped.length > 0) console.log(`already present ${result.skipped.join(", ")}`);
    }
    const reminder = vacuumReminder(migrationRewriteNotes(), await listVacuumTargets(db));
    if (reminder) console.log(reminder);
  });
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  console.error(message.replace(/postgres(?:ql)?:\/\/\S+/gi, "DATABASE_URL"));
  process.exit(1);
}
