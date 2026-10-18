-- Shrink the institution load without dropping live rows.
-- Text entity_id stays unique. Hot joins store entity.nid.
-- v2 keys and image attribution stay out of these indexes; the loader writes a pack.
-- VACUUM FULL is outside the migration transaction (see db/apply.ts).
-- Idempotent. A later schema change is a new numbered file.

set search_path = usd, public;

alter table entity add column if not exists nid bigint generated always as identity;
alter table entity add column if not exists code_scheme text;
alter table entity add column if not exists code text;

create unique index if not exists entity_nid on entity (nid);
create index if not exists entity_code on entity (country, code_scheme, code);

alter table entity drop constraint if exists entity_kind_check;
alter table entity add constraint entity_kind_check check (kind in (
  'nation','territory','province','state','county','municipality','township',
  'school_unified','school_elementary','school_secondary',
  'chamber','dc_council',
  'subdivision',
  'court',
  'special_district',
  'indigenous_government',
  'local_authority','regional_authority','intermunicipal','submunicipal','parish',
  'government_other',
  'brand','organization','company','nonprofit','fund',
  'other'
));

alter table entity drop constraint if exists entity_gov_status_check;
alter table entity add constraint entity_gov_status_check check (
  gov_status is null or gov_status in (
    'government','area_only','dependent','administrative','unknown'
  )
);

-- Foreign local governments (docs/v3 at ed669fa). US rows have country null, so they pass.
-- A code change keeps the frozen entity_id. Feed ids are never entity ids.
-- valid_from does not require valid_from_source: loaded rows already omit that source.
alter table entity drop constraint if exists entity_foreign_id_check;
alter table entity add constraint entity_foreign_id_check check (
  country is null or btrim(country) = 'us'
  or kind not in (
    'county','municipality','local_authority','regional_authority',
    'intermunicipal','submunicipal','parish'
  )
  or entity_id ~ ('^' || kind || ':' || btrim(country) || '-[A-Za-z0-9-]+$')
);

alter table entity drop constraint if exists entity_foreign_kind_country_check;
alter table entity add constraint entity_foreign_kind_country_check check (
  kind not in ('local_authority','regional_authority','intermunicipal','submunicipal','parish')
  or country is not null
);

alter table entity drop constraint if exists entity_feed_id_check;
alter table entity add constraint entity_feed_id_check check (
  entity_id !~ '^(gss|de-ars|fr-cog|fr-siren):'
);

alter table entity drop constraint if exists entity_code_scheme_check;
alter table entity add constraint entity_code_scheme_check check (
  code is null or code_scheme is not null
);

-- One insert can name a parent that appears later in the same statement.
alter table entity drop constraint if exists entity_parent_id_fkey;
alter table entity add constraint entity_parent_id_fkey
  foreign key (parent_id) references entity (entity_id) deferrable initially deferred;

-- v2_key is null on the hot row. The GIN indexed nothing useful and cost about 3 MB before vacuum.
drop index if exists entity_v2;

alter table entity drop constraint if exists entity_wikidata_key;
create unique index if not exists entity_wikidata_key on entity (wikidata) where wikidata is not null;

drop index if exists entity_iso_3166_2;
create unique index if not exists entity_iso_3166_2 on entity (iso_3166_2) where iso_3166_2 is not null;

-- Relation ends repeat entity_id. Store the surrogate once the text id is backfilled.
alter table entity_relation add column if not exists parent_nid bigint;
alter table entity_relation add column if not exists child_nid bigint;

do $fill_relation$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'usd' and table_name = 'entity_relation' and column_name = 'parent_id'
  ) then
    update entity_relation r
    set parent_nid = p.nid
    from entity p
    where p.entity_id = r.parent_id and r.parent_nid is null;
    update entity_relation r
    set child_nid = c.nid
    from entity c
    where c.entity_id = r.child_id and r.child_nid is null;
  end if;
end
$fill_relation$;

drop index if exists entity_relation_child;

do $drop_relation_text$
declare
  cons name;
begin
  for cons in
    select con.conname
    from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace nsp on nsp.oid = rel.relnamespace
    where nsp.nspname = 'usd'
      and rel.relname = 'entity_relation'
      and pg_get_constraintdef(con.oid) ~ 'parent_id|child_id'
  loop
    execute format('alter table entity_relation drop constraint %I', cons);
  end loop;
end
$drop_relation_text$;

alter table entity_relation drop column if exists parent_id;
alter table entity_relation drop column if exists child_id;
alter table entity_relation alter column parent_nid set not null;
alter table entity_relation alter column child_nid set not null;

alter table entity_relation drop constraint if exists entity_relation_parent_nid_fkey;
alter table entity_relation add constraint entity_relation_parent_nid_fkey
  foreign key (parent_nid) references entity (nid);

alter table entity_relation drop constraint if exists entity_relation_child_nid_fkey;
alter table entity_relation add constraint entity_relation_child_nid_fkey
  foreign key (child_nid) references entity (nid);

alter table entity_relation drop constraint if exists entity_relation_nid_distinct;
alter table entity_relation add constraint entity_relation_nid_distinct check (parent_nid <> child_nid);

alter table entity_relation drop constraint if exists entity_relation_nid_key;
alter table entity_relation add constraint entity_relation_nid_key
  unique nulls not distinct (parent_nid, child_nid, relation, valid_from);

create index if not exists entity_relation_child on entity_relation (child_nid);

-- Company locations repeat the brand id. The public id stays on entity.entity_id.
alter table entity_location add column if not exists entity_nid bigint;
alter table entity_location add column if not exists sub_entity_nid bigint;

do $fill_location$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'usd' and table_name = 'entity_location' and column_name = 'entity_id'
  ) then
    update entity_location l
    set entity_nid = e.nid
    from entity e
    where e.entity_id = l.entity_id and l.entity_nid is null;
    update entity_location l
    set sub_entity_nid = e.nid
    from entity e
    where e.entity_id = l.sub_entity_id and l.sub_entity_nid is null;
  end if;
end
$fill_location$;

drop index if exists entity_location_entity;

do $drop_location_text$
declare
  cons name;
begin
  for cons in
    select con.conname
    from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace nsp on nsp.oid = rel.relnamespace
    where nsp.nspname = 'usd'
      and rel.relname = 'entity_location'
      and pg_get_constraintdef(con.oid) ~ 'entity_id|sub_entity_id'
  loop
    execute format('alter table entity_location drop constraint %I', cons);
  end loop;
end
$drop_location_text$;

alter table entity_location drop column if exists entity_id;
alter table entity_location drop column if exists sub_entity_id;
alter table entity_location alter column entity_nid set not null;

alter table entity_location drop constraint if exists entity_location_entity_nid_fkey;
alter table entity_location add constraint entity_location_entity_nid_fkey
  foreign key (entity_nid) references entity (nid) on delete cascade;

alter table entity_location drop constraint if exists entity_location_sub_entity_nid_fkey;
alter table entity_location add constraint entity_location_sub_entity_nid_fkey
  foreign key (sub_entity_nid) references entity (nid);

create index if not exists entity_location_entity on entity_location (entity_nid) where not retracted;

-- Rewrites. applyMigrations runs these after COMMIT. npm run db:vacuum retries them,
-- and also rewrites the side tables once the institution reload has deleted their rows.
vacuum (full, analyze) entity;
vacuum (full, analyze) entity_location_unit;
