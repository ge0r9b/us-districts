import { isNeonHost, openLoadDb, requireDatabaseUrl } from "../db/connect.ts";
import { formatMb } from "../ingest/budget.ts";
import { loadAll, repoRoot } from "../ingest/load-all.ts";

function list(flag: string, envName: string, fallback: string[]): string[] {
  const fromArg = process.argv.find((arg) => arg.startsWith(`--${flag}=`));
  const raw = fromArg ? fromArg.slice(flag.length + 3) : process.env[envName];
  if (raw == null || raw.trim() === "") return fallback;
  return raw.split(",").map((part) => part.trim()).filter(Boolean);
}

function safe(err: unknown): string {
  const message = err instanceof Error ? err.message : "load failed";
  return message.replace(/postgres(?:ql)?:\/\/\S+/gi, "DATABASE_URL");
}

const include = list("include", "USD_LOAD_INCLUDE", ["core", "districts", "precincts", "schools"]);
const allowOverBudget = list("allow-over-budget", "USD_LOAD_OVER_BUDGET", []);

let db: Awaited<ReturnType<typeof openLoadDb>> | null = null;
try {
  const url = requireDatabaseUrl();
  db = await openLoadDb(url);
  const summary = await loadAll(db, repoRoot(), { include, allowOverBudget });
  console.log(
    JSON.stringify(
      {
        transport: isNeonHost(url) ? "neon-websocket" : "pg",
        database: formatMb(summary.databaseBytes),
        boundaries: summary.boundaries,
        results: summary.results.map((row) => ({
          file: row.fileName,
          status: row.status,
          rows: row.rows,
          rejected: row.rejected,
          changed: row.changed,
          rules: row.rejectRules,
        })),
        companies: summary.companies,
        institutions: summary.institutions,
        locations: summary.locations,
        estimates: summary.estimates.map((row) => ({ ...row, mb: formatMb(row.bytes) })),
        gaps: summary.gaps,
      },
      null,
      2,
    ),
  );
} catch (err) {
  console.error(safe(err));
  process.exitCode = 1;
} finally {
  await db?.end();
}
