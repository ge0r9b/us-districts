import { isGray, shares } from "./sort.ts";
import { STATE_ABBR, stateName } from "./states.ts";

/** Cloudflare Pages answers Range with 200. R2 answers 206. Both are a readable PMTiles header. */
export function tileRangeOk(status: number): boolean {
  return status === 200 || status === 206;
}

/** Bit i of a base64 bitset. Same layout as the precinct pack `est` field. */
export function estBit(est: string, index: number): boolean {
  if (!est) return false;
  const binary = atob(est);
  const byte = binary.charCodeAt(index >> 3);
  if (!Number.isFinite(byte)) return false;
  return (byte & (1 << (index & 7))) !== 0;
}

export function encodeEstBits(flags: boolean[]): string {
  const bytes = new Uint8Array(Math.ceil(flags.length / 8));
  flags.forEach((on, index) => {
    if (on) bytes[index >> 3] |= 1 << (index & 7);
  });
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

/** Compact result pack. Postgres stays the source of truth; this is the static copy. */
export type ResultPack = {
  v: 3;
  contest: string;
  unit_type: string;
  boundary_set: string;
  answers: string[];
  display_slots: Record<string, string>;
  ids: string[];
  names: string[];
  legacy: (string | null)[];
  states: (string | null)[];
  geoids: (string | null)[];
  votes: (number[] | null)[];
  total: (number | null)[];
  est: string;
};

export type PackRow = {
  unit: string;
  legacy: string | null;
  name: string;
  state: string | null;
  geoid: string | null;
  votes: number[] | null;
  total: number | null;
  share: number[] | null;
  est: boolean;
  gray: boolean;
};

/** One row shape for the API and for a static pack. */
export function rowsFromPack(pack: ResultPack): PackRow[] {
  return pack.ids.map((id, index) => {
    const votes = pack.votes[index] ?? null;
    const total = pack.total[index] ?? null;
    const has = votes != null && total != null;
    return {
      unit: id,
      legacy: pack.legacy[index] ?? null,
      name: pack.names[index] ?? id,
      state: pack.states[index] ?? null,
      geoid: pack.geoids[index] ?? null,
      votes: has ? votes : null,
      total: has ? total : null,
      share: has && votes && total != null ? shares(votes, total) : null,
      est: estBit(pack.est, index),
      gray: isGray(has, null),
    };
  });
}

export type StaticPackIndex = {
  v: 3;
  dv: number;
  packs: Record<string, { sha: string; file: string }>;
};

export function staticPackKey(contest: string, unitType: string): string {
  return `${contest}|${unitType}`;
}

export type PlaceName = {
  name: string;
  state: string | null;
  kind: string;
  unit: string;
};

/** Client-side place search when geocode and locate are not available. */
export function searchPlaceNames(query: string, names: readonly PlaceName[]): PlaceName | null {
  const q = query.trim().toLowerCase();
  if (!q) return null;
  const exact = names.find((row) => row.name.toLowerCase() === q || (row.state ?? "").toLowerCase() === q || row.unit.toLowerCase() === q);
  if (exact) return exact;
  return names.find((row) => row.name.toLowerCase().includes(q)) ?? null;
}

export function statePlaceNames(): PlaceName[] {
  return Object.entries(STATE_ABBR).map(([name, abbr]) => ({
    name,
    state: abbr,
    kind: "state",
    unit: abbr,
  }));
}

export function placeFromName(hit: PlaceName): {
  level: "state" | "county" | "ushouse";
  stateAbbr: string;
  stateKey: string | null;
  countyName: string | null;
  focus: string | null;
  crumbs: string[];
  dc: boolean;
} {
  const abbr = (hit.state ?? "").toUpperCase();
  if (hit.kind === "county") {
    return {
      level: "county",
      stateAbbr: abbr,
      stateKey: abbr,
      countyName: hit.name,
      focus: hit.unit,
      crumbs: [stateName(abbr) ?? abbr, hit.name],
      dc: abbr === "DC",
    };
  }
  if (hit.kind === "district") {
    return {
      level: "ushouse",
      stateAbbr: abbr,
      stateKey: abbr,
      countyName: null,
      focus: hit.unit,
      crumbs: [hit.name],
      dc: abbr === "DC",
    };
  }
  return {
    level: "state",
    stateAbbr: abbr || hit.unit.toUpperCase(),
    stateKey: hit.unit,
    countyName: null,
    focus: hit.unit,
    crumbs: [hit.name],
    dc: (abbr || hit.unit).toUpperCase() === "DC",
  };
}
