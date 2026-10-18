-- load_manifest.csv: load files marked db. source_set is the 8-hex hash from
-- source_sets.csv. Feed is a smallint code; the names live in enum_feed.
-- entity_v2_rows.csv is a repo file and is not loaded.
-- pack/entity_feed_map.csv stays a pack. This file does not insert it.
-- Changing entity.feed from text to smallint rewrites entity.
-- Run npm run db:vacuum after migrate. This file does not vacuum.

set search_path = usd, public;

create table if not exists enum_feed (
  feed smallint primary key,
  name text not null,
  description text
);

create table if not exists enum_feed_map_status (
  status smallint primary key,
  name text not null,
  description text
);

create table if not exists enum_load_group (
  load_group smallint primary key,
  name text not null,
  description text
);

create table if not exists source_set_member (
  source_set text not null check (source_set ~ '^[0-9a-f]{8}$'),
  ord smallint not null,
  source_id text not null references source(source_id),
  primary key (source_set, ord)
);

create index if not exists source_set_member_source on source_set_member (source_id);

alter table entity add column if not exists source_set text;
alter table entity drop constraint if exists entity_source_set_check;
alter table entity add constraint entity_source_set_check
  check (source_set is null or source_set ~ '^[0-9a-f]{8}$');

alter table entity_relation add column if not exists source_set text;
alter table entity_relation drop constraint if exists entity_relation_source_set_check;
alter table entity_relation add constraint entity_relation_source_set_check
  check (source_set is null or source_set ~ '^[0-9a-f]{8}$');

alter table entity_image add column if not exists source_set text;
alter table entity_image drop constraint if exists entity_image_source_set_check;
alter table entity_image add constraint entity_image_source_set_check
  check (source_set is null or source_set ~ '^[0-9a-f]{8}$');

alter table entity_geoid add column if not exists source_set text;
alter table entity_geoid drop constraint if exists entity_geoid_source_set_check;
alter table entity_geoid add constraint entity_geoid_source_set_check
  check (source_set is null or source_set ~ '^[0-9a-f]{8}$');

alter table body_entity add column if not exists source_set text;
alter table body_entity drop constraint if exists body_entity_source_set_check;
alter table body_entity add constraint body_entity_source_set_check
  check (source_set is null or source_set ~ '^[0-9a-f]{8}$');

do $feed$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'usd' and table_name = 'entity' and column_name = 'feed' and data_type = 'text'
  ) then
    alter table entity alter column feed type smallint using (
      case when feed ~ '^[0-9]+$' then feed::smallint else null end
    );
  end if;
end
$feed$;

alter table entity drop constraint if exists entity_feed_code_check;
alter table entity add constraint entity_feed_code_check
  check (feed is null or (feed >= 1 and feed <= 32767));
