import json, subprocess, os, time
pages = json.load(open('bp/courts/pages.json'))
excl = set(json.load(open('/workspace/seating/v3data/build_meta.json'))['excluded_courts'])
for k, t in pages.items():
    if k in excl: continue
    for y in range(2016, 2026):
        tt = t if k != 'TX_CCA' else 'Texas Court of Criminal Appeals'
        fn = f'bp/court_elections/{k}_{y}.html'
        if os.path.exists(fn) and os.path.getsize(fn) > 30000: continue
        subprocess.run(['curl', '-sL', '-m', '60', '-A', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                        'https://ballotpedia.org/' + (tt + ' elections, ' + str(y)).replace(' ', '_'), '-o', fn]); time.sleep(0.8)
print('done')
