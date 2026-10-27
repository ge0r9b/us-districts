"""Extract Historic Election Data candidate slugs (candidate_id) with their state/office/year/district from the
read-only Election Data checkout -> src/results/upstream_cids.json. Their slugs are surname-first and NOT unique
across states (e.g. rogers-mike = AL-03 House and MI Senate 2024), so every link must use (slug, state)."""
import csv, glob, json, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else '/workspace/w/v3-election/data-v3/results'
OUT = '/workspace/seating/src/results/upstream_cids.json'
UNIT = {'us_house': 'ushouse', 'us_senate': 'state', 'state_house': 'sldl', 'state_senate': 'sldu', 'state_legislature': 'sldu'}
rows = set()
for f in sorted(glob.glob(f'{ROOT}/20*/*/*.csv')):
    if re.search(r'county|school|changed|delta|superseded|GAPS|president|statewide|_sld[ul]', f): continue
    rd = csv.DictReader(open(f, newline=''))
    if 'candidate_id' not in (rd.fieldnames or []): continue
    for r in rd:
        cid = r['candidate_id']; off = r['office']
        fam = next((k for k in UNIT if off.startswith(k)), None)
        if not cid or cid.startswith(('party-', 'writein', 'write-in', 'scatter', 'other', 'blank', 'over', 'under')) or not fam: continue
        if r['unit_type'] != UNIT[fam] and not (fam == 'us_senate' and r['unit_type'] == 'state'): continue
        rows.add((cid, r['state'], int(r['year']), fam, off, r['district'], r['answer']))
rows = sorted(rows)
json.dump([dict(cid=a, st=b, year=c, fam=d, office=e, district=g, name=h) for a, b, c, d, e, g, h in rows], open(OUT, 'w'))
print(len(rows), 'rows', len({r[0] for r in rows}), 'slugs', len({(r[0], r[1]) for r in rows}), 'slug-states')
