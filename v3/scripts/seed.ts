import { applySeed } from "../db/apply.ts";
import { requireDatabaseUrl, withDatabase } from "../db/connect.ts";

try {
  await withDatabase(requireDatabaseUrl(), applySeed);
  console.log("seeded");
} catch (err) {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
}
