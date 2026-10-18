"""Rebuild every CSV in data-v3/institutions/governments from the cached sources.

    python3 scripts/fetch_sources.py           # download into cache/ (skips cached files; --refresh to re-download)
    python3 scripts/build_all.py               # write the CSVs + summary.json (deterministic for a given cache)
"""
import re, collections, json, os
import build_cog, build_states, build_federal_agencies, build_tribes, build_changes
from build_changes import CHANGE_COLUMNS
import wikidata, build_images, build_foreign
import build_foreign_gb
COUNTRY_BUILDS = [('gb', build_foreign_gb)]   # foreign/<cc>/: every government level of one country
from common import CACHE, ROOT, COLUMNS, XWALK_COLUMNS, EXTERNAL_IDS, SOURCE_TABLE, LICENSES, PUBLIC_DOMAIN, Registry, write_csv, manifest, meta


def sources_summary(man):
    """Named downloads in full; hash-keyed API batch caches (e.g. wd_p590_<16 hex>) as one entry per prefix, so the
    summary stays small. The full per-request list is cache/manifest.json (not in git)."""
    out, api = {}, collections.defaultdict(list)
    for k, v in sorted(man.items()):
        m = re.match(r'^(.*)_[0-9a-f]{16}(\.json)?$', k)
        if m:
            api[m.group(1)].append(v)
        else:
            out[k] = {kk: v[kk] for kk in ('url', 'last_modified', 'retrieved_at')}
    for p, vs in sorted(api.items()):
        out[p + '_*'] = {'api_requests': len(vs), 'host': vs[0]['url'].split('/')[2],
                         'retrieved_at_min': min(v['retrieved_at'] for v in vs), 'retrieved_at_max': max(v['retrieved_at'] for v in vs)}
    return out


def main():
    reg = Registry()
    states, xs = build_states.build(reg)
    local, xl, chk = build_cog.build(reg)
    fed = build_federal_agencies.build(reg)
    tribes, xt, n_lines = build_tribes.build(reg)
    # geoid provenance: add the TIGER / F-33 source code to rows whose geoid came from it
    geo_src = [('f33_ncesid_', None), ('ansi_via_2022', 'gaz2022;gaz2024'), ('ansi_via_2020', 'gaz2020;gaz2024'),
               ('fips_2022', 'gaz2022'), ('fips_2020', 'gaz2020'), ('concity', 'concity2024;gaz2024')]
    for r in local:
        g = r.get('geoid_match', '')
        if not r.get('geoid'):
            continue
        add = next((v if v else 'f33_' + g.rsplit('_', 1)[-1] + ';gaz2024' for p, v in geo_src if g.startswith(p)), 'gaz2024')
        r['source'] = r['source'] + ';' + add
    # changes after the CoG 2022 snapshot (Census GCN + cited state sources): new rows, ceased units, renames
    new_rows, changes, change_src = build_changes.build(reg, local)
    for r in new_rows:
        if r['geoid']:
            xl.append({'entity_id': r['entity_id'], 'unit_layer': r['geoid_layer'], 'geoid': r['geoid'], 'vintage': r['geoid_vintage'],
                       'relation': 'primary', 'match': r['geoid_match']})
    lost = {r['entity_id'] for r in local if r['geoid_match'] == 'ceased_geoid_to_successor'}
    xl = [x for x in xl if not (x['entity_id'] in lost and x['relation'] == 'primary')]
    local = local + new_rows
    # Wikidata QIDs from exact identifier links, then seal / flag image records (part D)
    qid_stats, terr = wikidata.assign_qids(states, local)
    fr_json = json.load(open(os.path.join(CACHE, 'fr_agencies.json'), encoding='utf-8'))
    qid_stats.update({'federal_agency|' + k: v for k, v in wikidata.agency_qids(fed, fr_json).items()})
    images, img_gaps, img_stats = build_images.build(states, local, tribes, fed, terr, fr_json)
    # foreign nations, dependencies and first-level subdivisions (foreign/), their flags and seals
    foreign, f_images, f_gaps, f_stats = build_foreign.build(reg)
    country_rows, country_stats, country_files = [], {}, {}
    for cc, mod in COUNTRY_BUILDS:
        rs, st, fs = mod.build(reg)
        country_rows += rs
        country_stats[cc] = st
        country_files[cc] = fs
    images = sorted(images + f_images, key=lambda r: (r['entity_id'], r['image_kind']))
    img_gaps = img_gaps + [g for g in f_gaps if g['entity_id']]
    write_csv(os.path.join(ROOT, 'images.csv'), images, build_images.IMAGE_COLUMNS)
    write_csv(os.path.join(ROOT, 'images_gaps.csv'), img_gaps, build_images.GAP_COLUMNS)
    per_state = build_cog.write_local(local)
    write_csv(os.path.join(ROOT, 'changes_since_cog2022.csv'), changes, CHANGE_COLUMNS)
    src_of = {r['entity_id']: r['source'] for r in local}
    for x in xl:                         # crosswalk rows carry the same geoid provenance as their entity
        if x['entity_id'] in src_of:
            x['source'] = src_of[x['entity_id']]
    n_reg = reg.save()
    used = {s for r in states + local + fed + tribes + foreign + country_rows for s in r['source'].split(';')} | \
           {s for x in xs + xl + xt for s in x['source'].split(';')}
    src_rows = []
    for sid in sorted(SOURCE_TABLE):
        desc, url, keys = SOURCE_TABLE[sid]
        man = manifest()
        ra = sorted(v['retrieved_at'] for k, v in man.items() if k in keys or any(x.endswith('*') and k.startswith(x[:-1]) for x in keys))
        src_rows.append({'source_id': sid, 'source': desc, 'source_url': url, 'license': LICENSES.get(sid, PUBLIC_DOMAIN),
                         'retrieved_at': ra[-1] if ra else '', 'commit': ''})
    src_rows += change_src
    for sid in sorted(used - set(SOURCE_TABLE) - {r['source_id'] for r in change_src}):
        if sid.startswith('bia_'):
            bm = meta('bia_notice')
            import json as _j
            bl = _j.load(open(os.path.join(ROOT, 'cache', 'bia_latest.json')))
            src_rows.append({'source_id': sid, 'source': 'Bureau of Indian Affairs, Federal Register {} ({}), {}: "{}"'.format(
                bl['document_number'], bl['publication_date'], bl['citation'], bl['title']), 'source_url': bl['html_url'],
                'license': PUBLIC_DOMAIN, 'retrieved_at': bm['retrieved_at'], 'commit': ''})
    missing = used - {r['source_id'] for r in src_rows}
    assert not missing, 'source codes without a sources.csv row: {}'.format(missing)
    write_csv(os.path.join(ROOT, 'sources.csv'), src_rows, ['source_id', 'source', 'source_url', 'license', 'retrieved_at', 'commit'])
    out = {}
    out['states.csv'] = write_csv(os.path.join(ROOT, 'states.csv'), states, COLUMNS)
    out['federal_agencies.csv'] = write_csv(os.path.join(ROOT, 'federal_agencies.csv'), fed, COLUMNS)
    out['tribes.csv'] = write_csv(os.path.join(ROOT, 'tribes.csv'), tribes, COLUMNS)
    xw = sorted(xs + xl + xt, key=lambda x: (x['entity_id'], x['relation'] != 'primary', x['unit_layer'], x['geoid']))
    out['governments_geoid_xwalk.csv'] = write_csv(os.path.join(ROOT, 'governments_geoid_xwalk.csv'), xw, XWALK_COLUMNS)
    out['county_government_check.csv'] = len(chk)
    out['id_registry.csv'] = n_reg
    out['sources.csv'] = len(src_rows)
    out['changes_since_cog2022.csv'] = len(changes)
    out['images.csv'] = len(images)
    out['images_gaps.csv'] = len(img_gaps)
    for k, v in per_state.items():
        out['local/{}.csv'.format(k)] = v
    ids = [r['entity_id'] for r in states + local + fed + tribes]
    assert len(ids) == len(set(ids)), 'duplicate entity_id'
    known = set(ids) | EXTERNAL_IDS
    known |= {r['entity_id'] for r in foreign + country_rows}
    dangling = sorted({r['parent_id'] for r in states + local + fed + tribes + foreign + country_rows if r['parent_id'] and r['parent_id'] not in known})
    dup = [e for e, n in collections.Counter(ids + [r['entity_id'] for r in foreign + country_rows]).items() if n > 1]
    assert not dup, 'entity_id in more than one row: {}'.format(dup[:10])
    # verification of school GEOIDs against the Geography bot's v2 school table (data-v3/geo/schools.csv), if present
    geo_schools = os.path.join(ROOT, '..', '..', 'geo', 'schools.csv')
    school_check = {}
    if os.path.exists(geo_schools):
        import csv
        gs = {r['geoid'] for r in csv.DictReader(open(geo_schools, encoding='utf-8')) if r['geoid']}
        ng = {r['geoid'] for r in local if r['type'] == 'school_district' and r.get('geoid')}
        school_check = {'entity_geoids': len(ng), 'found_in_geo_schools_csv': len(ng & gs),
                        'geo_schools_csv_geoids': len(gs), 'geo_schools_csv_geoids_without_cog_entity': len(gs - ng)}
    summary = {
        'files': out,
        'rows_total_entities': len(ids),
        'cog_by_type': dict(sorted(collections.Counter(r['type'] for r in local).items())),
        'cog_by_type_gov_status': {'{}|{}'.format(*k): v for k, v in sorted(collections.Counter((r['type'], r['gov_status']) for r in local).items())},
        'geoid_match': {'{}|{}'.format(*k): v for k, v in sorted(collections.Counter((r['type'], r['geoid_match']) for r in local + tribes).items())},
        'tiger_counties_without_cog_county_government': sum(1 for c in chk if c['cog_county_government'] == 'no'),
        'bia_list_lines': n_lines,
        'changes_since_cog2022': {'{}|{}'.format(*k): v for k, v in sorted(collections.Counter((c['change_type'], c['source_id']) for c in changes).items())},
        'wikidata_qid_assignment': dict(sorted(qid_stats.items())),
        'foreign': dict(sorted(f_stats.items())),
        'foreign_country_units': country_stats,
        'foreign_country_files': country_files,
        'foreign_not_built': [g['reason'] for g in f_gaps if not g['entity_id']],
        'images_by_kind_and_entity_type': dict(sorted(img_stats.items())),
        'foreign_images_by_kind_and_type': {k: v for k, v in sorted(f_stats.items()) if k.startswith(('flag|', 'seal|'))},
        'images_by_license': dict(sorted(collections.Counter(r['license'] for r in images).items())),
        'image_gaps_by_reason': dict(sorted(collections.Counter('{}|{}'.format(g['image_kind'], g['reason'].split(':')[0]) for g in img_gaps).items())),
        'changes_by_state': dict(sorted(collections.Counter(c['state'] for c in changes).items())),
        'dangling_parent_ids': dangling,
        'school_geoids_vs_data_v3_geo_schools_csv': school_check,
        'tiger_status': dict(sorted(collections.Counter(r.get('tiger_status', '') for r in local + tribes + states).items())),
        'sources': sources_summary(manifest()),
    }
    json.dump(summary, open(os.path.join(ROOT, 'summary.json'), 'w'), indent=1, sort_keys=False)
    print(json.dumps({k: summary[k] for k in summary if k != 'sources'}, indent=1))


if __name__ == '__main__':
    main()
