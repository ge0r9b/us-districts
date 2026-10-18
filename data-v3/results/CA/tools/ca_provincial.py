#!/usr/bin/env python3
"""Provincial official results -> v3 rows. usage: ca_provincial.py <qc2026|qc2022|on2025|bc2024|ab2023> <raw_root> <units_dir> <out_dir>
Exact only: every row is a count as published; nothing is apportioned. Units without a polygon keep the riding boundary_set."""
import csv, gzip, io, re, sys, json, os, zipfile, collections, unicodedata, warnings
warnings.filterwarnings('ignore')
COLS = ['state', 'year', 'office', 'district', 'unit_id', 'unit_type', 'candidate_id', 'answer', 'party', 'votes', 'weight',
        'source_url', 'retrieved_at', 'boundary_set', 'method']

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def ret(d): return open(f'{d}/RETRIEVED_AT').read().strip()

def qc2026(raw, units):
    d = f'{raw}/qc'; url = 'https://donnees.electionsquebec.qc.ca/production/provincial/resultats/resultats.json'
    j = json.load(open(f'{d}/resultats.json'))
    parties = {p['numeroPartiPolitique']: p['nomPartiPolitique'] for p in j['statistiques']['partisPolitiques']}
    rows, chk = [], []
    for c in j['circonscriptions']:
        s = 0
        for k in c['candidats']:
            base = dict(state='CA-QC', year='2026', office='qc_national_assembly', district=str(c['numeroCirconscription']),
                        unit_id=str(c['numeroCirconscription']), unit_type='riding', candidate_id=slug(f"{k['nom']} {k['prenom']}"),
                        answer=f"{k['prenom']} {k['nom']}", party=parties.get(k['numeroPartiPolitique'], k['abreviationPartiPolitique']),
                        weight=1, source_url=url, retrieved_at=ret(d), boundary_set='eq-2026-ced')
            rows.append(dict(base, votes=k['nbVoteTotal'], method=f"official;of_which_advance={k['nbVoteAvance']}"))
            s += k['nbVoteTotal']
        chk.append((str(c['numeroCirconscription']), s, c['nbVoteValide']))
    # independent check: circonscriptions.csv (valid votes per riding)
    off = {r[0]: int(r[6]) for r in list(csv.reader(open(f'{d}/circonscriptions.csv', encoding='latin1'), delimiter=';'))[1:]}
    chk = [(a, b, off.get(a, -1)) for a, b, _ in chk]
    return '2026', 'qc_national_assembly', rows, chk, collections.Counter({'riding_only': sum(r['votes'] for r in rows)})

def qc2022(raw, units):
    d = f'{raw}/qc'; url = 'https://donnees.electionsquebec.qc.ca/production/provincial/resultats/archives/gen2022-10-03/resultats-bureau-vote.zip'
    cands = collections.defaultdict(list); off = collections.Counter()
    for r in list(csv.reader(open(f'{d}/gen2022_candidats.csv', encoding='latin1'), delimiter=';'))[1:]:
        cands[r[0]].append((r[2], r[3], r[5])); off[r[0]] += int(r[6])
    z = zipfile.ZipFile(f'{d}/gen2022_resultats-bureau-vote.zip'); rows = []; got = collections.Counter(); st = collections.Counter()
    for n in sorted(x for x in z.namelist() if x.endswith('.csv')):
        t = list(csv.reader(io.TextIOWrapper(z.open(n), 'latin1'), delimiter=';'))
        h = t[0]; ci = list(range(9, h.index('B.V.')))
        code = t[1][0]
        hc = {}
        for i in ci:
            m = [c for c in cands[code] if h[i].startswith(f'{c[0]} {c[1]} ')]
            if len(m) != 1: raise SystemExit(f'cand {code} {h[i]!r}')
            hc[i] = m[0]
        seen = collections.Counter()
        for r in t[1:]:
            if len(r) < len(h) or r[4].startswith(('Total de la', 'Majorit')): continue
            if r[7]:
                ut, uid, how = 'poll', f'{code}:{r[7]}', 'official;election_day_only'
            elif r[4].startswith('BVA'):
                ut, uid, how = 'advance', f'{code}:{r[4].split(":")[0]}', 'official;' + r[4].replace(';', ',')
            else:
                ut, uid, how = 'special', f'{code}:{slug(r[4])}', 'official'
            seen[uid] += 1
            if seen[uid] > 1: uid += f'#{seen[uid]}'
            if r[6]: how += ';' + slug(r[6])
            for i in ci:
                v = int(r[i] or 0); last, first, party = hc[i]
                rows.append(dict(state='CA-QC', year='2022', office='qc_national_assembly', district=code, unit_id=uid, unit_type=ut,
                                 candidate_id=slug(f'{last} {first}'), answer=f'{first} {last}', party=party, votes=v, weight=1,
                                 source_url=url, retrieved_at=ret(d), boundary_set='eq-2022-ced', method=how))
                got[code] += v; st['poll_no_2022_polygon' if ut == 'poll' else ut] += v
    chk = [(k, got[k], off[k]) for k in sorted(set(got) | set(off))]
    return '2022', 'qc_national_assembly', rows, chk, st

def on2025(raw, units):
    d = f'{raw}/on'; url = 'https://results.elections.on.ca/api/report-groups/48/report-outputs/1095/csv'
    party = {}; off = collections.Counter()
    for r in csv.DictReader(open(f'{d}/on2025_report1096.csv', encoding='utf-8-sig')):
        if r['IsGeneralElection'] != '1': continue
        ed = str(int(r['ElectoralDistrictNumber'])); party[(ed, r['NameOfCandidates'].strip().upper())] = r['PoliticalInterestCode']
        off[ed] += int(r['TotalValidBallotsCast'])
    rows = []; got = collections.Counter(); st = collections.Counter(); agg = collections.OrderedDict()
    for r in csv.DictReader(open(f'{d}/on2025_report1095.csv', encoding='utf-8-sig')):
        if 'General' not in r['EventNameEnglish']: continue
        ed = str(int(r['ElectoralDistrictNameEnglish'].split()[0]))
        nm = r['NameOfCandidates'].strip(); last, _, first = nm.partition(',')
        ut = 'advance' if r['PollCategory'] == 'Advance' else 'poll'
        uid = f"{ed}:{r['PollNumber']}"
        how = ['official']
        if r['IsCombinedPoll'] == '1': how.append('combined_with=' + r['CombinedWith'])
        if r['IsNoPollTaken'] == '1': how.append('no_poll_taken')
        if ut == 'poll': how.append('no_pd_polygon:on_pd_licence')
        k = (ed, uid, nm)
        v = int(r['AcceptedBallotCount'] or 0)
        if k in agg: agg[k]['votes'] += v; continue
        agg[k] = dict(state='CA-ON', year='2025', office='on_legislature', district=ed, unit_id=uid, unit_type=ut,
                      candidate_id=slug(f'{last} {first}'), answer=f'{first.strip()} {last.strip()}'.title(),
                      party=party.get((ed, f'{first.strip()} {last.strip()}'.upper()), party.get((ed, nm.upper()), '')), votes=v, weight=1,
                      source_url=url, retrieved_at=ret(d), boundary_set='eo-2022-ed', method=';'.join(how))
    for r in agg.values():
        got[r['district']] += r['votes']; st['poll_no_polygon' if r['unit_type'] == 'poll' else r['unit_type']] += r['votes']
    rows = list(agg.values())
    chk = [(k, got[k], off[k]) for k in sorted(set(got) | set(off), key=int)]
    return '2025', 'on_legislature', rows, chk, st

def bc2024(raw, units):
    d = f'{raw}/bc'; url = 'https://catalogue.data.gov.bc.ca/dataset/44914a35-de9a-4830-ac48-870001ef8935/resource/4e7be8e3-0805-4f39-87f3-47c4c29e262d/download/provincial_voting_results_by_voting_place.csv'
    agg = collections.OrderedDict(); st = collections.Counter(); got = collections.Counter()
    for r in csv.DictReader(open(f'{d}/provincial_voting_results_by_voting_place.csv', encoding='utf-8-sig')):
        if r['EVENT_NAME'] != '2024 Provincial General Election' or r['VOTE_CATEGORY'] != 'Valid': continue
        ed = r['ED_ABBREVIATION']; opp = r['VOTING_OPPORTUNITY']
        ut = 'advance' if opp.startswith('Advance') else ('poll' if opp == 'Final voting' and r['VOTING_LOCATION'] else 'special')
        loc = r['VOTING_LOCATION'] or ''
        uid = f"{ed}:{slug(opp)}:{r['ADDRESS_STANDARD_ID'] or slug(loc) or '-'}"
        last, _, first = r['CANDIDATE'].partition(',')
        k = (uid, r['CANDIDATE'])
        how = ['official', 'voting_place=' + loc.replace(';', ',')] if loc else ['official']
        if r['COMBINED_INDICATOR'] == 'Y': how.append('reported_under=' + r['RESULTS_REPORTED_UNDER'].replace(';', ','))
        v = int(r['VOTES_CONSIDERED'] or 0)
        if k in agg: agg[k]['votes'] += v
        else:
            agg[k] = dict(state='CA-BC', year='2024', office='bc_legislature', district=ed, unit_id=uid, unit_type=ut,
                          candidate_id=slug(f'{last} {first}'), answer=f'{first.strip()} {last.strip()}', party=r['AFFILIATION'], votes=v,
                          weight=1, source_url=url, retrieved_at=ret(d), boundary_set='ebc-2023-ed', method=';'.join(how))
    rows = list(agg.values())
    for r in rows: got[r['district']] += r['votes']; st['voting_place_no_va' if r['unit_type'] == 'poll' else r['unit_type']] += r['votes']
    offp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'provincial', 'bc2024_official_riding_totals_sov.csv')  # parsed from the Statement of Votes PDF
    off = {r['district']: int(r['valid']) for r in csv.DictReader(open(offp))} if os.path.exists(offp) else {}
    chk = [(k, got[k], off.get(k, -1)) for k in sorted(got)]
    return '2024', 'bc_legislature', rows, chk, st

def ab2023(raw, units):
    import openpyxl
    d = f'{raw}/ab'; rows = []; chk = []; st = collections.Counter()
    vas = {r['unit_key'] for r in csv.DictReader(open(f'{units}/units_ca_ppoll.csv')) if r['province'] == 'AB'}
    for i in range(1, 88):
        url = f'https://officialresults.elections.ab.ca/orResultsED.cfm?MODE=exED&ED={i:02d}&EventId=101'
        t = list(openpyxl.load_workbook(f'{d}/ab2023_ED{i:02d}.xlsx', read_only=True).worksheets[0].iter_rows(values_only=True))
        h = t[1]; ci = list(range(5, h.index('Valid Ballots Cast')))
        ed = str(i); s = 0; tot = None; seen = collections.Counter()
        for r in t[2:]:
            if r[3] == 'Total (All Voting Locations)': tot = sum(int(r[c]) for c in ci)
            if not isinstance(r[0], (int, float)): continue
            typ = r[3]; ut = {'Election Day': 'poll', 'Advance': 'advance'}.get(typ, 'special')
            uid = f'{ed}:{slug(typ)}-{int(r[0])}'
            how = ['official', 'voting_place=' + str(r[1]).replace(';', ',')]
            if typ == 'Mobile': how.append('mobile')
            if r[2]:
                vl = [x.strip() for x in str(r[2]).split(',') if x.strip()]
                how.append('vas=' + '+'.join(vl))
                cov = all(f'{ed}:{x}' in vas for x in vl)
            for c in ci:
                nm, _, pa = h[c].partition('\n'); v = int(r[c] or 0)
                rows.append(dict(state='CA-AB', year='2023', office='ab_legislature', district=ed, unit_id=uid, unit_type=ut,
                                 candidate_id=slug(nm), answer=nm.title(), party=pa, votes=v, weight=1, source_url=url,
                                 retrieved_at=ret(d), boundary_set='ea-2019-ed', method=';'.join(how)))
                s += v
                st[('va_union_codes_in_2026_units' if cov else 'va_union_codes_missing') if ut == 'poll' else ut] += v
        chk.append((ed, s, tot))
    return '2023', 'ab_legislature', rows, chk, st

def main(which, raw, units, out):
    year, office, rows, chk, st = globals()[which](raw, units)
    os.makedirs(out, exist_ok=True)
    fn = f'{out}/{office}_{year}.csv.gz'
    with gzip.open(fn, 'wt', newline='', compresslevel=9) as f:
        w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)
    with open(f'{out}/check_{office}_{year}_riding_vs_official.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['year', 'district', 'rows_sum', 'official_total', 'diff', 'match'])
        for a, b, c in chk: w.writerow([year, a, b, c, b - c, 'Y' if b == c else 'N'])
    tot = sum(st.values())
    s = dict(year=year, office=office, rows=len(rows), ridings=len(chk), votes=tot, by_unit=dict(st),
             pct_on_polygon=0.0, ridings_mismatch=sum(b != c for _, b, c in chk))
    json.dump(s, open(f'{out}/summary_{office}_{year}.json', 'w'), indent=1); print(json.dumps(s))

if __name__ == '__main__':
    main(*sys.argv[1:5])
