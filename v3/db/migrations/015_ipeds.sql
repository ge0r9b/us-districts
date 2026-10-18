-- Allow ipeds:<UNITID> on brand, organization, company, nonprofit, and fund.
-- A later QID match re-keys through entity_merge rule ipeds_to_qid, the same way usd: does.
-- 004 already applied, so this file replaces that check. Idempotent.

set search_path = usd, public;

do $ipeds$
declare
  old_name text;
begin
  for old_name in
    select con.conname
    from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace nsp on nsp.oid = rel.relnamespace
    where nsp.nspname = 'usd'
      and rel.relname = 'entity'
      and con.contype = 'c'
      and pg_get_constraintdef(con.oid) like '%wikidata:Q%'
      and pg_get_constraintdef(con.oid) not like '%ipeds%'
      and pg_get_constraintdef(con.oid) like '%brand%'
  loop
    execute format('alter table entity drop constraint %I', old_name);
  end loop;
end
$ipeds$;

alter table entity drop constraint if exists entity_org_id_check;
alter table entity add constraint entity_org_id_check check (
  kind not in ('brand', 'organization', 'company', 'nonprofit', 'fund')
  or entity_id ~ '^(wikidata:Q[0-9]+|usd:[0-9a-f-]{36}|ipeds:[0-9]{6})$'
);
