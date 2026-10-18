-- Slim institution text, keep precinct geometry out of the unit row's index,
-- and supersede rejected batches that already have a later applied sibling.
-- Idempotent. A later schema change is a new numbered file.

set search_path = usd, public;

-- v2 keys and long source notes are not on the hot entity row, and they are not indexed.
create table if not exists entity_extra (
  entity_id          text primary key references entity(entity_id) on delete cascade,
  v2_layer           text[],
  v2_key             text[],
  v2_row             text[],
  valid_from_source  text,
  inception_source   text
);

-- Attribution, source URL, and usage text. The hot entity_image row keeps the licence code and file name.
-- Deed URLs live once on license.url.
create table if not exists entity_image_text (
  image_id     bigint primary key references entity_image(id) on delete cascade,
  attribution  text,
  source_url   text,
  usage_basis  text,
  note         text
);

-- A public or hidden image still needs attribution. The loader writes it here, not on the hot row.
alter table entity_image drop constraint if exists entity_image_public_attr_check;
alter table entity_image drop constraint if exists entity_image_hidden_check;

-- Null centroids (precincts) do not take a GiST entry. Polygons stay in PMTiles.
drop index if exists unit_centroid_gist;
create index if not exists unit_centroid_gist on unit using gist (centroid) where centroid is not null;

-- 2022/2024 sldu, sldl, and school left rejected rows after a later batch applied.
update load_batch as stale
set status = 'superseded'
where stale.status = 'rejected'
  and exists (
    select 1
    from load_batch applied
    where applied.file_name = stale.file_name
      and applied.status = 'applied'
  );
