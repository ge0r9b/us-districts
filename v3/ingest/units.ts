import type pg from "pg";
import { STATE_ABBR } from "@usd/core";
import { insertJsonChunks } from "./batch.ts";
import { parseCsv } from "./csv.ts";

export type UnitInsert = {
  unit_type: string;
  unit_key: string;
  legacy_key: string | null;
  name: string;
  state_fips: string | null;
  state_abbr: string | null;
  geoid: string | null;
  source_record_id: string | null;
};

const TIGER_UNIT: Record<string, string> = {
  unsd: "school_unified",
  elsd: "school_elementary",
  scsd: "school_secondary",
  sldu: "sldu",
  sldl: "sldl",
};

/**
 * data/geo rows for state legislative districts and school districts. No polygons.
 * Pass tigerSets when a file mixes layers (statehouse.csv also repeats Nebraska and DC sldu rows).
 */
export function unitsFromGeoCsv(text: string, tigerSets?: readonly string[]): { units: UnitInsert[]; gaps: string[] } {
  const parsed = parseCsv(text);
  const units = new Map<string, UnitInsert>();
  const gaps: string[] = [];
  const legacySeen = new Set<string>();
  const allow = tigerSets ? new Set(tigerSets) : null;
  for (const row of parsed.rows) {
    const tiger = (row.tiger_set ?? "").trim();
    if (allow && !allow.has(tiger)) continue;
    const unitType = TIGER_UNIT[tiger];
    const geoid = (row.geoid ?? "").trim();
    const abbr = STATE_ABBR[row.state ?? ""];
    if (!unitType || !geoid || !abbr) {
      gaps.push(`geo ${row.tiger_set || "?"} ${row.state}|${row.v2_name || row.geoid}`);
      continue;
    }
    let legacy = `${row.state}|${row.v2_name || geoid}`;
    const legacyId = `${unitType}|${legacy}`;
    if (legacySeen.has(legacyId)) legacy = `${legacy}|${geoid}`;
    legacySeen.add(`${unitType}|${legacy}`);
    // Keep the last row for a GEOID so a repeated key cannot bump data_version.
    units.set(`${unitType}|${geoid}`, {
      unit_type: unitType,
      unit_key: geoid,
      legacy_key: legacy,
      name: row.tiger_name || row.v2_name || geoid,
      state_fips: geoid.slice(0, 2),
      state_abbr: abbr,
      geoid,
      source_record_id: (row.row ?? "").trim() || geoid,
    });
  }
  return { units: [...units.values()], gaps };
}

export async function ensureUnits(db: pg.Pool, units: UnitInsert[]): Promise<number> {
  if (units.length === 0) return 0;
  const client = await db.connect();
  try {
    await client.query("begin");
    const written = await insertJsonChunks(
      client,
      `insert into unit (
         boundary_set_id, unit_type, unit_key, legacy_key, name, state_fips, state_abbr, geoid, country, source_record_id
       )
       select b.id, x.unit_type, x.unit_key, nullif(x.legacy_key, ''), x.name,
              nullif(x.state_fips, ''), nullif(x.state_abbr, ''), nullif(x.geoid, ''), 'us', x.source_record_id
       from jsonb_to_recordset($1::jsonb) as x(
         unit_type text, unit_key text, legacy_key text, name text, state_fips text, state_abbr text, geoid text,
         source_record_id text
       )
       join boundary_set b on b.slug = 'v2-2024' and b.unit_type = x.unit_type
       on conflict (boundary_set_id, unit_key) do update
         set legacy_key = excluded.legacy_key, name = excluded.name,
             state_fips = excluded.state_fips, state_abbr = excluded.state_abbr, geoid = excluded.geoid,
             source_record_id = excluded.source_record_id
         where unit.name is distinct from excluded.name
            or unit.legacy_key is distinct from excluded.legacy_key
            or unit.source_record_id is distinct from excluded.source_record_id`,
      units,
    );
    if (written > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
      await client.query(
        `update boundary_set b set feature_count = c.n
         from (select boundary_set_id, count(*)::int n from unit group by boundary_set_id) c
         where b.id = c.boundary_set_id and b.slug = 'v2-2024'`,
      );
    }
    await client.query("commit");
    return written;
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}
