/**
 * Result-list state filter. Empty filter keeps every row.
 * Comparison is on the USPS abbreviation the API already resolved.
 */
export function matchesState(stateAbbr: string | null | undefined, filter: string | null | undefined): boolean {
  if (!filter) return true;
  if (!stateAbbr) return false;
  return stateAbbr.toUpperCase() === filter.trim().toUpperCase();
}

/** Unit types the alpha.1 boundary load actually has. Others are rejected, not invented. */
export const ALPHA_UNIT_TYPES = ["state", "county", "ushouse"] as const;

export type AlphaUnitType = (typeof ALPHA_UNIT_TYPES)[number];

const ALIASES: Record<string, string> = {
  senate: "sldu",
  statehouse: "sldl",
  cd: "ushouse",
  counties: "county",
  states: "state",
};

export function canonicalUnitType(raw: string): string {
  const t = raw.trim().toLowerCase();
  return ALIASES[t] ?? t;
}

/** Geography filter. Place and district level. Not the institution filter. */
export const GEOGRAPHY_LEVELS = [
  { key: "state", label: "States" },
  { key: "county", label: "Counties" },
  { key: "precinct", label: "Precincts" },
] as const;

export type GeographyLevel = (typeof GEOGRAPHY_LEVELS)[number]["key"];

export function geographyLevel(raw: string | null | undefined): GeographyLevel | null {
  const key = (raw ?? "").trim().toLowerCase();
  return GEOGRAPHY_LEVELS.some((level) => level.key === key) ? (key as GeographyLevel) : null;
}

export const ALLOWED_UNIT_TYPES = new Set([
  "state",
  "county",
  "county_subdivision",
  "place",
  "precinct",
  "ushouse",
  "sldu",
  "sldl",
  "school_unified",
  "school_elementary",
  "school_secondary",
  "ward",
  "seat",
]);
