import type pg from "pg";

/**
 * Heap width from the catalog. Fixed-length columns use attlen. Text uses the
 * allowance in `textBytes` when that column is named, otherwise a short inline
 * width. Geometry and skipped columns add nothing: a null does not store a value.
 * `indexBytes` is the index entry allowance for one row.
 */
export async function catalogRowBytes(
  db: pg.Pool | pg.PoolClient,
  relation: string,
  opts: { skip?: string[]; textBytes?: Record<string, number>; indexBytes?: number } = {},
): Promise<number> {
  const rel = relation.includes(".") ? relation : `usd.${relation}`;
  const sized = await db.query<{ attname: string; attlen: number; typ: string }>(
    `select a.attname, a.attlen::int attlen, t.typname typ
     from pg_attribute a
     join pg_type t on t.oid = a.atttypid
     where a.attrelid = to_regclass($1)
       and a.attnum > 0
       and not a.attisdropped`,
    [rel],
  );
  const skip = new Set(opts.skip ?? []);
  let bytes = 24;
  for (const col of sized.rows) {
    if (skip.has(col.attname)) continue;
    if (opts.textBytes && col.attname in opts.textBytes) {
      bytes += opts.textBytes[col.attname] ?? 0;
      continue;
    }
    if (col.attlen > 0) {
      bytes += col.attlen;
      continue;
    }
    if (col.typ === "geometry" || col.typ === "box2d") continue;
    if (col.typ === "numeric") bytes += 16;
    else if (col.typ === "jsonb" || col.typ === "text" || col.typ === "varchar" || col.typ === "_text") bytes += 24;
    else bytes += 16;
  }
  return bytes + (opts.indexBytes ?? 0);
}
