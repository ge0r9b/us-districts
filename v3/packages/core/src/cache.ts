export type CacheKind = "manifest" | "pinned" | "open" | "geocode" | "locate";

/** Cache-Control values from ARCHITECTURE.md §5. Pinned responses embed dv. */
export function cacheControl(kind: CacheKind): string {
  switch (kind) {
    case "manifest":
      return "public, max-age=60, s-maxage=60, stale-while-revalidate=600";
    case "pinned":
      return "public, max-age=86400, s-maxage=31536000, immutable";
    case "geocode":
      return "private, max-age=3600";
    case "locate":
      return "public, s-maxage=86400";
    default:
      return "public, s-maxage=300, stale-while-revalidate=86400";
  }
}

/**
 * Address normalization for the geocode cache key.
 * Uppercase, collapse whitespace, expand a few common suffixes. No raw address is stored.
 */
export function normalizeAddress(q: string): string {
  const suffixes: Record<string, string> = {
    STREET: "ST",
    AVENUE: "AVE",
    BOULEVARD: "BLVD",
    DRIVE: "DR",
    ROAD: "RD",
    LANE: "LN",
    COURT: "CT",
    PLACE: "PL",
    NORTH: "N",
    SOUTH: "S",
    EAST: "E",
    WEST: "W",
  };
  return q
    .trim()
    .toUpperCase()
    .replace(/[.,#]/g, " ")
    .replace(/\s+/g, " ")
    .split(" ")
    .map((w) => suffixes[w] ?? w)
    .join(" ");
}
