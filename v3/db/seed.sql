-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

-- Reference rows only. Safe to re-run: every insert uses ON CONFLICT DO NOTHING.
-- The public tenant insert does not override identity, so the first apply still gets id 1.
set search_path = usd, public;

-- id 1 is the default owner_tenant_id. This insert has to run before any boundary_set row.
insert into tenant (slug, name, kind) values ('public', 'Public', 'public')
on conflict (slug) do nothing;

-- Canadian licences (data/inst-canada b4dc491 sources_ca.csv, CANADA_SCHEMA_PROPOSALS.md item 9).
insert into license (code, name, url, commercial_ok, attribution_required, non_commercial) values
  ('OGL-CA',         'Open Government Licence - Canada', 'https://open.canada.ca/en/open-government-licence-canada', true, true, false),
  ('OGL-NB',         'Open Government Licence - New Brunswick', null, true, true, false),
  ('StatCan-OL',     'Statistics Canada Open Licence', 'https://www.statcan.gc.ca/en/terms-conditions/open-licence', true, true, false),
  ('EO-OUDPL',       'Elections Ontario Open Use Data Product Licence', null, true, true, false),
  ('DGEQ-OD',        'Licence d''utilisation des données ouvertes du DGEQ (Élections Québec)', null, false, true, true),
  ('EBC-OD',         'Elections BC Open Data Licence', null, true, true, false),
  ('PEI-OD',         'Government of Prince Edward Island open data', null, null, true, false),
  ('not-stated',     'No licence stated on the agency download page (AB, MB, SK, NL)', null, null, true, false),
  ('HoC-website',    'House of Commons website (no reuse grant; factual fields only)', 'https://www.ourcommons.ca', null, true, false),
  ('ca-public-record','Official legislature website (public record; factual fields only)', null, null, true, false),
  ('ca-federal-law', 'Reproduction of Federal Law Order (SI/97-5)', 'https://laws-lois.justice.gc.ca/eng/const/page-1.html', true, true, false)
on conflict (code) do nothing;

insert into unit_category (category, label) values
  ('country','Countries'), ('state','States'), ('county','Counties'), ('town','Towns'), ('place','Places'),
  ('precinct','Precincts'), ('congressional','US House districts'), ('legislative_upper','State senate districts'),
  ('legislative_lower','State house districts'), ('school_district','School districts'), ('ward','Wards'), ('custom','Custom'), ('seat','Seats without a district'),
  ('federal_district','Federal electoral districts (Canada)'), ('provincial_district','Provincial electoral districts (Canada)')
on conflict (category) do nothing;

insert into unit_type_def (unit_type, category, label, tiger_set) values
  ('country','country','Country',null), ('state','state','State','state'), ('county','county','County','county'),
  ('county_subdivision','town','Town / township','cousub'), ('place','place','Place','place'),
  ('precinct','precinct','Precinct',null), ('ushouse','congressional','US House district','cd'),
  ('sldu','legislative_upper','State senate district','sldu'), ('sldl','legislative_lower','State house district','sldl'),
  ('school_unified','school_district','Unified school district','unsd'),
  ('school_elementary','school_district','Elementary school district','elsd'),
  ('school_secondary','school_district','Secondary school district','scsd'),
  ('ward','ward','Ward',null), ('custom','custom','Custom area',null),
  ('seat','seat','Seat without a district polygon',null),   -- NH floterials, ME tribal seats, House delegates of territories
  -- Canada (prefixed ca_; the inst-canada files say fed/poll/ped/ppoll/cd/csd and the loader maps them)
  ('ca_fed','federal_district','Federal electoral district (Canada)',null),            -- key FED_NUM ('35075')
  ('ca_poll','precinct','Federal polling division (Canada)',null),                     -- '<FED_NUM>:<PD_NUM>-<SFX>' ('10001:78-0')
  ('ca_ped','provincial_district','Provincial / territorial electoral district',null), -- agency code (ON ED_ID, QC CO_CEP, BC 'ABM')
  ('ca_ppoll','precinct','Provincial polling division / voting area / section de vote',null),  -- '<district key>:<poll code>'
  ('ca_cd','county','Census division (Canada)',null),                                  -- StatCan CDUID
  ('ca_csd','town','Census subdivision (Canada)',null)
on conflict (unit_type) do nothing;                                -- StatCan CSDUID

-- Agreed registry (Election + Institutions, Oct 18, 2026). Units are loaded per (slug, unit_type).
insert into boundary_set (slug, unit_type, vintage_year, is_current)
select v.slug, t.unit_type, v.yr, v.cur
from (values ('v2-2024', 2024, true), ('tiger-2020-cd116', 2020, false), ('tiger-2020-sldu', 2020, false),
             ('tiger-2020-sldl', 2020, false), ('tiger-2020-county', 2020, false)) as v(slug, yr, cur)
join unit_type_def t on
     (v.slug = 'v2-2024'           and t.unit_type in ('state','county','county_subdivision','place','precinct','ushouse','sldu','sldl',
                                                       'school_unified','school_elementary','school_secondary','ward','seat'))
  or (v.slug = 'tiger-2020-cd116'  and t.unit_type in ('ushouse','seat'))
  or (v.slug = 'tiger-2020-sldu'   and t.unit_type = 'sldu')
  or (v.slug = 'tiger-2020-sldl'   and t.unit_type = 'sldl')
  or (v.slug = 'tiger-2020-county' and t.unit_type = 'county')
on conflict (slug, unit_type) do nothing;   -- the 8 old CT counties (09001 ... 09015)

-- Canada (b4dc491): 24 sets, slug pattern '<agency>-<boundary year>-<set>'.
insert into boundary_set (slug, unit_type, country, province, vintage_year, is_current) values
  ('ec-2023-fed','ca_fed','ca',null,2023,true),   ('ec-2013-fed','ca_fed','ca',null,2013,false),
  ('ec-2025-pd','ca_poll','ca',null,2025,true),   ('ec-2021-pd','ca_poll','ca',null,2021,false), ('ec-2019-pd','ca_poll','ca',null,2019,false),
  ('eo-2022-ed','ca_ped','ca','ON',2022,true),
  ('eq-2026-ced','ca_ped','ca','QC',2026,true),   ('eq-2026-sv','ca_ppoll','ca','QC',2026,true),
  ('ebc-2023-ed','ca_ped','ca','BC',2023,true),   ('ebc-2024-va','ca_ppoll','ca','BC',2024,true),
  ('ea-2019-ed','ca_ped','ca','AB',2019,true),    ('ea-2026-va','ca_ppoll','ca','AB',2026,true),
  ('em-2018-ed','ca_ped','ca','MB',2018,true),    ('em-2023-va','ca_ppoll','ca','MB',2023,true),
  ('esk-2022-ed','ca_ped','ca','SK',2022,true),   ('esk-2024-va','ca_ppoll','ca','SK',2024,true),
  ('enb-2024-ed','ca_ped','ca','NB',2024,true),   ('enb-2024-pd','ca_ppoll','ca','NB',2024,true),
  ('epei-2017-ed','ca_ped','ca','PE',2017,true),  ('epei-2017-poll','ca_ppoll','ca','PE',2017,true),  -- vintage not stated by the source
  ('enl-2015-ed','ca_ped','ca','NL',2015,true),   ('enl-2019-poll','ca_ppoll','ca','NL',2019,false), -- maybe superseded
  ('statcan-2021-cd','ca_cd','ca',null,2021,true), ('statcan-2021-csd','ca_csd','ca',null,2021,true)
on conflict (slug, unit_type) do nothing;

insert into data_version (id, dv) values (1, 1)
on conflict (id) do nothing;
