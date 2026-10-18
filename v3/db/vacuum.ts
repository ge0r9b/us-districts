/** Rewrites that return space to pg_database_size. Regular VACUUM does not. Not inside a transaction. */

export const VACUUM_FULL = [
  "vacuum (full, analyze) entity",
  "vacuum (full, analyze) entity_location_unit",
  "vacuum (full, analyze) entity_extra",
  "vacuum (full, analyze) entity_image_text",
  "vacuum (full, analyze) entity_image_source",
] as const;

export function isVacuumStatement(sql: string): boolean {
  return /^\s*vacuum\b/i.test(sql);
}
