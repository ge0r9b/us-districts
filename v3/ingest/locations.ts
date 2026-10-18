import type pg from "pg";

export type LocationAssignReport = {
  eligible: number;
  assigned: number;
  outside: number;
  counties: number;
  states: number;
  ushouse: number;
  skippedNonUs: number;
  changed: number;
};

/** One short transaction per slice. A dropped connection retries that slice once. */
export const LOCATION_CHUNK = 10_000;

const ELIGIBLE = `
  l.geom is not null
  and not l.retracted
  and (l.country_code is null or btrim(l.country_code) = 'US')
`;

export function isConnectionDrop(err: unknown): boolean {
  const message = err instanceof Error ? `${err.name} ${err.message}` : String(err);
  return /connection terminated|ECONNRESET|socket hang up|Connection closed|connection error|WebSocket/i.test(message);
}

async function reconnect(db: pg.Pool): Promise<void> {
  const fn = (db as pg.Pool & { reconnect?: () => Promise<void> }).reconnect;
  if (fn) await fn();
}

async function withClient<T>(db: pg.Pool, fn: (client: pg.PoolClient) => Promise<T>): Promise<T> {
  const client = await db.connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}

async function once<T>(db: pg.Pool, label: string, fn: (client: pg.PoolClient) => Promise<T>): Promise<T> {
  try {
    return await withClient(db, async (client) => {
      await client.query("begin");
      try {
        const value = await fn(client);
        await client.query("commit");
        return value;
      } catch (err) {
        try {
          await client.query("rollback");
        } catch {
          /* the socket is already gone */
        }
        throw err;
      }
    });
  } catch (err) {
    if (!isConnectionDrop(err)) throw err;
    console.log(`${label} connection dropped; retrying once`);
    await reconnect(db);
    return await withClient(db, async (client) => {
      await client.query("begin");
      try {
        const value = await fn(client);
        await client.query("commit");
        return value;
      } catch (inner) {
        try {
          await client.query("rollback");
        } catch {
          /* the socket is already gone */
        }
        throw inner;
      }
    });
  }
}

async function writeChunk(client: pg.PoolClient, ids: string[]): Promise<number> {
  await client.query("set local statement_timeout = '2min'");
  await client.query(
    `create temp table loc_hit on commit drop as
     select location_id, unit_id, unit_type
     from (
       select distinct on (l.location_id, u.unit_type)
         l.location_id,
         u.id as unit_id,
         u.unit_type
       from entity_location l
       join unit_geom g on g.lod = 0 and st_covers(g.geom, l.geom)
       join unit u on u.id = g.unit_id
         and u.unit_type in ('county', 'state', 'ushouse')
       join boundary_set b on b.id = u.boundary_set_id and b.slug = 'v2-2024'
       where l.location_id = any($1::bigint[])
       order by l.location_id, u.unit_type, st_area(g.geom::geography)
     ) hits`,
    [ids],
  );
  await client.query("create index loc_hit_loc on loc_hit (location_id, unit_type)");
  await client.query("analyze loc_hit");
  const upsert = await client.query(
    `insert into entity_location_unit (location_id, unit_id, unit_type)
     select location_id, unit_id, unit_type from loc_hit
     on conflict (location_id, unit_type) do update
       set unit_id = excluded.unit_id
       where entity_location_unit.unit_id is distinct from excluded.unit_id`,
  );
  const removed = await client.query(
    `delete from entity_location_unit elu
     using (
       select elu2.location_id, elu2.unit_type
       from unnest($1::bigint[]) as ids(id)
       join entity_location_unit elu2 on elu2.location_id = ids.id
       left join loc_hit h
         on h.location_id = elu2.location_id
        and h.unit_type = elu2.unit_type
        and h.unit_id = elu2.unit_id
       where h.location_id is null
     ) stale
     where elu.location_id = stale.location_id
       and elu.unit_type = stale.unit_type`,
    [ids],
  );
  const county = await client.query(
    `update entity_location l
     set unit_id = h.unit_id
     from loc_hit h
     where h.location_id = l.location_id
       and h.unit_type = 'county'
       and l.unit_id is distinct from h.unit_id`,
  );
  const cleared = await client.query(
    `update entity_location l
     set unit_id = null
     from (
       select ids.id
       from unnest($1::bigint[]) as ids(id)
       left join loc_hit h on h.location_id = ids.id and h.unit_type = 'county'
       where h.location_id is null
     ) s
     where l.location_id = s.id
       and l.unit_id is not null`,
    [ids],
  );
  const flagged = await client.query(
    `update entity_location l
     set flags = case
       when s.hit then array_remove(l.flags, 'no_unit_resolved')
       when 'no_unit_resolved' = any (coalesce(l.flags, '{}')) then l.flags
       else array_append(coalesce(l.flags, '{}'), 'no_unit_resolved')
     end
     from (
       select ids.id, (h.location_id is not null) as hit
       from unnest($1::bigint[]) as ids(id)
       left join (select distinct location_id from loc_hit) h on h.location_id = ids.id
     ) s
     where l.location_id = s.id
       and (('no_unit_resolved' = any (coalesce(l.flags, '{}'))) is distinct from (not s.hit))`,
    [ids],
  );
  return (
    (upsert.rowCount ?? 0) +
    (removed.rowCount ?? 0) +
    (county.rowCount ?? 0) +
    (cleared.rowCount ?? 0) +
    (flagged.rowCount ?? 0)
  );
}

/**
 * Assign every US location to its county, state, and US House district.
 * Each slice of about 10k ids commits on its own, so a dropped WebSocket keeps
 * the slices that finished. Running it again writes nothing when the hits are unchanged.
 * A point on a boundary takes the smallest polygon of that type. Non-US rows stay unit-less.
 */
export async function assignLocationUnits(db: pg.Pool): Promise<LocationAssignReport> {
  const ids = await db.query<{ location_id: string }>(
    `select l.location_id::text location_id
     from entity_location l
     where ${ELIGIBLE}
     order by l.location_id`,
  );
  const all = ids.rows.map((row) => row.location_id);
  const chunks = Math.max(1, Math.ceil(all.length / LOCATION_CHUNK));
  console.log(`locations: ${all.length} eligible in ${all.length === 0 ? 0 : chunks} chunks`);
  let changed = 0;
  for (let i = 0; i < all.length; i += LOCATION_CHUNK) {
    const slice = all.slice(i, i + LOCATION_CHUNK);
    const index = Math.floor(i / LOCATION_CHUNK) + 1;
    const label = `locations chunk ${index}/${chunks} ids ${slice[0]}–${slice[slice.length - 1]}`;
    const wrote = await once(db, label, (client) => writeChunk(client, slice));
    changed += wrote;
    console.log(`${label} changed ${wrote}`);
  }
  const report = await once(db, "locations finish", async (client) => {
    await client.query("set local statement_timeout = '30s'");
    const removed = await client.query(
      `delete from entity_location_unit elu
       where not exists (
         select 1 from entity_location l
         where l.location_id = elu.location_id and ${ELIGIBLE}
       )`,
    );
    const cleared = await client.query(
      `update entity_location l
       set unit_id = null
       where l.unit_id is not null
         and not (${ELIGIBLE})`,
    );
    const unflagged = await client.query(
      `update entity_location l
       set flags = array_remove(l.flags, 'no_unit_resolved')
       where 'no_unit_resolved' = any (coalesce(l.flags, '{}'))
         and not (${ELIGIBLE})`,
    );
    const total =
      changed + (removed.rowCount ?? 0) + (cleared.rowCount ?? 0) + (unflagged.rowCount ?? 0);
    const counts = await client.query<{
      eligible: string;
      assigned: string;
      counties: string;
      states: string;
      ushouse: string;
      skipped: string;
    }>(`
      select
        (select count(*) from entity_location l where ${ELIGIBLE})::text eligible,
        (select count(distinct elu.location_id) from entity_location_unit elu
          join entity_location l on l.location_id = elu.location_id
          where ${ELIGIBLE})::text assigned,
        (select count(*) from entity_location_unit elu
          join entity_location l on l.location_id = elu.location_id
          where elu.unit_type = 'county' and ${ELIGIBLE})::text counties,
        (select count(*) from entity_location_unit elu
          join entity_location l on l.location_id = elu.location_id
          where elu.unit_type = 'state' and ${ELIGIBLE})::text states,
        (select count(*) from entity_location_unit elu
          join entity_location l on l.location_id = elu.location_id
          where elu.unit_type = 'ushouse' and ${ELIGIBLE})::text ushouse,
        (select count(*) from entity_location l
          where l.geom is not null and not l.retracted
            and l.country_code is not null and btrim(l.country_code) <> 'US')::text skipped
    `);
    const row = counts.rows[0];
    const eligible = Number(row?.eligible ?? 0);
    const assigned = Number(row?.assigned ?? 0);
    return {
      eligible,
      assigned,
      outside: eligible - assigned,
      counties: Number(row?.counties ?? 0),
      states: Number(row?.states ?? 0),
      ushouse: Number(row?.ushouse ?? 0),
      skippedNonUs: Number(row?.skipped ?? 0),
      changed: total,
    };
  });
  if (report.changed > 0) {
    await once(db, "locations version", async (client) => {
      await client.query("set local statement_timeout = '30s'");
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    });
  }
  return report;
}
