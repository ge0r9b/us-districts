-- Alpha.2 load columns. Idempotent.
-- CREATE / ADD IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

alter table result add column if not exists source_record_id text;
alter table unit add column if not exists source_record_id text;
alter table entity_location add column if not exists country_code char(2);

create index if not exists entity_location_country on entity_location (country_code);
