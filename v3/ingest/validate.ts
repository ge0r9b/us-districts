import { ALLOWED_UNIT_TYPES, canonicalUnitType, isAllowedStateCode } from "@usd/core";

export type RawResult = {
  lineNo: number;
  state: string;
  year: string;
  office: string;
  district: string;
  unitId: string;
  unitType: string;
  candidateId: string;
  answer: string;
  party: string;
  votes: string;
  weight: string;
  sourceUrl: string;
  retrievedAt: string;
  method: string;
  boundarySet: string;
  /** Set by the v2 importer. CSV rows leave this unset and derive it. */
  estimate?: boolean;
};

export type Reject = { lineNo: number; rule: string; detail: string };

const FUTURE_SKEW_MS = 2 * 24 * 60 * 60 * 1000;

export function validateRow(row: RawResult, now = Date.now()): Reject | null {
  const required: [string, string][] = [
    ["state", row.state],
    ["year", row.year],
    ["office", row.office],
    ["unit_id", row.unitId],
    ["unit_type", row.unitType],
    ["votes", row.votes],
    ["source_url", row.sourceUrl],
    ["retrieved_at", row.retrievedAt],
    ["candidate_id", row.candidateId],
  ];
  for (const [name, value] of required) {
    if (!value.trim()) return { lineNo: row.lineNo, rule: "R02_required", detail: name };
  }
  const votes = Number(row.votes);
  if (!Number.isFinite(votes) || votes < 0) return { lineNo: row.lineNo, rule: "R03_votes", detail: row.votes };
  if (row.weight.trim()) {
    const w = Number(row.weight);
    if (!Number.isFinite(w) || w <= 0 || w > 1) return { lineNo: row.lineNo, rule: "R04_weight", detail: row.weight };
  }
  if (!/^\d{4}$/.test(row.year.trim())) return { lineNo: row.lineNo, rule: "R05_year", detail: row.year };
  const year = Number(row.year);
  if (year < 1789 || year > 2100) return { lineNo: row.lineNo, rule: "R05_year", detail: row.year };
  if (!isAllowedStateCode(row.state.trim().toUpperCase())) {
    return { lineNo: row.lineNo, rule: "R05_state", detail: row.state };
  }
  const unitType = canonicalUnitType(row.unitType);
  if (!ALLOWED_UNIT_TYPES.has(unitType)) return { lineNo: row.lineNo, rule: "R06_unit_type", detail: row.unitType };
  if (!/^https?:\/\//i.test(row.sourceUrl.trim())) {
    return { lineNo: row.lineNo, rule: "R08_url", detail: "source_url" };
  }
  const when = Date.parse(row.retrievedAt.trim());
  if (Number.isNaN(when)) return { lineNo: row.lineNo, rule: "R08_timestamp", detail: row.retrievedAt };
  if (when > now + FUTURE_SKEW_MS) return { lineNo: row.lineNo, rule: "R08_timestamp", detail: "in the future" };
  return null;
}

/** Natural key of a results row (Q-E12). Stage is inside the office token. */
export function naturalKey(row: RawResult): string {
  return [
    row.year.trim(),
    row.office.trim(),
    row.boundarySet.trim() || "v2-2024",
    canonicalUnitType(row.unitType),
    row.unitId.trim(),
    row.candidateId.trim(),
  ].join("\u001f");
}

export function countRejectRules(rejects: Reject[]): Record<string, number> {
  const rules: Record<string, number> = {};
  for (const reject of rejects) rules[reject.rule] = (rules[reject.rule] ?? 0) + 1;
  return rules;
}

/** Up to three negative vote cells, for the load report. The value is the votes column. */
export function negativeVoteExamples(rejects: Reject[], limit = 3): { lineNo: number; detail: string }[] {
  return rejects
    .filter((reject) => reject.rule === "R03_votes")
    .slice(0, limit)
    .map((reject) => ({ lineNo: reject.lineNo, detail: reject.detail }));
}

export function formatRejectRules(
  rules: Record<string, number>,
  examples: { lineNo: number; detail: string }[] = [],
): string {
  const parts = Object.keys(rules)
    .sort()
    .map((rule) => `${rule} ${rules[rule]}`);
  const sample = examples.map((example) => `line ${example.lineNo} votes=${example.detail}`);
  return [parts.join(", "), sample.length > 0 ? `examples: ${sample.join("; ")}` : ""].filter(Boolean).join("; ");
}

export function markDuplicates(rows: RawResult[]): Reject[] {
  const seen = new Map<string, number[]>();
  for (const row of rows) {
    const k = naturalKey(row);
    const list = seen.get(k);
    if (list) list.push(row.lineNo);
    else seen.set(k, [row.lineNo]);
  }
  const out: Reject[] = [];
  for (const [key, lines] of seen) {
    if (lines.length < 2) continue;
    for (const lineNo of lines) out.push({ lineNo, rule: "R09_duplicate", detail: key });
  }
  return out;
}
