-- Location membership, institution columns, and body_entity.
-- Maps data/inst-entities 4215fab onto docs/v3 at v3/plan 99481d0.
-- Idempotent. A later schema change is a new numbered file.

set search_path = usd, public;

-- A company point can fall in a county, a state, and a US House district.
-- entity_location.unit_id stays the county. The other two live here.
create table if not exists entity_location_unit (
  location_id bigint not null references entity_location(location_id) on delete cascade,
  unit_id     bigint not null references unit(id) on delete cascade,
  unit_type   text not null check (unit_type in ('county','state','ushouse')),
  primary key (location_id, unit_type)
);

create index if not exists entity_location_unit_unit on entity_location_unit (unit_id);

alter table entity drop constraint if exists entity_kind_check;
alter table entity add constraint entity_kind_check check (kind in (
  'nation','territory','province','state','county','municipality','township',
  'school_unified','school_elementary','school_secondary',
  'chamber','dc_council',
  'subdivision',
  'court',
  'special_district',
  'indigenous_government',
  'government_other',
  'brand','organization','company','nonprofit','fund',
  'other'
));

alter table entity drop constraint if exists entity_special_district_check;
alter table entity add constraint entity_special_district_check check (
  kind <> 'special_district'
  or entity_id ~ '^special_district:[a-z]{2}-[a-z0-9]+-[A-Za-z0-9._-]+$'
);

alter table entity add column if not exists valid_from_source text;
alter table entity add column if not exists inception date;
alter table entity add column if not exists inception_precision text;
alter table entity add column if not exists inception_source text;
alter table entity add column if not exists constituent_qid text;

alter table entity drop constraint if exists entity_inception_precision_check;
alter table entity add constraint entity_inception_precision_check check (
  inception_precision is null or inception_precision in ('day','month','year')
);

alter table entity drop constraint if exists entity_constituent_qid_check;
alter table entity add constraint entity_constituent_qid_check check (
  constituent_qid is null or constituent_qid ~ '^Q[0-9]+$'
);

alter table entity_relation drop constraint if exists entity_relation_relation_check;
alter table entity_relation add constraint entity_relation_relation_check check (
  relation in ('parent_org','owned_by','brand_of','consolidated_with','parent','in_county')
);

alter table entity_relation add column if not exists method text;

alter table entity_relation drop constraint if exists entity_relation_method_check;
alter table entity_relation add constraint entity_relation_method_check check (
  method is null or method in ('sourced','overlay','point_in_polygon','manual')
);

-- Public images need attribution. Hidden rows need attribution and a source URL.
-- Applied before any image insert on a fresh database. Neon has no image rows yet.
alter table entity_image drop constraint if exists entity_image_public_attr_check;
alter table entity_image add constraint entity_image_public_attr_check check (
  not public or attribution is not null
);

alter table entity_image drop constraint if exists entity_image_hidden_check;
alter table entity_image add constraint entity_image_hidden_check check (
  public or (attribution is not null and source_url is not null)
);

create table if not exists body_entity (
  body_key         text primary key,
  entity_id        text not null references entity(entity_id) on update cascade,
  role             text not null check (role in ('council','mayor','chamber','court','board')),
  source_record_id text
);

create index if not exists body_entity_entity on body_entity (entity_id);
