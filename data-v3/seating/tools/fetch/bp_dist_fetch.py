import json, os, re, gzip, time, subprocess, sys
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
urls = {}
for fn in sorted(os.listdir('bp/chambers')):
    if not fn.endswith('.html'): continue
    k = fn[:-5]
    s = BeautifulSoup(open('bp/chambers/' + fn).read(), 'lxml')
    for t in s.find_all('table'):
        tr = t.find('tr')
        hdr = [c.get_text(' ', strip=True) for c in tr.find_all(['th', 'td'])] if tr else []
        if hdr[:3] != ['Office', 'Name', 'Party']: continue
        for r in t.find_all('tr')[1:]:
            c = r.find_all(['td', 'th'])
            if not c: continue
            a = c[0].find('a')
            off = c[0].get_text(' ', strip=True)
            u = a['href'] if a and a.has_attr('href') else 'https://ballotpedia.org/' + off.replace(' ', '_')
            if u.startswith('/'): u = 'https://ballotpedia.org' + u
            urls[u] = (k, off)
        break
json.dump(urls, open('bp/districts/urls.json', 'w'), indent=0)
print('urls', len(urls), flush=True)
def get(item):
    u, (k, off) = item
    fn = 'bp/districts/' + re.sub(r'[^A-Za-z0-9_.-]', '_', u.split('/')[-1]) + '.html.gz'
    if os.path.exists(fn) and os.path.getsize(fn) > 5000: return
    for a in range(3):
        r = subprocess.run(['curl', '-sL', '-m', '60', '-A', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36', u], capture_output=True)
        if len(r.stdout) > 20000:
            gzip.open(fn, 'wb').write(r.stdout); break
        time.sleep(5 * (a + 1))
    time.sleep(0.4)
with ThreadPoolExecutor(4) as ex:
    for i, _ in enumerate(ex.map(get, urls.items())):
        if i % 250 == 0: print(i, time.strftime('%H:%M:%S'), flush=True)
print('done')
