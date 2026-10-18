/**
 * v2-parity d/r columns (DATA_LOADING.md §12). v3 stores every answer;
 * this picks which answer fills the d and r display slots.
 *
 * d = the Democratic nominee, unless an eligible non-major candidate has more
 *     votes than that Democrat (independent beat the Democrat), or there is
 *     no Democrat (then the leading eligible candidate).
 * r = the Republican with the most votes.
 * Write-ins (party wri) and the aggregate "other" bucket never take a slot.
 * Colour still follows party; an independent in the d slot is not Democratic.
 */
export type SlotCandidate = {
  answerKey: string;
  party: string;
  votes: number;
  aggregate?: boolean;
};

export type DisplaySlot = { answerKey: string; rule: string };

export type DisplaySlots = { d: DisplaySlot | null; r: DisplaySlot | null };

function eligible(c: SlotCandidate): boolean {
  if (c.aggregate || c.party === "oth" || c.party === "wri" || c.answerKey === "other") return false;
  return true;
}

function byVotes(a: SlotCandidate, b: SlotCandidate): number {
  if (b.votes !== a.votes) return b.votes - a.votes;
  return a.answerKey < b.answerKey ? -1 : a.answerKey > b.answerKey ? 1 : 0;
}

export function displaySlots(candidates: SlotCandidate[]): DisplaySlots {
  const pool = candidates.filter(eligible);
  const dems = pool.filter((c) => c.party === "dem").sort(byVotes);
  const reps = pool.filter((c) => c.party === "rep").sort(byVotes);
  const others = pool.filter((c) => c.party !== "dem" && c.party !== "rep").sort(byVotes);
  const dem = dems[0] ?? null;
  const other = others[0] ?? null;

  let d: DisplaySlot | null = null;
  if (dem && other && other.votes > dem.votes) {
    d = { answerKey: other.answerKey, rule: "independent_beat_dem" };
  } else if (dem) {
    d = { answerKey: dem.answerKey, rule: "dem_nominee" };
  } else if (other) {
    d = { answerKey: other.answerKey, rule: "no_dem" };
  }

  const rep = reps[0] ?? null;
  const r = rep ? { answerKey: rep.answerKey, rule: "rep_nominee" } : null;
  return { d, r };
}
