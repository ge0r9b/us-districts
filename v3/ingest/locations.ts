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

/**
 * Assign every US location to its county, state, and US House district.
 * One statement finds the hits. A point on a boundary takes the smallest polygon
 * of that type. Non-US rows stay unit-less and keep country_code.
 * Running it again changes nothing when the hits are unchanged.
 */
export async function assignLocationUnits(db: pg.Pool): Promise<LocationAssignReport> {
  const client = await db.connect();
  try {
    await client.query("begin");
    await client.query("set local statement_timeout = '10min'");
    await client.query(`
      create temp table loc_hit on commit drop as
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
        where l.geom is not null
          and not l.retracted
          and (l.country_code is null or btrim(l.country_code) = 'US')
        order by l.location_id, u.unit_type, st_area(g.geom::geography)
      ) hits
    `);
    const upsert = await client.query(`
      insert into entity_location_unit (location_id, unit_id, unit_type)
      select location_id, unit_id, unit_type from loc_hit
      on conflict (location_id, unit_type) do update
        set unit_id = excluded.unit_id
        where entity_location_unit.unit_id is distinct from excluded.unit_id
    `);
    const removed = await client.query(`
      delete from entity_location_unit elu
      where not exists (
        select 1 from loc_hit h
        where h.location_id = elu.location_id
          and h.unit_type = elu.unit_type
          and h.unit_id = elu.unit_id
      )
    `);
    const county = await client.query(`
      update entity_location l
      set unit_id = h.unit_id
      from loc_hit h
      where h.location_id = l.location_id
        and h.unit_type = 'county'
        and l.unit_id is distinct from h.unit_id
    `);
    const cleared = await client.query(`
      update entity_location l
      set unit_id = null
      where l.unit_id is not null
        and not exists (
          select 1 from loc_hit h
          where h.location_id = l.location_id and h.unit_type = 'county'
        )
    `);
    const flagged = await client.query(`
      update entity_location l
      set flags = case
        when exists (select 1 from loc_hit h where h.location_id = l.location_id)
          then array_remove(l.flags, 'no_unit_resolved')
        when l.geom is not null
          and not l.retracted
          and (l.country_code is null or btrim(l.country_code) = 'US')
          then case
            when 'no_unit_resolved' = any (coalesce(l.flags, '{}')) then l.flags
            else array_append(coalesce(l.flags, '{}'), 'no_unit_resolved')
          end
        else array_remove(l.flags, 'no_unit_resolved')
      end
      where ('no_unit_resolved' = any (coalesce(l.flags, '{}')))
        is distinct from (
          l.geom is not null
          and not l.retracted
          and (l.country_code is null or btrim(l.country_code) = 'US')
          and not exists (select 1 from loc_hit h where h.location_id = l.location_id)
        )
    `);
    const counts = await client.query<{
      eligible: string;
      assigned: string;
      counties: string;
      states: string;
      ushouse: string;
      skipped: string;
    }>(`
      select
        (select count(*) from entity_location l
          where l.geom is not null and not l.retracted
            and (l.country_code is null or btrim(l.country_code) = 'US'))::text eligible,
        (select count(distinct location_id) from loc_hit)::text assigned,
        (select count(*) from loc_hit where unit_type = 'county')::text counties,
        (select count(*) from loc_hit where unit_type = 'state')::text states,
        (select count(*) from loc_hit where unit_type = 'ushouse')::text ushouse,
        (select count(*) from entity_location l
          where l.geom is not null and not l.retracted
            and l.country_code is not null and btrim(l.country_code) <> 'US')::text skipped
    `);
    const changed =
      (upsert.rowCount ?? 0) +
      (removed.rowCount ?? 0) +
      (county.rowCount ?? 0) +
      (cleared.rowCount ?? 0) +
      (flagged.rowCount ?? 0);
    if (changed > 0) {
      await client.query(`update data_version set dv = dv + 1, built_at = now() where id = 1`);
    }
    await client.query("commit");
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
      changed,
    };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}
