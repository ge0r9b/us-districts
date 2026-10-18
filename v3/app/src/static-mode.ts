import {
  matchesState,
  placeFromName,
  rowsFromPack,
  searchPlaceNames,
  statePlaceNames,
  staticPackKey,
  type PlaceName,
  type ResultPack,
  type StaticPackIndex,
} from "@usd/core";

export type StaticResults = {
  dv: number;
  answers: string[];
  rows: ReturnType<typeof rowsFromPack>;
};

function asset(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}${path.replace(/^\//, "")}`;
}

let indexPromise: Promise<StaticPackIndex | null> | null = null;
let namesPromise: Promise<PlaceName[] | null> | null = null;

function loadIndex(): Promise<StaticPackIndex | null> {
  indexPromise ??= fetch(asset("packs/static/index.json"))
    .then(async (res) => (res.ok ? ((await res.json()) as StaticPackIndex) : null))
    .catch(() => null);
  return indexPromise;
}

function loadNames(): Promise<PlaceName[] | null> {
  namesPromise ??= fetch(asset("packs/static/names.json"))
    .then(async (res) => {
      if (!res.ok) return null;
      const body = (await res.json()) as { names?: PlaceName[] };
      return body.names ?? null;
    })
    .catch(() => null);
  return namesPromise;
}

/** Results from the content-hashed pack index. The same row shape as `/api/v1/results`. */
export async function fetchStaticResults(
  year: number,
  view: { unitType: string; state: string | null },
): Promise<{ ok: true; body: StaticResults } | { ok: false; message: string }> {
  const index = await loadIndex();
  const contest = `${year}|US|president|`;
  const hit = index?.packs[staticPackKey(contest, view.unitType)];
  if (!index || !hit) return { ok: false, message: "No rows" };
  const res = await fetch(asset(`packs/static/${hit.file}`));
  if (!res.ok) return { ok: false, message: "No rows" };
  const pack = (await res.json()) as ResultPack;
  let rows = rowsFromPack(pack);
  if (view.state) rows = rows.filter((row) => matchesState(row.state, view.state));
  return { ok: true, body: { dv: index.dv, answers: pack.answers, rows } };
}

/** Address box without geocode or locate: bundled names, then the state list. */
export async function lookupPlace(query: string) {
  const bundled = (await loadNames()) ?? [];
  const hit = searchPlaceNames(query, bundled) ?? searchPlaceNames(query, statePlaceNames());
  return hit ? placeFromName(hit) : null;
}
