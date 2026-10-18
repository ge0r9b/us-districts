import { applyMigrations } from "../db/apply.ts";
import { requireDatabaseUrl, withDatabase } from "../db/connect.ts";

try {
  const result = await withDatabase(requireDatabaseUrl(), applyMigrations);
  if (result.applied.length === 0) {
    console.log(`already applied (${result.skipped.length} files)`);
  } else {
    console.log(`applied ${result.applied.join(", ")}`);
    if (result.skipped.length > 0) console.log(`already present ${result.skipped.join(", ")}`);
  }
} catch (err) {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
}
