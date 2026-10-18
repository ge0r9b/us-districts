-- Precinct rollups. Idempotent.
-- Precinct result rows and polygons stay out of Postgres. This table is the sum of
-- placed precinct packs under a parent unit. It is not an official county or district total.

set search_path = usd, public;

create table if not exists precinct_rollup (
  contest_key    text not null,
  parent_unit_id bigint not null references unit(id) on delete cascade,
  votes_d        bigint not null,
  votes_r        bigint not null,
  votes_o        bigint not null,
  total_votes    bigint not null,
  precincts      int not null,
  primary key (contest_key, parent_unit_id)
);
