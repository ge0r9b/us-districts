"""Rebuild every CSV in data-v3/institutions/governments from the cached sources.

    python3 scripts/fetch_sources.py           # download into cache/ (skips cached files; --refresh to re-download)
    python3 scripts/build_all.py               # write the CSVs + summary.json (deterministic for a given cache)
"""
import collections, json, os
import build_cog, build_states, build_federal_agencies, build_tribes
from common import ROOT, COLUMNS, XWALK_COLUMNS, write_csv, manifest


def main():
    states, xs = build_states.build()
    local, xl, per_state, chk = build_cog.build()
    fed = build_federal_agencies.build()
    tribes, xt, n_lines = build_tribes.build()
    out = {}
    out['states.csv'] = write_csv(os.path.join(ROOT, 'states.csv'), states, COLUMNS)
    out['federal_agencies.csv'] = write_csv(os.path.join(ROOT, 'federal_agencies.csv'), fed, COLUMNS)
    out['tribes.csv'] = write_csv(os.path.join(ROOT, 'tribes.csv'), tribes, COLUMNS)
    xw = sorted(xs + xl + xt, key=lambda x: (x['entity_id'], x['relation'] != 'primary', x['unit_layer'], x['geoid']))
    out['governments_geoid_xwalk.csv'] = write_csv(os.path.join(ROOT, 'governments_geoid_xwalk.csv'), xw, XWALK_COLUMNS)
    out['county_government_check.csv'] = len(chk)
    for k, v in per_state.items():
        out['local/{}.csv'.format(k)] = v
    ids = [r['entity_id'] for r in states + local + fed + tribes]
    assert len(ids) == len(set(ids)), 'duplicate entity_id'
    known = set(ids)
    dangling = sorted({r['parent_id'] for r in states + local + fed + tribes if r['parent_id'] and r['parent_id'] not in known})
    summary = {
        'files': out,
        'rows_total_entities': len(ids),
        'cog_by_type': dict(sorted(collections.Counter(r['type'] for r in local).items())),
        'cog_by_type_gov_status': {'{}|{}'.format(*k): v for k, v in sorted(collections.Counter((r['type'], r['gov_status']) for r in local).items())},
        'geoid_match': {'{}|{}'.format(*k): v for k, v in sorted(collections.Counter((r['type'], r['geoid_match']) for r in local + tribes).items())},
        'tiger_counties_without_cog_county_government': sum(1 for c in chk if c['cog_county_government'] == 'no'),
        'bia_list_lines': n_lines,
        'dangling_parent_ids': dangling,
        'sources': {k: {kk: v[kk] for kk in ('url', 'last_modified', 'retrieved_at')} for k, v in sorted(manifest().items())},
    }
    json.dump(summary, open(os.path.join(ROOT, 'summary.json'), 'w'), indent=1, sort_keys=False)
    print(json.dumps({k: summary[k] for k in summary if k != 'sources'}, indent=1))


if __name__ == '__main__':
    main()
