import { STATE_ABBR, stateName } from "./states.ts";

/** Two-answer margin scale ends at ±90 points (Build 1579). Fractions, so 90 points is 0.9. */
export const MARGIN_MAX = 0.9;
export const MARGIN_MAX_POINTS = 90;
export const THUMB_PX = 30;

const DEM = [37, 99, 235] as const;
const NEUTRAL = [245, 245, 244] as const;
const REP = [220, 38, 38] as const;
const SLIDER_YEARS = [2016, 2020, 2024] as const;

export type ChartKind = "pie" | "bar" | "line";

function hex(rgb: readonly [number, number, number]): string {
  return `#${rgb.map((n) => n.toString(16).padStart(2, "0")).join("")}`;
}

function mix(a: readonly [number, number, number], b: readonly [number, number, number], t: number): string {
  const rgb = a.map((v, i) => Math.round(v + (b[i]! - v) * t)) as [number, number, number];
  return hex(rgb);
}

/** Linear red/blue through neutral. ±90 and beyond are the endpoint colours; ±60 is not. */
export function marginColor(margin: number): string {
  if (margin <= -MARGIN_MAX) return hex(DEM);
  if (margin >= MARGIN_MAX) return hex(REP);
  const t = margin / MARGIN_MAX;
  if (t < 0) return mix(NEUTRAL, DEM, -t);
  return mix(NEUTRAL, REP, t);
}

const LEGEND_LEFT: Record<number, string> = { 2016: "Clinton", 2020: "Biden", 2024: "Harris" };

export function legendText(year: number, compact = false): string {
  const left = LEGEND_LEFT[year] ?? "Dem";
  if (compact) return `${left} +90  Trump +90`;
  return `${left} D+90 … Trump R+90`;
}

export function chartMenu(years: readonly number[]): ChartKind[] {
  return years.length <= 1 ? ["pie", "bar"] : ["line", "bar"];
}

export function resolveChart(pick: string, years: readonly number[]): ChartKind {
  const menu = chartMenu(years);
  return menu.includes(pick as ChartKind) ? (pick as ChartKind) : "bar";
}

export function lineYears(start: number, end: number): number[] {
  const lo = Math.min(start, end);
  const hi = Math.max(start, end);
  return SLIDER_YEARS.filter((year) => year >= lo && year <= hi);
}

export type SegmentChange = {
  fromYear: number;
  toYear: number;
  change: number | null;
  label: string;
};

/** Margin-point change between each consecutive slider year. `margins` are rep − dem fractions. */
export function segmentChanges(years: readonly number[], margins: readonly (number | null)[]): SegmentChange[] {
  const out: SegmentChange[] = [];
  for (let i = 1; i < years.length; i++) {
    const fromYear = years[i - 1]!;
    const toYear = years[i]!;
    const a = margins[i - 1] ?? null;
    const b = margins[i] ?? null;
    const change = a == null || b == null ? null : Math.round((b - a) * 1000) / 10;
    const span = `'${String(fromYear).slice(2)}>'${String(toYear).slice(2)}`;
    const label = change == null ? `${span} n/a` : `${span} ${change > 0 ? "+" : ""}${change.toFixed(1)}`;
    out.push({ fromYear, toYear, change, label });
  }
  return out;
}

export type InstitutionGroupName = "Countries" | "States" | "Counties" | "Provinces";

export type InstitutionHit = {
  id: string;
  label: string;
  group: InstitutionGroupName;
  gray: boolean;
  note: string | null;
};

export type InstitutionExtra = { id: string; label: string; group?: InstitutionGroupName };

export type InstitutionSearch = {
  groups: { name: InstitutionGroupName; hits: InstitutionHit[] }[];
  message: string | null;
};

export const CANADA_NOTE = "Canada units load in v3.1";

export const CANADA_PROVINCES: readonly { abbr: string; name: string }[] = [
  { abbr: "AB", name: "Alberta" },
  { abbr: "BC", name: "British Columbia" },
  { abbr: "MB", name: "Manitoba" },
  { abbr: "NB", name: "New Brunswick" },
  { abbr: "NL", name: "Newfoundland and Labrador" },
  { abbr: "NS", name: "Nova Scotia" },
  { abbr: "NT", name: "Northwest Territories" },
  { abbr: "NU", name: "Nunavut" },
  { abbr: "ON", name: "Ontario" },
  { abbr: "PE", name: "Prince Edward Island" },
  { abbr: "QC", name: "Quebec" },
  { abbr: "SK", name: "Saskatchewan" },
  { abbr: "YT", name: "Yukon" },
];

const COUNTRIES: { id: string; label: string; aliases: string[] }[] = [
  { id: "country:US", label: "United States", aliases: ["us", "usa", "america", "united states", "u.s.", "u.s.a."] },
  { id: "country:CA", label: "Canada", aliases: ["canada"] },
  { id: "country:GE", label: "Georgia", aliases: ["republic of georgia"] },
];

const GROUP_ORDER: InstitutionGroupName[] = ["Countries", "States", "Counties", "Provinces"];

function norm(q: string): string {
  return q.trim().toLowerCase().replace(/\./g, "");
}

function rank(label: string, aliases: string[], q: string): number {
  const l = norm(label);
  if (!q) return l === "united states" ? 0 : 50;
  if (l === q) return 0;
  if (aliases.some((alias) => norm(alias) === q)) return 1;
  if (l.startsWith(q) || aliases.some((alias) => norm(alias).startsWith(q))) return 2;
  if (l.includes(q) || aliases.some((alias) => norm(alias).includes(q))) return 3;
  return 99;
}

export function searchInstitutions(query: string, extras: readonly InstitutionExtra[] = []): InstitutionSearch {
  const q = norm(query);
  const scored: { hit: InstitutionHit; score: number }[] = [];
  const push = (hit: InstitutionHit, score: number) => {
    if (score < 99) scored.push({ hit, score });
  };
  if (!q) {
    push({ id: "country:US", label: "United States", group: "Countries", gray: false, note: null }, 0);
  } else {
    for (const country of COUNTRIES) push({ id: country.id, label: country.label, group: "Countries", gray: false, note: null }, rank(country.label, country.aliases, q));
    for (const [name, abbr] of Object.entries(STATE_ABBR)) {
      push({ id: `state:${abbr}`, label: name, group: "States", gray: false, note: null }, rank(name, [abbr], q));
    }
    for (const extra of extras) {
      if ((extra.group ?? "Counties") !== "Counties") continue;
      push({ id: extra.id, label: extra.label, group: "Counties", gray: false, note: null }, rank(extra.label, [], q));
    }
    for (const province of CANADA_PROVINCES) {
      push(
        { id: `province:${province.abbr}`, label: province.name, group: "Provinces", gray: true, note: CANADA_NOTE },
        rank(province.name, [province.abbr], q),
      );
    }
  }
  const exactState = q.length > 0 && scored.some((item) => {
    if (item.hit.group !== "States") return false;
    return norm(item.hit.label) === q || item.hit.id.toLowerCase().endsWith(`:${q}`);
  });
  const order: InstitutionGroupName[] = exactState
    ? ["States", "Countries", "Counties", "Provinces"]
    : GROUP_ORDER;
  const groups = order.map((name) => ({
    name,
    hits: scored
      .filter((item) => item.hit.group === name)
      .sort((a, b) => a.score - b.score || a.hit.label.localeCompare(b.hit.label))
      .map((item) => item.hit),
  })).filter((group) => group.hits.length > 0);
  if (q && scored.length === 0) return { groups: [], message: "No institutions match" };
  return { groups, message: null };
}

export function topInstitutionHit(query: string, extras: readonly InstitutionExtra[] = []): InstitutionHit | null {
  const found = searchInstitutions(query, extras);
  const flat = found.groups.flatMap((group) => group.hits);
  if (flat.length === 0) return null;
  const q = norm(query);
  const exact = flat.filter((hit) => norm(hit.label) === q || hit.id.toLowerCase().endsWith(`:${q}`));
  return exact.find((hit) => hit.group === "States") ?? exact[0] ?? flat[0]!;
}

/** Committed institution label. Never empty. */
export function institutionField(raw: string, current: string): string {
  const typed = raw.trim();
  if (typed) return typed;
  const kept = current.trim();
  if (kept) return kept;
  return "United States";
}

export type ChainUnit = {
  unit_type: string;
  unit_key: string;
  state_abbr?: string | null;
  name?: string | null;
};

export type PlaceChain = {
  dc: boolean;
  stateAbbr: string | null;
  stateKey: string | null;
  countyKey: string | null;
  countyName: string | null;
  precinctKey: string | null;
  precinctLabel: string | null;
  crumbs: string[];
  level: "state" | "county" | "precinct";
};

/** Drop a county prefix. Precinct names are shown whole. */
export function precinctLabel(name: string | null | undefined): string {
  let text = (name ?? "").trim();
  const pipe = text.lastIndexOf("|");
  if (pipe >= 0) text = text.slice(pipe + 1).trim();
  const stripped = text.replace(/^.+?\bCounty\b\s+/i, "").trim();
  return stripped || text;
}

export function placeChain(units: readonly ChainUnit[]): PlaceChain {
  const first = (type: string) => units.find((unit) => unit.unit_type === type);
  const state = first("state");
  const county = first("county");
  const precinct = first("precinct");
  const abbr = state?.state_abbr?.trim().toUpperCase() || null;
  const dc = abbr === "DC" || state?.unit_key === "11";
  const prec = precinct ? precinctLabel(precinct.name) : "";
  if (dc) {
    const crumbs = ["District of Columbia"];
    if (prec) crumbs.push(prec);
    return {
      dc: true,
      stateAbbr: "DC",
      stateKey: state?.unit_key ?? "11",
      countyKey: null,
      countyName: null,
      precinctKey: precinct?.unit_key ?? null,
      precinctLabel: prec || null,
      crumbs,
      level: precinct ? "precinct" : "state",
    };
  }
  const named = abbr ? stateName(abbr) : null;
  const stateLabel = named || state?.name?.trim() || null;
  const countyName = county?.name?.trim() || null;
  const crumbs: string[] = [];
  if (stateLabel) crumbs.push(stateLabel);
  if (countyName) crumbs.push(countyName);
  if (prec) crumbs.push(prec);
  const level = precinct ? "precinct" : county ? "county" : "state";
  return {
    dc: false,
    stateAbbr: abbr,
    stateKey: state?.unit_key ?? null,
    countyKey: county?.unit_key ?? null,
    countyName,
    precinctKey: precinct?.unit_key ?? null,
    precinctLabel: prec || null,
    crumbs,
    level,
  };
}

/** 2016 twin of a 2024 precinct. Map lookup only. */
export function twinKey(twins: ReadonlyMap<string, string>, unitKey: string): string | null {
  return twins.get(unitKey) ?? null;
}

/**
 * Start value for a range. Precincts that include 2016 read the stored twin.
 * A missing twin is null. States and other types use the same unit. No geometry.
 */
export function rangeStartVotes(opts: {
  years: readonly number[];
  unitKey: string;
  unitType: string;
  twins: ReadonlyMap<string, string>;
  votesAt: (year: number, unitKey: string) => number | null;
}): number | null {
  if (opts.years.length === 0) return null;
  const start = Math.min(...opts.years);
  if (opts.unitType === "precinct" && opts.years.includes(2016)) {
    const twin = twinKey(opts.twins, opts.unitKey);
    if (!twin) return null;
    return opts.votesAt(2016, twin);
  }
  return opts.votesAt(start, opts.unitKey);
}

/** Clock offset does not depend on whether the year row is open. */
export function sliderFrame(open: boolean): { clockTop: number; rowVisibility: "visible" | "hidden" } {
  return { clockTop: 0, rowVisibility: open ? "visible" : "hidden" };
}

export function sliderLabelXs(rects: readonly { left: number; width: number }[]): number[] {
  return rects.map((rect) => rect.left + rect.width / 2);
}

export function thumbnailBox(ready: boolean): { size: number; visibility: "visible" | "hidden" } {
  return { size: THUMB_PX, visibility: ready ? "visible" : "hidden" };
}

/**
 * pointerup performs the tap and marks it handled.
 * The click that follows does not.
 * A click with no prior pointerup (keyboard) does.
 * Non-primary buttons do not.
 */
export function pointerTap(
  kind: "pointerup" | "click",
  alreadyHandled: boolean,
  button = 0,
): { act: boolean; handled: boolean } {
  if (button !== 0) return { act: false, handled: alreadyHandled };
  if (kind === "pointerup") return { act: true, handled: true };
  if (alreadyHandled) return { act: false, handled: false };
  return { act: true, handled: false };
}

/** A pick is a map lookup. Twins, slot years, and membership stay off this path. */
export function pickUnit<T>(index: ReadonlyMap<string, T>, id: string): T | undefined {
  return index.get(id);
}

export type CameraView = { lon: number; lat: number; zoom: number };

const PARENT_SCOPE = new Set(["", "US", "USA"]);

/**
 * A state scope with no rows of this type stays empty.
 * A US total, or a row with no state, is not shown under that state.
 */
export function scopeRows<T extends { state?: string | null; unit?: string }>(input: {
  stateAbbr: string;
  unitType: string;
  rows: readonly T[];
}): T[] {
  const state = input.stateAbbr.trim().toUpperCase();
  const districtList = input.unitType === "ushouse" || input.unitType.startsWith("school_") || input.unitType === "sldu" || input.unitType === "sldl";
  if (!state || state === "US" || !districtList) return [...input.rows];
  return input.rows.filter((row) => {
    const rowState = (row.state ?? "").trim().toUpperCase();
    if (PARENT_SCOPE.has(rowState) || row.unit === "US") return false;
    return rowState === state;
  });
}

export function emptyScopeMessage(unitType: string, count: number): string | null {
  if (count > 0) return null;
  if (unitType === "ushouse" || unitType.startsWith("school_") || unitType === "sldu" || unitType === "sldl") {
    return "No districts";
  }
  return null;
}

export type SchoolLabelRow = {
  geoid?: string | null;
  unit?: string | null;
  name: string;
  county?: string | null;
  state?: string | null;
  lea?: string | null;
};

/** Same-name school districts gain a county, else a state, else an id. Duplicate GEOIDs drop. */
export function schoolLabels(rows: readonly SchoolLabelRow[]): { geoid: string; label: string }[] {
  const seen = new Set<string>();
  const unique: (SchoolLabelRow & { geoid: string })[] = [];
  for (const row of rows) {
    const geoid = (row.geoid ?? row.unit ?? "").trim();
    if (!geoid || seen.has(geoid)) continue;
    seen.add(geoid);
    unique.push({ ...row, geoid });
  }
  const counts = new Map<string, number>();
  for (const row of unique) counts.set(row.name, (counts.get(row.name) ?? 0) + 1);
  return unique.map((row) => {
    if ((counts.get(row.name) ?? 0) < 2) return { geoid: row.geoid, label: row.name };
    const extra = (row.county ?? "").trim() || (row.state ?? "").trim() || (row.lea ?? "").trim() || row.geoid;
    return { geoid: row.geoid, label: `${row.name}, ${extra}` };
  });
}
