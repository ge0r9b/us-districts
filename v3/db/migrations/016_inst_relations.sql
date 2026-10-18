-- member_of, area, and predecessor from data/inst-entities.
-- gov_status 'unknown', the foreign kinds, code_scheme/code, and valid_to
-- are already in 014 and 004. This file does not rewrite a table.
-- entity_feed_map stays empty: pack/entity_feed_map.csv is a content-hashed pack.
-- Feed and status stay text codes. They are not Postgres enums.

set search_path = usd, public;

alter table entity_relation drop constraint if exists entity_relation_relation_check;
alter table entity_relation add constraint entity_relation_relation_check check (
  relation in (
    'parent_org', 'owned_by', 'brand_of', 'consolidated_with', 'parent', 'in_county',
    'member_of', 'area', 'predecessor'
  )
);
