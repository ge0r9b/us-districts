"""2022 Census of Governments individual units -> local/<USPS>.csv (+ crosswalk rows, county check).

Input : cache/Govt_Units_2022_Final.xlsx (from govt_units_2022.ZIP), cache/2024_Gaz_*_national.txt
Output: local/<USPS>.csv, county_government_check.csv; returns crosswalk rows to build_all.py

GEOID rules (Geography bot conventions, TIGER 2024 vintage, strings with leading zeros):
  county        -> counties  SS+CCC       from FIPS_STATE+FIPS_COUNTY, kept only if it exists in the 2024 Gazetteer
  municipality  -> place     SS+PPPPP     from FIPS_STATE+FIPS_PLACE, kept only if it exists in the 2024 place Gazetteer;
                   a 2024 cousub with the same code in FIPS_COUNTY is added to the crosswalk (relation coextensive_cousub)
  township      -> cousub    SS+CCC+CCCCC from FIPS_STATE+FIPS_COUNTY+FIPS_PLACE, kept only if it exists in the 2024 cousub
                   Gazetteer; other county parts with the same state+code go to the crosswalk (relation county_part)
  school        -> unsd/elsd/scsd SS+LEA  only by exact normalized name match within the state, unique candidate only
  special       -> none (TIGER has no special-district layer)
Nothing is guessed: no match leaves geoid blank and geoid_match says why.
"""
import collections, os, re, openpyxl
from common import CACHE, ROOT, COLUMNS, PUBLIC_DOMAIN, meta, read_gaz, norm, write_csv, state_table

SRC = 'U.S. Census Bureau, 2022 Census of Governments: Organization, Government Units Listing (Govt_Units_2022_Final.xlsx)'
LEVEL = {'01': 'elementary', '02': 'secondary', '03': 'unified', '04': 'post_secondary',
         '05': 'special_vocational', '06': 'non_operating'}
GP_TYPE = {'1': 'county', '2': 'municipality', '3': 'township'}
DEP_ON = {'0': 'state', '1': 'county', '2': 'municipality', '3': 'township'}
SCHOOL_LAYER = {'elementary': ['elsd'], 'secondary': ['scsd'], 'unified': ['unsd'],
                'non_operating': ['unsd', 'elsd', 'scsd']}   # post-secondary / vocational units are not TIGER school districts
ABBR = {'SCH': 'SCHOOL', 'SCHS': 'SCHOOLS', 'DIST': 'DISTRICT', 'DISTS': 'DISTRICTS', 'IND': 'INDEPENDENT',
        'ISD': 'INDEPENDENT SCHOOL DISTRICT', 'UNIF': 'UNIFIED', 'ELEM': 'ELEMENTARY', 'CTL': 'CENTRAL', 'CENT': 'CENTRAL',
        'TWP': 'TOWNSHIP', 'BORO': 'BOROUGH', 'REG': 'REGIONAL', 'CONS': 'CONSOLIDATED', 'CONSOL': 'CONSOLIDATED',
        'CO': 'COUNTY', 'JT': 'JOINT', 'COMM': 'COMMUNITY', 'COMMUN': 'COMMUNITY', 'UN': 'UNION', 'HS': 'HIGH SCHOOL',
        'HI': 'HIGH', 'MT': 'MOUNT', 'ST': 'SAINT', 'FT': 'FORT', 'PK': 'PARK', 'VLY': 'VALLEY', 'SPGS': 'SPRINGS',
        'TWNSHP': 'TOWNSHIP', 'VIL': 'VILLAGE', 'EXEMP': 'EXEMPTED', 'EX': 'EXEMPTED', 'CUSD': 'COMMUNITY UNIT SCHOOL DISTRICT',
        'USD': 'UNIFIED SCHOOL DISTRICT', 'UFSD': 'UNION FREE SCHOOL DISTRICT', 'CSD': 'CENTRAL SCHOOL DISTRICT',
        'SD': 'SCHOOL DISTRICT', 'TWN': 'TOWN', 'VLG': 'VILLAGE', 'UF': 'UNION FREE', 'MUN': 'MUNICIPAL',
        'SEP': 'SEPARATE', 'NO': '', 'NUMBER': ''}
GENERIC = {'SCHOOL', 'SCHOOLS', 'DISTRICT', 'DISTRICTS', 'PUBLIC', 'INDEPENDENT', 'THE', 'OF', 'BOARD', 'EDUCATION', 'SYSTEM'}


def school_keys(name):
    """Match keys, strongest first: expanded full name, core name (generic words dropped), core without trailing number."""
    n = re.sub(r'\([^)]*\)', ' ', name or '')
    words = [w for t in norm(n).split() for w in ABBR.get(t, t).split()]
    full = ' '.join(words)
    core = ' '.join(w for w in words if w not in GENERIC)
    bare = re.sub(r'( \d+[A-Z]?)+$', '', core)
    return [('name_exact', full), ('name_core', core), ('name_core_no_number', bare)]


def sheet(wb, name):
    rows = wb[name].iter_rows(values_only=True)
    hdr = next(rows)
    for r in rows:
        if r[0] is None:
            continue
        yield {h: ('' if v is None else str(v).strip()) for h, v in zip(hdr, r)}


def build():
    m = meta('cog2022')
    st = state_table()
    base = {'source': SRC, 'source_url': m['url'], 'source_date': m['last_modified'],
            'retrieved_at': m['retrieved_at'], 'license': PUBLIC_DOMAIN}
    gaz = {g: {r['GEOID']: r for r in read_gaz(g)} for g in ('counties', 'place', 'cousubs', 'unsd', 'elsd', 'scsd')}
    cousub_by_code = collections.defaultdict(list)          # (SS, 5-digit cousub code) -> [GEOID]
    for g in gaz['cousubs']:
        cousub_by_code[(g[:2], g[5:])].append(g)
    school_by_name = collections.defaultdict(set)           # (tier, USPS, layer, key) -> {GEOID}
    for layer in ('unsd', 'elsd', 'scsd'):
        for g, r in gaz[layer].items():
            keys = school_keys(r['NAME'])
            for tier, k in keys:
                # the no-number key is only offered by TIGER names that carry no number themselves
                if tier == 'name_core_no_number' and k != keys[1][1]:
                    continue
                school_by_name[(tier, r['USPS'], layer, k)].add(g)

    wb = openpyxl.load_workbook(os.path.join(CACHE, 'Govt_Units_2022_Final.xlsx'), read_only=True)
    rows, xw = [], []

    def common(r, typ):
        ss = r['FIPS_STATE']
        usps = st[ss][0] if ss in st else r['STATE']
        cty = (ss + r['FIPS_COUNTY']) if r.get('FIPS_COUNTY') else ''
        # parent = the state government; DC has no state government, so DC units get no parent
        return dict(base, entity_id='cog:' + r['CENSUS_ID_PID6'], name=r['UNIT_NAME'], type=typ,
                    parent_id='' if ss == '11' else 'state:' + ss, state_fips=ss, state=usps, county_geoid=cty,
                    cog_id=r['CENSUS_ID_PID6'], cog_gidid=r['CENSUS_ID_GIDID'],
                    is_active=r['IS_ACTIVE'], geoid_vintage='')

    def setgeo(row, layer, geoid, how, gnis=''):
        row.update(geoid=geoid, geoid_layer=layer, geoid_vintage='2024', geoid_match=how, gnis_id=gnis)
        xw.append({'entity_id': row['entity_id'], 'unit_layer': layer, 'geoid': geoid, 'vintage': '2024',
                   'relation': 'primary', 'match': how})

    for r in sheet(wb, 'General Purpose'):
        typ = GP_TYPE[r['UNIT_TYPE'][:1]]
        row = common(r, typ)
        row.update(gov_status='independent', fips_place=r['FIPS_PLACE'])
        ss, cc, pp = r['FIPS_STATE'], r['FIPS_COUNTY'], r['FIPS_PLACE']
        if typ == 'county':
            g = ss + cc
            if g in gaz['counties']:
                setgeo(row, 'counties', g, 'fips', gaz['counties'][g]['ANSICODE'])
            else:
                row['geoid_match'] = 'not_in_tiger_2024'
        elif typ == 'municipality':
            g = ss + pp
            if g in gaz['place']:
                setgeo(row, 'place', g, 'fips', gaz['place'][g]['ANSICODE'])
                cs = ss + cc + pp
                if cs in gaz['cousubs']:
                    xw.append({'entity_id': row['entity_id'], 'unit_layer': 'cousub', 'geoid': cs, 'vintage': '2024',
                               'relation': 'coextensive_cousub', 'match': 'fips'})
                cg = ss + cc
                if cg in gaz['counties'] and gaz['counties'][cg]['NAME'].lower().endswith(' city') and \
                        norm(gaz['counties'][cg]['NAME']) == norm(gaz['place'][g]['NAME']):
                    xw.append({'entity_id': row['entity_id'], 'unit_layer': 'counties', 'geoid': cg, 'vintage': '2024',
                               'relation': 'independent_city_county_equivalent', 'match': 'fips+name'})
            elif (ss + cc + pp) in gaz['cousubs']:      # municipal government that TIGER carries as a county subdivision
                g = ss + cc + pp
                setgeo(row, 'cousub', g, 'fips', gaz['cousubs'][g]['ANSICODE'])
            else:
                row['geoid_match'] = 'not_in_tiger_2024'
        else:  # township
            g = ss + cc + pp
            parts = sorted(cousub_by_code.get((ss, pp), []))
            if g in gaz['cousubs']:
                setgeo(row, 'cousub', g, 'fips', gaz['cousubs'][g]['ANSICODE'])
                for p in parts:
                    if p != g:
                        xw.append({'entity_id': row['entity_id'], 'unit_layer': 'cousub', 'geoid': p, 'vintage': '2024',
                                   'relation': 'county_part', 'match': 'fips'})
            elif len(parts) == 1:
                setgeo(row, 'cousub', parts[0], 'fips_other_county', gaz['cousubs'][parts[0]]['ANSICODE'])
                row['note'] = 'cousub code found in county {} (CoG county area {})'.format(parts[0][2:5], cc)
            elif (ss + pp) in gaz['place']:             # township government that TIGER carries as a place
                setgeo(row, 'place', ss + pp, 'fips', gaz['place'][ss + pp]['ANSICODE'])
            else:
                row['geoid_match'] = 'not_in_tiger_2024' if not parts else 'ambiguous'
        rows.append(row)

    for r in sheet(wb, 'Special District'):
        row = common(r, 'special_district')
        fn = r['FUNCTION_NAME']
        row.update(gov_status='independent', subtype=fn.split(' - ', 1)[-1].lower() if fn else '',
                   geoid_match='no_tiger_layer')
        rows.append(row)

    def school(r, status):
        row = common(r, 'school_district')
        lvl = LEVEL.get(r['SCHOOL_LEVEL_DESCRIPTION'][:2], r['SCHOOL_LEVEL_DESCRIPTION'].lower())
        row.update(gov_status=status, subtype=lvl)
        layers = SCHOOL_LAYER.get(lvl)
        if not layers:
            row['geoid_match'] = 'no_tiger_layer'
            return row
        row['geoid_match'] = 'no_name_match'
        for tier, k in school_keys(r['UNIT_NAME']):
            cands = sorted({g for l in layers for g in school_by_name.get((tier, row['state'], l, k), ())})
            if len(cands) == 1:
                g = cands[0]
                layer = next(l for l in ('unsd', 'elsd', 'scsd') if g in gaz[l])
                setgeo(row, layer, g, tier)
                break
            if cands:
                row['geoid_match'] = 'ambiguous'
                break
        return row

    for r in sheet(wb, 'School District'):
        rows.append(school(r, 'independent'))
    for r in sheet(wb, 'DEP School Dist'):
        row = school(r, 'dependent')
        row['note'] = 'dependent school system of a {} government (CoG UNIT_TYPE {}); parent government not identified in source'.format(
            DEP_ON.get(r['UNIT_TYPE'][:1], '?'), r['UNIT_TYPE'])
        rows.append(row)

    # a GEOID may be claimed by only one entity as primary. If several units claim it, the single claim with the
    # strongest match tier keeps it; on a tie all claims are dropped (left blank, never guessed).
    rank = {'fips': 0, 'fips_other_county': 1, 'name_exact': 2, 'name_core': 3, 'name_core_no_number': 4}
    claims = collections.defaultdict(list)
    for x in xw:
        if x['relation'] == 'primary':
            claims[(x['unit_layer'], x['geoid'])].append(x)
    lose = set()
    for k, cl in claims.items():
        if len(cl) > 1:
            best = min(rank[c['match']] for c in cl)
            winners = [c for c in cl if rank[c['match']] == best]
            for c in cl:
                if len(winners) > 1 or c is not winners[0]:
                    lose.add(c['entity_id'])
    if lose:
        for row in rows:
            if row['entity_id'] in lose:
                row['note'] = (row.get('note', '') + '; ' if row.get('note') else '') + \
                    'candidate GEOID {} {} is claimed by another CoG unit; left blank'.format(row['geoid_layer'], row['geoid'])
                row.update(geoid='', geoid_layer='', geoid_vintage='', geoid_match='ambiguous', gnis_id='')
        xw = [x for x in xw if x['entity_id'] not in lose]

    rows.sort(key=lambda r: (r['state_fips'], r['type'], r['county_geoid'], r['name'], r['cog_id']))
    by_state = collections.defaultdict(list)
    for r in rows:
        by_state[r['state']].append(r)
    outdir = os.path.join(ROOT, 'local')
    for f in os.listdir(outdir) if os.path.isdir(outdir) else []:
        if f.endswith('.csv'):
            os.remove(os.path.join(outdir, f))
    counts = {}
    for usps, rs in sorted(by_state.items()):
        counts[usps] = write_csv(os.path.join(outdir, usps + '.csv'), rs, COLUMNS)

    # county government check: every 2024 TIGER county vs the CoG county governments
    cog_cty = collections.defaultdict(list)
    for r in rows:
        if r['type'] == 'county':
            cog_cty[r['county_geoid']].append(r)
    icc = collections.defaultdict(list)   # county GEOID -> entity_ids of independent-city governments
    for x in xw:
        if x['relation'] == 'independent_city_county_equivalent':
            icc[x['geoid']].append(x['entity_id'])
    chk = []
    for g, c in sorted(gaz['counties'].items()):
        hits = cog_cty.get(g, [])
        muni_here = [] if hits else icc.get(g, [])
        chk.append({'county_geoid': g, 'tiger_name': c['NAME'], 'state': c['USPS'],
                    'cog_county_government': 'yes' if hits else 'no',
                    'cog_id': ';'.join(h['cog_id'] for h in hits), 'cog_name': ';'.join(h['name'] for h in hits),
                    'note': ('county-equivalent governed by independent city ' + ';'.join(muni_here)) if muni_here else '',
                    'source': SRC + '; TIGER 2024 Gazetteer counties', 'source_date': m['last_modified']})
    for g, hits in sorted(cog_cty.items()):
        if g not in gaz['counties']:
            for h in hits:
                chk.append({'county_geoid': g, 'tiger_name': '', 'state': h['state'], 'cog_county_government': 'yes',
                            'cog_id': h['cog_id'], 'cog_name': h['name'], 'note': 'CoG county FIPS not in TIGER 2024 counties',
                            'source': SRC, 'source_date': m['last_modified']})
    write_csv(os.path.join(ROOT, 'county_government_check.csv'), chk,
              ['county_geoid', 'tiger_name', 'state', 'cog_county_government', 'cog_id', 'cog_name', 'note', 'source', 'source_date'])
    for x in xw:
        x.update(source='cog2022;gaz2024', source_date=m['last_modified'])
    return rows, xw, counts, chk
