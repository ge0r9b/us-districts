/** Neon free-tier guard. The project cap is 0.5 GB; stay near 350 MB unless a group is named. */

export const BUDGET_BYTES = 350 * 1024 * 1024;

/** Result row plus its indexes and the refreshed aggregate share. Measured from the alpha.1 load, rounded up. */
export const EST_RESULT_BYTES = 800;

export const EST_UNIT_BYTES = 280;

/** Point row plus the GiST index. */
export const EST_LOCATION_BYTES = 520;

/**
 * company_locations.csv.gz at data/companies c6f1cf9: 212,439 rows, 172 brands.
 * Four sub-brand QIDs are only in sub_entity_id (1,146 rows). Their entity rows are tiny next to the points.
 */
export const COMPANY_LOCATION_ROWS = 212_439;

export function fitsBudget(currentBytes: number, addBytes: number): boolean {
  return currentBytes + addBytes <= BUDGET_BYTES;
}

/** The load gate. `pg_database_size` is the measurement. A rounded row estimate is not added. */
export function overMeasuredBudget(databaseBytes: number): boolean {
  return databaseBytes > BUDGET_BYTES;
}

/**
 * Institution loads gate on the projected net change.
 * A reload that adds nothing, or that deletes side-table rows, is allowed
 * when the live database is already over the gate. A positive addition that
 * lands over the gate is refused unless `allow` is set.
 * `projectedBytes` null means the projection could not be made.
 */
export function loadGrowthRefused(
  currentBytes: number,
  projectedBytes: number | null,
  allow = false,
): boolean {
  if (allow) return false;
  if (projectedBytes == null) return overMeasuredBudget(currentBytes);
  const net = projectedBytes - currentBytes;
  return net > 0 && projectedBytes > BUDGET_BYTES;
}

export function companyLoadAllowed(databaseBytes: number, allow: boolean): boolean {
  return allow || !overMeasuredBudget(databaseBytes);
}

export function formatMb(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
}

/**
 * Gzipped election CSVs on data/election run about 0.17 rows per compressed byte
 * (Pennsylvania 2024 precincts: 152,423 bytes, 25,874 rows).
 */
export function estimateRowsFromGzip(bytes: number): number {
  return Math.ceil(bytes * 0.17);
}
