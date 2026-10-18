export type SortBy = "share" | "votes";
export type SortDir = "desc" | "asc";

export type SortableRow = {
  name: string;
  /** null = no data for the sort answer. Those rows sort last, then A→Z. */
  share: number | null;
  votes: number | null;
  gray?: boolean;
};

/**
 * Bar lists sort high → low by the selected answer (SPEC §5.1).
 * Rows without data go last, alphabetical, in either direction.
 * Native clients and the web shell both call this; the API returns rows already sorted.
 */
export function sortRows<T extends SortableRow>(rows: T[], by: SortBy = "share", dir: SortDir = "desc"): T[] {
  const copy = rows.slice();
  copy.sort((a, b) => {
    const aMissing = a.gray === true || (by === "share" ? a.share == null : a.votes == null);
    const bMissing = b.gray === true || (by === "share" ? b.share == null : b.votes == null);
    if (aMissing !== bMissing) return aMissing ? 1 : -1;
    if (aMissing && bMissing) return a.name.localeCompare(b.name);
    const av = (by === "share" ? a.share : a.votes) ?? 0;
    const bv = (by === "share" ? b.share : b.votes) ?? 0;
    if (av !== bv) return dir === "desc" ? bv - av : av - bv;
    return a.name.localeCompare(b.name);
  });
  return copy;
}

export function shares(votes: number[], total: number): number[] {
  if (!(total > 0)) return votes.map(() => 0);
  return votes.map((v) => v / total);
}

/** coverage under 50% stays gray, and so does a unit with no source row. */
export function isGray(hasData: boolean, coverage: number | null): boolean {
  if (!hasData) return true;
  if (coverage != null && coverage < 0.5) return true;
  return false;
}

export type ValueFormat = "pct" | "num" | null;

/** # mode returns no shares. % mode returns no counts. Omit fmt and the client hides one. */
export function applyFormat<T extends { votes?: unknown; share?: unknown; total?: unknown }>(
  row: T,
  fmt: ValueFormat,
): T {
  if (fmt === "pct") {
    const { votes: _v, total: _t, ...rest } = row;
    return rest as T;
  }
  if (fmt === "num") {
    const { share: _s, ...rest } = row;
    return rest as T;
  }
  return row;
}
