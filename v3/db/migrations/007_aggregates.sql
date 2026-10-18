-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 6. Precomputed aggregates (instant reads)
-- ---------------------------------------------------------------------------

-- Per contest x unit: answers in one row, shares, winner, margin. Refreshed per contest
-- after a load (DATA_LOADING.md step 6). Reads never touch `result` directly.
do $mv$
begin
  if not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = current_schema()
      and c.relname = 'unit_contest_agg'
      and c.relkind = 'm'
  ) then
    execute $sql$create materialized view unit_contest_agg as
select r.contest_id,
       r.unit_id,
       u.unit_type,
       t.category,
       u.parent_unit_id,
       u.state_abbr,
       sum(r.weighted_votes)                                         as total,
       jsonb_object_agg(a.answer_key, round(r.weighted_votes, 2))    as votes,
       bool_or(r.is_estimate)                                         as is_estimate,
       (array_agg(a.answer_key order by r.weighted_votes desc))[1]    as leader_key
from result r
join answer a on a.id = r.answer_id
join unit   u on u.id = r.unit_id
join unit_type_def t on t.unit_type = u.unit_type
group by r.contest_id, r.unit_id, u.unit_type, t.category, u.parent_unit_id, u.state_abbr$sql$;
  end if;
end
$mv$;

create unique index if not exists unit_contest_agg_pk on unit_contest_agg (contest_id, unit_id);

create index if not exists unit_contest_agg_list on unit_contest_agg (contest_id, unit_type, state_abbr);

create index if not exists unit_contest_agg_cat on unit_contest_agg (contest_id, category, state_abbr);  -- one 'School districts' list

create index if not exists unit_contest_agg_parent on unit_contest_agg (contest_id, parent_unit_id);

-- Bar-list rows: one row per contest x unit x answer with share and rank, so
-- "sorted high to low" is an index range scan, not a sort.
do $mv$
begin
  if not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = current_schema()
      and c.relname = 'answer_share'
      and c.relkind = 'm'
  ) then
    execute $sql$create materialized view answer_share as
with s as (
  select r.contest_id, r.unit_id, u.unit_type, t.category, u.parent_unit_id, u.state_abbr, a.answer_key,
         r.weighted_votes as votes,
         r.weighted_votes / nullif(sum(r.weighted_votes) over (partition by r.contest_id, r.unit_id), 0) as share,
         r.is_estimate
  from result r
  join answer a on a.id = r.answer_id
  join unit   u on u.id = r.unit_id
  join unit_type_def t on t.unit_type = u.unit_type
)
select s.*,
       rank() over (partition by contest_id, category, state_abbr, answer_key
                    order by share desc nulls last) as rank_in_list
from s$sql$;
  end if;
end
$mv$;

create unique index if not exists answer_share_pk on answer_share (contest_id, unit_id, answer_key);

create index if not exists answer_share_sorted on answer_share (contest_id, category, state_abbr, answer_key, share desc nulls last);
