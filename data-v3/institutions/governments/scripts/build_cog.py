"""2022 Census of Governments individual units -> local/<USPS>.csv (+ crosswalk rows, county check).

Input : cache/Govt_Units_2022_Final.xlsx (from govt_units_2022.ZIP), cache/2024_Gaz_*_national.txt
Output: local/<USPS>.csv, county_government_check.csv; returns crosswalk rows to build_all.py

GEOID rules (Geography bot conventions, TIGER 2024 vintage, strings with leading zeros):
  county        -> counties  SS+CCC from FIPS_STATE+FIPS_COUNTY, kept only if it exists in the 2024 Gazetteer
  municipality  -> place     SS+PPPPP if in the 2024 place Gazetteer (+ coextensive cousub / independent-city county /
                   consolidated city-county in the crosswalk). CoG codes that are TIGER CONCITY codes take the
                   '(balance)' place (county + CONCITY in the crosswalk); 'CITY AND COUNTY OF X'
                   without a place takes county X (Honolulu).
  township      -> cousub    SS+CCC+CCCCC if in the 2024 cousub Gazetteer (other county parts -> county_part); else the
                   same code once elsewhere in the state (fips_other_county)
  not in 2024   -> the code in the 2022, then 2020 Gazetteer; followed into 2024 by ANSI code (ansi_via_YYYY), else
                   a labeled name fallback in 2024 (fallback_name_2024), else the old GEOID carried with
                   geoid_vintage=YYYY and tiger_status=absent_2024 (fips_YYYY)
  school        -> code join CoG PID6 = F-33 PID6 -> NCESID (= NCES LEAID = TIGER unsd/elsd/scsd GEOID); name matching
                   is only a labeled fallback (fallback_name_*) for units absent from the F-33 files
  special       -> none (TIGER has no special-district layer)
Nothing is guessed: no match leaves geoid blank and geoid_match says why.
"""
import collections, os, re, openpyxl
from common import (CACHE, ROOT, COLUMNS, PUBLIC_DOMAIN, CONCITY_STATES, F33_YEARS, meta, read_gaz, read_dbf, norm,
                    write_csv, state_table)
import csv

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
# CONCITY GEOIDs whose government takes the county GEOID as primary instead of the '(balance)' place.
CONSOLIDATED_COUNTY_PRIMARY = set()   # Greeley County KS moved to its balance place (Geography bot, Oct 18, 2026)
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


def build(reg):
    m = meta('cog2022')
    st = state_table()
    base = {'source': 'cog2022', 'source_url': '', 'source_date': m['last_modified'],
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

    # TIGER 2024 consolidated cities and their '(balance)' places
    concity, balance = {}, {}
    for ss in CONCITY_STATES:
        for c in read_dbf(os.path.join(CACHE, 'tl_2024_{}_concity.dbf'.format(ss))):
            concity[c['GEOID']] = c
            want = c['NAMELSAD'] + ' (balance)'
            hits = [g for g, p in gaz['place'].items() if g[:2] == ss and p['NAME'] == want]
            if len(hits) == 1:
                balance[c['GEOID']] = hits[0]
    concity_of_balance = {b: c for c, b in balance.items()}
    # earlier vintages (2022, 2020) for units missing from TIGER 2024, linked forward by ANSI (GNIS) code
    prior = {y: {g: {r['GEOID']: r for r in read_gaz(g, y)} for g in ('place', 'cousubs')} for y in ('2022', '2020')}
    prior_cbc = {y: collections.defaultdict(list) for y in prior}
    for y in prior:
        for g in prior[y]['cousubs']:
            prior_cbc[y][(g[:2], g[5:])].append(g)
    ansi24 = {g: {r['ANSICODE']: k for k, r in gaz[g].items()} for g in ('place', 'cousubs')}
    # F-33 school finance unit files: PID6 -> (fiscal year, NCESID), newest file first
    f33 = {}
    for y in F33_YEARS:
        with open(os.path.join(CACHE, 'elsec{}.txt'.format(y[2:])), encoding='latin-1', newline='') as f:
            for r in csv.DictReader(f):
                pid, nces = r['PID6'].strip(), r['NCESID'].strip()
                if pid and pid not in f33:
                    f33[pid] = (y, nces)
    school_layer_of = {g: l for l in ('unsd', 'elsd', 'scsd') for g in gaz[l]}
    unsd_by_name = collections.defaultdict(list)
    for g, r0 in gaz['unsd'].items():
        unsd_by_name[(g[:2], r0['NAME'])].append(g)
    secondary_of = {}                                   # unsd GEOID -> (scsd GEOID, grades) for 'X (9-12)' areas
    # pairs confirmed by the Geography bot where the unsd name is not unique in the state (Oct 18, 2026)
    SECONDARY_PAIRS = {'0601415': '0606018'}            # Washington Unified SD (Fresno Co.) CA -> its (9-12) area
    for u, sc in SECONDARY_PAIRS.items():
        mm = re.match(r'^(.*) \((\d+)-(\d+)\)$', gaz['scsd'][sc]['NAME'])
        assert mm and mm.group(1) == gaz['unsd'][u]['NAME'], (u, sc)
        secondary_of[u] = (sc, '{}_{}'.format(mm.group(2), mm.group(3)))
    for g, r0 in gaz['scsd'].items():
        mm = re.match(r'^(.*) \((\d+)-(\d+)\)$', r0['NAME'])
        if mm and len(unsd_by_name.get((g[:2], mm.group(1)), [])) == 1 and unsd_by_name[(g[:2], mm.group(1))][0] not in secondary_of:
            secondary_of[unsd_by_name[(g[:2], mm.group(1))][0]] = (g, '{}_{}'.format(mm.group(2), mm.group(3)))

    wb = openpyxl.load_workbook(os.path.join(CACHE, 'Govt_Units_2022_Final.xlsx'), read_only=True)
    rows, xw = [], []

    def common(r, typ):
        ss = r['FIPS_STATE']
        usps = st[ss][0] if ss in st else r['STATE']
        cty = (ss + r['FIPS_COUNTY']) if r.get('FIPS_COUNTY') else ''
        # parent = the state government; DC has no state government, so DC units get no parent
        eid = reg.get(['cog_pid6:' + r['CENSUS_ID_PID6']], 'cog:' + r['CENSUS_ID_PID6'], m['retrieved_at'][:10])
        return dict(base, entity_id=eid, name=r['UNIT_NAME'], type=typ,
                    parent_id='' if ss == '11' else 'state:' + ss, state_fips=ss, state=usps, county_geoid=cty,
                    cog_id=r['CENSUS_ID_PID6'], cog_gidid=r['CENSUS_ID_GIDID'],
                    is_active=r['IS_ACTIVE'], geoid_vintage='')

    def setgeo(row, layer, geoid, how, gnis='', vintage='2024'):
        row.update(geoid=geoid, geoid_layer=layer, geoid_vintage=vintage, geoid_match=how, gnis_id=gnis,
                   tiger_status='current_2024' if vintage == '2024' else 'absent_2024')
        xw.append({'entity_id': row['entity_id'], 'unit_layer': layer, 'geoid': geoid, 'vintage': vintage,
                   'relation': 'primary', 'match': how})

    def addx(row, layer, geoid, relation, how, vintage='2024'):
        xw.append({'entity_id': row['entity_id'], 'unit_layer': layer, 'geoid': geoid, 'vintage': vintage,
                   'relation': relation, 'match': how})

    def addnote(row, text):
        row['note'] = (row['note'] + '; ' if row.get('note') else '') + text

    # labeled fallback for general-purpose units whose CoG code is in no TIGER vintage, or only as a predecessor:
    # same state (and same county for cousubs), same core name, compatible kind, exactly one candidate in TIGER 2024
    KIND_PREFIX = ('CHARTER TOWNSHIP OF ', 'TOWNSHIP OF ', 'TOWN OF ', 'CITY OF ', 'VILLAGE OF ', 'BOROUGH OF ',
                   'PLANTATION OF ', 'METRO GOVERNMENT OF ', 'UNIFIED GOVERNMENT OF ')
    TOWN_KINDS = {'town', 'township', 'plantation', 'town city'}

    def tiger_core(name):
        n = re.sub(r'^(Town|Village|City) of ', '', name)
        core, _, kind = n.rpartition(' ')
        if kind == 'city' and core.endswith(' Town'):
            core, kind = core[:-5], 'town city'
        return norm(core), kind

    name_index = collections.defaultdict(list)          # (layer, SS, core) -> [(GEOID, kind)]
    for lay in ('place', 'cousubs'):
        for g, p in gaz[lay].items():
            core, kind = tiger_core(p['NAME'])
            if kind not in ('CDP', 'CCD', 'UT', 'area', 'district', 'precinct', 'reservation'):
                name_index[(lay, g[:2], core)].append((g, kind))

    def name_fallback(row, typ, r, ss, cc):
        n = r['UNIT_NAME']
        pre = next((p for p in KIND_PREFIX if n.startswith(p)), '')
        core = norm(n[len(pre):])
        cores = {core} | {core[:-len(sfx)] for sfx in (' TOWN', ' CITY') if core.endswith(sfx)}
        lay = 'place' if typ == 'municipality' else 'cousubs'
        cands = set()
        for c in cores:
            for g, kind in name_index.get((lay, ss, c), []):
                if typ == 'township' and (kind not in TOWN_KINDS or g[2:5] != cc):
                    continue
                if typ == 'municipality' and kind in ('town', 'township', 'plantation') and pre == 'TOWNSHIP OF ':
                    continue
                cands.add(g)
        if len(cands) == 1:
            g = cands.pop()
            L = 'place' if lay == 'place' else 'cousub'
            setgeo(row, L, g, 'fallback_name_2024', gaz[lay][g]['ANSICODE'])
            addnote(row, 'CoG code {} not usable; matched by name to TIGER 2024 "{}" (same state{}, unique)'.format(
                r['FIPS_PLACE'], gaz[lay][g]['NAME'], ' and county' if L == 'cousub' else ''))
            return True
        return False

    def prior_vintage(row, typ, ss, cc, pp, r):
        """Unit not in TIGER 2024: find its code in the 2022, then 2020 Gazetteer; follow the ANSI code into 2024."""
        order = ('place', 'cousubs') if typ == 'municipality' else ('cousubs', 'place')
        for y in ('2022', '2020'):
            for lay in order:
                if lay == 'place':
                    g = ss + pp
                else:
                    g = ss + cc + pp
                    if g not in prior[y]['cousubs'] and len(prior_cbc[y].get((ss, pp), [])) == 1:
                        g = prior_cbc[y][(ss, pp)][0]
                rec = prior[y][lay].get(g)
                if not rec:
                    continue
                L = 'place' if lay == 'place' else 'cousub'
                new = ansi24[lay].get(rec['ANSICODE'])
                if new:
                    setgeo(row, L, new, 'ansi_via_' + y, rec['ANSICODE'])
                    addx(row, L, g, 'prior_vintage_code', 'fips', y)
                    addnote(row, 'code {} ({} "{}") changed to {} "{}" in TIGER 2024 (same ANSI code {})'.format(
                        pp, y, rec['NAME'], new, gaz[lay][new]['NAME'], rec['ANSICODE']))
                elif name_fallback(row, typ, r, ss, cc):
                    addx(row, L, g, 'predecessor_code', 'fips', y)
                    addnote(row, 'CoG code {} is {} "{}" in the {} Gazetteer'.format(pp, g, rec['NAME'], y))
                else:
                    setgeo(row, L, g, 'fips_' + y, rec['ANSICODE'], vintage=y)
                    addnote(row, 'not in TIGER 2024 (dissolved, merged or re-coded after {}); GEOID from the {} Gazetteer "{}"'.format(
                        y, y, rec['NAME']))
                return
        if not name_fallback(row, typ, r, ss, cc):
            row['geoid_match'] = 'not_in_tiger_2020_2024'
            addnote(row, 'CoG FIPS_PLACE {} equals no TIGER 2020/2022/2024 place or cousub code in the state and no unique '
                         'same-name feature exists; left blank (code-only rule, Geography bot Oct 18, 2026)'.format(pp))

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
            cg = ss + cc
            if g in concity:            # CoG code = TIGER consolidated-city code
                c, bal = concity[g], balance.get(g)
                if g in CONSOLIDATED_COUNTY_PRIMARY and cg in gaz['counties']:
                    setgeo(row, 'counties', cg, 'concity_county', gaz['counties'][cg]['ANSICODE'])
                    if bal:
                        addx(row, 'place', bal, 'balance_place', 'concity_name')
                elif bal:
                    setgeo(row, 'place', bal, 'concity_balance', gaz['place'][bal]['ANSICODE'])
                    if cg in gaz['counties']:
                        addx(row, 'counties', cg, 'consolidated_city_county', 'fips')
                else:
                    row['geoid_match'] = 'ambiguous'
                addx(row, 'concity', g, 'consolidated_city', 'fips')
                addnote(row, 'TIGER 2024 consolidated city {} "{}"'.format(g, c['NAMELSAD']))
            elif r['UNIT_NAME'].startswith('CITY AND COUNTY OF ') and cg in gaz['counties'] and \
                    norm(gaz['counties'][cg]['NAME']).startswith(norm(r['UNIT_NAME'][19:]) + ' ') and g not in gaz['place']:
                setgeo(row, 'counties', cg, 'city_and_county_name', gaz['counties'][cg]['ANSICODE'])
                addnote(row, 'CoG place code {} not in TIGER 2024; consolidated city-county mapped to county {}'.format(pp, cg))
            elif g in gaz['place']:
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
                if r['UNIT_NAME'].startswith('CITY AND COUNTY OF ') and cg in gaz['counties'] and \
                        norm(gaz['counties'][cg]['NAME']).startswith(norm(r['UNIT_NAME'][19:]) + ' '):
                    addx(row, 'counties', cg, 'consolidated_city_county', 'fips+name')
                if g in concity_of_balance:       # CoG already uses the balance code (Augusta, Indianapolis, Milford CT)
                    c = concity_of_balance[g]
                    addx(row, 'concity', c, 'consolidated_city', 'concity_name')
                    if cg in gaz['counties'] and 'Planning Region' not in gaz['counties'][cg]['NAME']:
                        addx(row, 'counties', cg, 'consolidated_city_county', 'fips')
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
                cn = gaz['counties'].get(parts[0][:5], {}).get('NAME', '')
                row['note'] = ('cousub code found only in county {} {} (CoG county area {}{}); the CoG county code looks like '
                               'a coding slip (Geography bot review, Oct 18, 2026)').format(parts[0][:5], cn, ss, cc)
            elif (ss + pp) in gaz['place']:             # township government that TIGER carries as a place
                setgeo(row, 'place', ss + pp, 'fips', gaz['place'][ss + pp]['ANSICODE'])
            else:
                row['geoid_match'] = 'not_in_tiger_2024' if not parts else 'ambiguous'
        if row.get('geoid_match') == 'not_in_tiger_2024' and typ in ('municipality', 'township'):
            prior_vintage(row, typ, ss, cc, pp, r)
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
        hit = f33.get(r['CENSUS_ID_PID6'])
        if hit and hit[1]:              # code join: CoG PID6 = F-33 PID6 -> NCESID (= NCES LEAID = TIGER school GEOID)
            y, nces = hit
            row['nces_leaid'] = nces
            if nces in school_layer_of:
                setgeo(row, school_layer_of[nces], nces, 'f33_ncesid_' + y)
                # TIGER splits some unified LEAs into a unified area and a separate 'NAME (9-12)' secondary area
                if school_layer_of[nces] == 'unsd':
                    sec = secondary_of.get(nces)
                    if sec:
                        addx(row, 'scsd', sec[0], 'secondary_' + sec[1], 'tiger_name')
            else:
                row['geoid_match'] = 'f33_ncesid_not_in_tiger_2024'
            return row
        layers = SCHOOL_LAYER.get(lvl)
        if not layers:
            row['geoid_match'] = 'no_tiger_layer'
            return row
        row['geoid_match'] = 'no_name_match'
        for tier, k in school_keys(r['UNIT_NAME']):     # fallback only: unit absent from the F-33 files
            cands = sorted({g for l in layers for g in school_by_name.get((tier, row['state'], l, k), ())})
            if len(cands) == 1:
                g = cands[0]
                layer = next(l for l in ('unsd', 'elsd', 'scsd') if g in gaz[l])
                setgeo(row, layer, g, 'fallback_' + tier)
                break
            if cands:
                row['geoid_match'] = 'ambiguous'
                break
        return row

    for r in sheet(wb, 'School District'):
        rows.append(school(r, 'independent'))
    for r in sheet(wb, 'DEP School Dist'):
        row = school(r, 'dependent')
        row['flags'] = 'owner_unknown'
        row['note'] = 'dependent school system of a {} government (CoG UNIT_TYPE {}); parent government not identified in source'.format(
            DEP_ON.get(r['UNIT_TYPE'][:1], '?'), r['UNIT_TYPE'])
        rows.append(row)

    # a GEOID may be claimed by only one entity as primary. If several units claim it, the single claim with the
    # strongest match tier keeps it; on a tie all claims are dropped (left blank, never guessed).
    rank = {'fips_other_county': 1, 'city_and_county_name': 1, 'fallback_name_2024': 2, 'fallback_name_exact': 2, 'fallback_name_core': 3,
            'fallback_name_core_no_number': 4}
    claims = collections.defaultdict(list)
    for x in xw:
        if x['relation'] == 'primary':
            claims[(x['unit_layer'], x['geoid'], x['vintage'])].append(x)
    lose = set()
    for k, cl in claims.items():
        if len(cl) > 1:
            best = min(rank.get(c['match'], 0) for c in cl)
            winners = [c for c in cl if rank.get(c['match'], 0) == best]
            for c in cl:
                if len(winners) > 1 or c is not winners[0]:
                    lose.add(c['entity_id'])
    if lose:
        for row in rows:
            if row['entity_id'] in lose:
                row['note'] = (row.get('note', '') + '; ' if row.get('note') else '') + \
                    'candidate GEOID {} {} is claimed by another CoG unit; left blank'.format(row['geoid_layer'], row['geoid'])
                row.update(geoid='', geoid_layer='', geoid_vintage='', geoid_match='ambiguous', gnis_id='', tiger_status='')
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
