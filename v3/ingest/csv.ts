/** RFC 4180 reader. Columns are addressed by header name, never by position. */

export function parseCsv(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const src = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  const records = splitRecords(src);
  if (records.length === 0) return { headers: [], rows: [] };
  const headers = records[0]!.map((h) => h.trim());
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < records.length; i++) {
    const rec = records[i]!;
    if (rec.length === 1 && rec[0] === "") continue;
    const row: Record<string, string> = {};
    for (let c = 0; c < headers.length; c++) row[headers[c]!] = rec[c] ?? "";
    rows.push(row);
  }
  return { headers, rows };
}

function splitRecords(src: string): string[][] {
  const records: string[][] = [];
  let field = "";
  let rec: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < src.length; i++) {
    const ch = src[i]!;
    if (inQuotes) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          field += '"';
          i++;
        } else inQuotes = false;
      } else field += ch;
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === ",") {
      rec.push(field);
      field = "";
      continue;
    }
    if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && src[i + 1] === "\n") i++;
      rec.push(field);
      field = "";
      records.push(rec);
      rec = [];
      continue;
    }
    field += ch;
  }
  if (field.length > 0 || rec.length > 0) {
    rec.push(field);
    records.push(rec);
  }
  return records;
}

export const REQUIRED_RESULT_HEADERS = [
  "state",
  "year",
  "office",
  "district",
  "unit_id",
  "unit_type",
  "candidate_id",
  "answer",
  "party",
  "votes",
  "weight",
  "source_url",
  "retrieved_at",
] as const;

export function missingResultHeaders(headers: string[]): string[] {
  const set = new Set(headers);
  return REQUIRED_RESULT_HEADERS.filter((h) => !set.has(h));
}
