/** Full state name → USPS abbreviation, including DC. Names match v2 and data-v3/geo. */
export const STATE_ABBR: Record<string, string> = {
  Alabama: "AL",
  Alaska: "AK",
  Arizona: "AZ",
  Arkansas: "AR",
  California: "CA",
  Colorado: "CO",
  Connecticut: "CT",
  Delaware: "DE",
  "District of Columbia": "DC",
  Florida: "FL",
  Georgia: "GA",
  Hawaii: "HI",
  Idaho: "ID",
  Illinois: "IL",
  Indiana: "IN",
  Iowa: "IA",
  Kansas: "KS",
  Kentucky: "KY",
  Louisiana: "LA",
  Maine: "ME",
  Maryland: "MD",
  Massachusetts: "MA",
  Michigan: "MI",
  Minnesota: "MN",
  Mississippi: "MS",
  Missouri: "MO",
  Montana: "MT",
  Nebraska: "NE",
  Nevada: "NV",
  "New Hampshire": "NH",
  "New Jersey": "NJ",
  "New Mexico": "NM",
  "New York": "NY",
  "North Carolina": "NC",
  "North Dakota": "ND",
  Ohio: "OH",
  Oklahoma: "OK",
  Oregon: "OR",
  Pennsylvania: "PA",
  "Rhode Island": "RI",
  "South Carolina": "SC",
  "South Dakota": "SD",
  Tennessee: "TN",
  Texas: "TX",
  Utah: "UT",
  Vermont: "VT",
  Virginia: "VA",
  Washington: "WA",
  "West Virginia": "WV",
  Wisconsin: "WI",
  Wyoming: "WY",
};

const ABBR_TO_NAME = new Map(Object.entries(STATE_ABBR).map(([name, abbr]) => [abbr, name]));

export const STATE_ABBRS = new Set(Object.values(STATE_ABBR));

export function stateAbbr(nameOrAbbr: string): string | null {
  const raw = nameOrAbbr.trim();
  if (raw.length === 2 && STATE_ABBRS.has(raw.toUpperCase())) return raw.toUpperCase();
  return STATE_ABBR[raw] ?? null;
}

export function stateName(abbr: string): string | null {
  return ABBR_TO_NAME.get(abbr.toUpperCase()) ?? null;
}

/** Row `state` column: 50 states, DC, or US for a national row. */
export function isAllowedStateCode(code: string): boolean {
  return code === "US" || STATE_ABBRS.has(code);
}
