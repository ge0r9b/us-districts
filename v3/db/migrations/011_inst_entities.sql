-- inst-entities 1fde48d (docs/v3 at 1bf4947). Idempotent.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

alter table entity add column if not exists iso_3166_2 text;

alter table entity drop constraint if exists entity_kind_check;
alter table entity add constraint entity_kind_check check (kind in (
  'nation','territory','province','state','county','municipality','township',
  'school_unified','school_elementary','school_secondary',
  'chamber','dc_council',
  'subdivision',
  'court',
  'government_other',
  'brand','organization','company','nonprofit','fund',
  'other'
));

alter table entity drop constraint if exists entity_subdivision_check;
alter table entity add constraint entity_subdivision_check check (
  kind <> 'subdivision'
  or (entity_id ~ '^subdivision:[a-z]{2}-[a-z0-9]{1,3}$' and iso_3166_2 is not null)
);

alter table entity drop constraint if exists entity_court_check;
alter table entity add constraint entity_court_check check (
  kind <> 'court' or entity_id ~ '^court:[a-z]{2}-[a-z0-9-]+$'
);

create unique index if not exists entity_iso_3166_2 on entity (iso_3166_2);

comment on column entity.wikidata is
  'entities.csv wikidata. At data/inst-entities 1fde48d the value is already wikidata:Q.... A bare Q id is prefixed once.';

alter table entity_relation drop constraint if exists entity_relation_relation_check;
alter table entity_relation add constraint entity_relation_relation_check check (
  relation in ('parent_org','owned_by','brand_of','consolidated_with','parent')
);

alter table entity_image add column if not exists icon boolean not null default false;

alter table entity_image drop constraint if exists entity_image_icon_check;
alter table entity_image add constraint entity_image_icon_check check (not icon or public);

create unique index if not exists entity_image_one_icon
  on entity_image (coalesce(entity_id, feed_entity_id)) where icon;
