import json, subprocess, os, time, re, unicodedata
from bs4 import BeautifulSoup
bp = json.load(open('bp_courts.json'))
import openstates_metadata as M
os.makedirs('wiki/courts', exist_ok=True)
titles = {}
for k in bp:
    st, c = k.split('_')
    name = M.lookup(abbr=st).name
    if c == 'CCA': t = f"{name} Court of Criminal Appeals"
    else: t = bp[k]['title'] if st in ('NY','MA','ME','WV') else f"{name} Supreme Court"
    titles[k] = t
def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
out = {}
for k, t in titles.items():
    fn = f"wiki/courts/{k}.html"
    if not os.path.exists(fn) or os.path.getsize(fn) < 5000:
        subprocess.run(["curl","-sL","-A","seating-bot/0.1 (research)","https://en.wikipedia.org/api/rest_v1/page/html/"+t.replace(' ','_'),"-o",fn]); time.sleep(0.3)
    txt = norm(BeautifulSoup(open(fn).read(), 'lxml').get_text(' '))
    missing = []
    for r in bp[k]['rows']:
        if r['name'] == 'Vacant': continue
        last = norm(r['name']).replace(' jr.','').replace(' iii','').split()[-1]
        if last not in txt: missing.append(r['name'])
    out[k] = dict(title=t, size=os.path.getsize(fn), missing=missing)
    print(k, t, os.path.getsize(fn), missing)
json.dump(out, open('wiki_courts_check.json','w'), indent=1)
