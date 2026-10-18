/** Party spellings seen in bot rows and v2, mapped to party_key. */
const PARTY_ALIASES: Record<string, string> = {
  D: "dem",
  DEM: "dem",
  DEMOCRATIC: "dem",
  DEMOCRAT: "dem",
  R: "rep",
  REP: "rep",
  REPUBLICAN: "rep",
  I: "ind",
  IND: "ind",
  INDEPENDENT: "ind",
  INDEPENDEN: "ind",
  UNA: "ind",
  UNAFFILIATED: "ind",
  LIB: "lib",
  L: "lib",
  LIBERTARIAN: "lib",
  GRN: "grn",
  GREEN: "grn",
  G: "grn",
  CON: "con",
  CONSTITUTION: "con",
  OTH: "oth",
  OTHER: "oth",
  WRI: "wri",
  "WRITE-IN": "wri",
  WRITEIN: "wri",
  "WRITE-INS": "wri",
};

export type PartySeed = { key: string; name: string; color: string; aliases: string[] };

export const PARTY_SEEDS: PartySeed[] = [
  { key: "dem", name: "Democratic", color: "#2563eb", aliases: ["DEM", "D", "DEMOCRATIC", "DEMOCRAT"] },
  { key: "rep", name: "Republican", color: "#dc2626", aliases: ["REP", "R", "REPUBLICAN"] },
  { key: "ind", name: "Independent", color: "#6b7280", aliases: ["IND", "I", "INDEPENDENT", "UNA", "UNAFFILIATED"] },
  { key: "lib", name: "Libertarian", color: "#d97706", aliases: ["LIB", "L", "LIBERTARIAN"] },
  { key: "grn", name: "Green", color: "#16a34a", aliases: ["GRN", "GREEN", "G"] },
  { key: "con", name: "Constitution", color: "#7c3aed", aliases: ["CON", "CONSTITUTION"] },
  { key: "oth", name: "Other", color: "#a8a29e", aliases: ["OTH", "OTHER"] },
  { key: "wri", name: "Write-in", color: "#a8a29e", aliases: ["WRI", "WRITE-IN", "WRITEIN"] },
];

const PARTY_COLOR = new Map(PARTY_SEEDS.map((p) => [p.key, p.color]));

export function normalizeParty(raw: string): { key: string; known: boolean } {
  const token = raw.trim().toUpperCase();
  if (!token) return { key: "oth", known: false };
  const known = PARTY_ALIASES[token];
  if (known) return { key: known, known: true };
  const key = token.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 32);
  return { key: key || "oth", known: false };
}

export function partyColor(key: string): string {
  return PARTY_COLOR.get(key) ?? "#78716c";
}

export type AnswerKeyInput = {
  candidateId: string;
  party: string;
};

/**
 * Stable answer key. dem_nominee / rep_nominee only when that party has exactly
 * one candidate in the contest, so a jungle primary does not collapse two
 * Democrats onto one slot (R10). all-others is the aggregate remainder.
 */
export function assignAnswerKeys<T extends AnswerKeyInput>(rows: T[]): (T & { answerKey: string; aggregate: boolean })[] {
  const parties = rows.map((row) => normalizeParty(row.party).key);
  const demIds = new Set<string>();
  const repIds = new Set<string>();
  rows.forEach((row, i) => {
    const id = row.candidateId.trim();
    if (parties[i] === "dem") demIds.add(id);
    if (parties[i] === "rep") repIds.add(id);
  });
  const dem = demIds.size;
  const rep = repIds.size;
  return rows.map((row, i) => {
    const party = parties[i]!;
    const id = row.candidateId.trim();
    let answerKey: string;
    if (id === "all-others") answerKey = "other";
    else if (party === "dem" && dem === 1) answerKey = "dem_nominee";
    else if (party === "rep" && rep === 1) answerKey = "rep_nominee";
    else answerKey = `cand:${id}`;
    return { ...row, answerKey, aggregate: answerKey === "other" };
  });
}

/** Presidential short labels used by the v2 thumbnails. Other contests keep the ballot label. */
const SHORT_NAME: Record<string, string> = {
  "clinton-hillary-r": "Clinton",
  "clinton-hillary": "Clinton",
  "biden-joseph-r": "Biden",
  "biden-joseph-robinette-jr": "Biden",
  "harris-kamala-d": "Harris",
  "trump-donald-j": "Trump",
  "all-others": "All other",
};

export function shortLabel(candidateId: string, ballotLabel: string): string {
  return SHORT_NAME[candidateId] ?? ballotLabel;
}

/** dem_nominee, rep_nominee, other, then every other key. */
export function compareAnswerKeys(a: string, b: string): number {
  const rank = (key: string) => (key === "dem_nominee" ? 0 : key === "rep_nominee" ? 1 : key === "other" ? 2 : 3);
  const d = rank(a) - rank(b);
  return d !== 0 ? d : a < b ? -1 : a > b ? 1 : 0;
}

export type OfficeParts = {
  /** Raw office token, including _special / _runoff. Used in contest_key. */
  token: string;
  /** Base office row (us_senate_special → us_senate). */
  officeKey: string;
  stage: "general" | "primary" | "runoff" | "special" | "recall" | "poll";
};

export function officeParts(office: string): OfficeParts {
  const token = office.trim();
  if (token.endsWith("_runoff")) return { token, officeKey: token.slice(0, -"_runoff".length), stage: "runoff" };
  if (token.endsWith("_special")) return { token, officeKey: token.slice(0, -"_special".length), stage: "special" };
  if (token.endsWith("_primary")) return { token, officeKey: token.slice(0, -"_primary".length), stage: "primary" };
  return { token, officeKey: token, stage: "general" };
}

const OFFICE_LABEL: Record<string, string> = {
  president: "President",
  us_senate: "US Senate",
  us_house: "US House",
  state_senate: "State senate",
  state_house: "State house",
};

export function officeLabel(officeKey: string): string {
  return OFFICE_LABEL[officeKey] ?? officeKey.replace(/_/g, " ");
}

/**
 * contest_key = year|state|officeToken|district.
 * President is one national contest (state US). Statewide district is empty.
 */
export function contestKey(input: { year: number | string; office: string; state: string; district?: string | null }): string {
  const parts = officeParts(input.office);
  const national = parts.officeKey === "president";
  const state = national ? "US" : input.state.trim().toUpperCase();
  const district = input.district && input.district !== "statewide" ? input.district : "";
  return `${input.year}|${state}|${parts.token}|${district}`;
}

/** Higher rank wins over a lower one even when the lower row is newer. Q-E8. */
export function methodRank(method: string): number {
  if (method === "official") return 3;
  if (method === "v2_import") return 1;
  return 2;
}

export function isEstimate(method: string, weight: number, explicit?: boolean): boolean {
  if (explicit !== undefined) return explicit;
  return method === "area_weighted" || weight < 1;
}
