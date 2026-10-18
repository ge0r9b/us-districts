-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 1. Tenancy + provenance
-- ---------------------------------------------------------------------------

-- Owner of a boundary set / dataset. 'public' (id 1) owns everything shipped today.
-- Paid custom boundary sets later belong to a customer tenant.
create table if not exists tenant (
  id          bigint generated always as identity primary key,
  slug        text not null unique,                 -- 'public', 'acme-campaign'
  name        text not null,
  kind        text not null default 'public' check (kind in ('public','customer','internal')),
  created_at  timestamptz not null default now()
);

create table if not exists license (
  id             bigint generated always as identity primary key,
  code           text not null unique,              -- 'CC0','CC-BY-4.0','public-record','NYT-C-UDA','ODbL','proprietary'
  name           text not null,
  url            text,
  commercial_ok  boolean,                            -- null = not verified yet (spec 9.3 'Check')
  attribution_required boolean not null default false,
  share_alike    boolean not null default false,
  non_commercial boolean not null default false      -- licence forbids commercial use (DGEQ open-data metadata)
);

-- One row per source (sources.csv; election rows mint one per distinct url + retrieved_at). Unique on source_id only.
create table if not exists source (
  source_id     text primary key,                    -- sources.csv source_id, stable '<slug>-<sha8(url|commit)>' ('census-cog2022-0fba3401')
  title         text,                                -- sources.csv 'source' (human-readable description)
  publisher     text,                                -- 'U.S. Census Bureau', 'OpenStates' (optional)
  url           text,                                -- first / primary URL; every URL (incl. this one) is in source_url
  retrieved_at  timestamptz,
  commit        text,                                -- upstream commit (congress-legislators, OpenStates) when given
  license       text,                                -- license as stated by the source, verbatim (generic provenance)
  license_id    bigint references license(id),
  non_commercial boolean not null default false,    -- no commercial use: never shown in paid features (Élections Québec data)
  attribution_required boolean not null default false,
  license_verified boolean not null default false,   -- true once the license/terms page has been read (date in license_checked_at)
  license_checked_at date,
  robots_ok     boolean,                             -- scraped lists: robots.txt and terms of service allow it (DATA_LOADING §15.3)
  attribution   text,                                -- exact credit line to display
  sha256        text,                                -- of the raw download, when the data bot records it
  notes         text
);

-- Sources with several URLs (sources.csv 'source_url' as a ' ; '-list, e.g. a legislature's House + Senate pages).
create table if not exists source_url (
  source_id   text not null references source(source_id) on delete cascade,
  ord         smallint not null,                     -- position in the ' ; '-list (1 = source.url)
  url         text not null,
  label       text,                                  -- optional ('house', 'senate', 'cousub', 'place')
  primary key (source_id, ord)
);
