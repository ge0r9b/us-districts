#!/usr/bin/env python3
"""Elections Canada Format-2 poll-by-poll results -> v3 rows on the Institutions lane's PD units.
usage: ca_federal.py <ge45|ge44|ge43> <raw_dir> <units_dir> <out_dir>
Exact only: station rows are summed into their PD (78A+78B -> 78-0, 174-1A -> 174-1); nothing is estimated."""
import csv, gzip, io, re, sys, unicodedata, zipfile, collections, json, os
GE = {'ge45': ('2025', 'ovrGE45/62', 'ec-2025-pd', 'ec-2023-fed'),
      'ge44': ('2021', 'ovr2021app/53', 'ec-2021-pd', 'ec-2013-fed'),
      'ge43': ('2019', 'ovr2019app/51', 'ec-2019-pd', 'ec-2013-fed')}
PROV = {'10': 'NL', '11': 'PE', '12': 'NS', '13': 'NB', '24': 'QC', '35': 'ON', '46': 'MB', '47': 'SK', '48': 'AB',
        '59': 'BC', '60': 'YT', '61': 'NT', '62': 'NU'}
COLS = ['state', 'year', 'office', 'district', 'unit_id', 'unit_type', 'candidate_id', 'answer', 'party', 'votes', 'weight',
        'source_url', 'retrieved_at', 'boundary_set', 'method']

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def main(ge, raw, units, out):
    year, path, pdset, fedset = GE[ge]
    url = f'https://www.elections.ca/res/rep/off/{path}/data_donnees/pollresults_resultatsbureauCanada.zip'
    ret = open(f'{raw}/RETRIEVED_AT').read().strip()
    pds = {r['unit_key'] for r in csv.DictReader(open(f'{units}/units_ca_pd_{year}.csv'))}
    z = zipfile.ZipFile(f'{raw}/{ge}_pollresults_Canada.zip')
    agg = collections.OrderedDict()   # (fed, unit_id, cand) -> [row, votes, stations, notes]
    fedtot = collections.defaultdict(lambda: collections.Counter())
    stats = collections.Counter(); unjoined = []
    allrows = [row for n in sorted(z.namelist()) for row in list(csv.reader(io.TextIOWrapper(z.open(n), 'utf-8-sig')))[1:]]
    # one candidate per (riding, party); independents / no affiliation by name. Spelling variants of the same
    # candidate within a riding (e.g. 2021 59001 'Dhrmasena'/'dharmasena') fold onto the most-voted spelling.
    def ckey(row):
        party = row[13].strip()
        if party.lower() in ('independent', 'no affiliation'): return (row[0].strip(), party, slug(row[12] + ' ' + row[11] + ' ' + row[10]))
        return (row[0].strip(), party, '')
    spell = collections.defaultdict(collections.Counter)
    for row in allrows:
        spell[ckey(row)][(row[10].strip(), row[11].strip(), row[12].strip())] += int(row[17] or 0)
    canon = {k: c.most_common(1)[0][0] for k, c in spell.items()}
    variants = {k: sorted(c) for k, c in spell.items() if len(c) > 1}
    byslug = collections.Counter((k[0], slug(f'{v[0]} {v[2]} {v[1]}')) for k, v in canon.items())
    for row in allrows:
            fed, st = row[0].strip(), row[3].strip()
            last, mid, first = canon[ckey(row)]; party = row[13].strip()
            v = int(row[17] or 0)
            notes = []
            if row[5] == 'Y': notes.append(st + ':void')
            if row[6] == 'Y': notes.append(st + ':no_poll_held')
            if row[7].strip(): notes.append(st + ':combined_with=' + row[7].strip())
            if st.startswith('S/R'):
                ut, uid, bset = 'special', f'{fed}:{st}', fedset
            else:
                m = re.fullmatch(r'(\d+)([A-Z]?)(?:-(\d+)([A-Z]?))?', st)
                if not m: raise SystemExit(f'bad station {fed} {st!r}')
                num, sfx = int(m.group(1)), m.group(3) or '0'
                if 600 <= num < 700 and not m.group(3):
                    ut, uid, bset = 'advance', f'{fed}:{num}', fedset
                else:
                    uid = f'{fed}:{num}-{sfx}'
                    if uid in pds: ut, bset = 'poll', pdset
                    else: ut, bset = 'poll', ''; notes.append(st + ':no_pd_polygon')
            name = ' '.join(x for x in (first, mid, last) if x)
            cid = slug(f'{last} {first} {mid}')
            if byslug[(fed, cid)] > 1: cid += '-' + slug(party)
            k = (fed, uid, cid)
            if k not in agg:
                agg[k] = [dict(state='CA-' + PROV[fed[:2]], year=year, office='ca_house_of_commons', district=fed, unit_id=uid,
                               unit_type=ut, candidate_id=cid, answer=name, party=party, weight=1, source_url=url,
                               retrieved_at=ret, boundary_set=bset), 0, [], set()]
            a = agg[k]; a[1] += v; a[2].append(st); a[3].update(notes)
            fedtot[fed][cid] += v
            jt = 'pd_polygon' if bset == pdset else ('no_pd_polygon' if not bset else ut)
            stats[jt] += v
            if not bset: unjoined.append((fed, st, v))
    os.makedirs(out, exist_ok=True)
    fn = f'{out}/ca_house_of_commons_{year}_poll.csv.gz'
    with gzip.open(fn, 'wt', newline='', compresslevel=9) as f:
        w = csv.DictWriter(f, COLS); w.writeheader()
        for (fed, uid, cid), (r, v, sts, notes) in agg.items():
            m = ['official']
            if len(set(sts)) > 1: m.append('stations=' + '+'.join(sorted(set(sts))))
            m += sorted(notes)
            r = dict(r, votes=v, method=';'.join(m)); w.writerow(r)
    # official riding totals (Table 12)
    off = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{raw}/{ge}_table_tableau12.csv', encoding='utf-8-sig')):
        k = [c for c in r if c.startswith('Electoral District Number')][0]
        vk = [c for c in r if c.startswith('Votes Obtained')][0]
        off[r[k].strip()].append(int(r[vk]))
    chk = []; bad = 0
    for fed in sorted(set(off) | set(fedtot)):
        a = sorted(fedtot[fed].values(), reverse=True); b = sorted(off.get(fed, []), reverse=True)
        ok = a == b; bad += not ok
        chk.append(dict(year=year, district=fed, candidates=len(a), poll_sum=sum(a), official_total=sum(b),
                        diff=sum(a) - sum(b), match='Y' if ok else 'N'))
    with open(f'{out}/check_{year}_riding_vs_official.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, list(chk[0])); w.writeheader(); w.writerows(chk)
    tot = sum(stats.values())
    s = dict(year=year, rows=len(agg), ridings=len(fedtot), votes=tot, by_join={k: v for k, v in stats.items()},
             pct_on_pd_polygon=round(100 * stats['pd_polygon'] / tot, 2), ridings_mismatch=bad,
             unjoined_stations=len({(a, b) for a, b, _ in unjoined}),
             unjoined_examples=sorted({(a, b) for a, b, _ in unjoined})[:20],
             unjoined_votes=sum(v for *_, v in unjoined), name_variants_folded={'|'.join(k): [' '.join(x) for x in v] for k, v in variants.items()})
    json.dump(s, open(f'{out}/summary_{year}.json', 'w'), indent=1)
    print(json.dumps(s))

if __name__ == '__main__':
    main(*sys.argv[1:5])
