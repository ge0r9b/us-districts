"""TCEQ Water Districts Database (WDD, https://www14.tceq.texas.gov/iwud/): district list (all statuses) and the
detail pages of selected districts (creation date, activity date, activity status). Cached in cache/tceq_wdd/.
One request per second."""
import html, json, os, re, time, urllib.parse, urllib.request
from common import CACHE

BASE = 'https://www14.tceq.texas.gov/iwud/dist/index.cfm?'
UA = 'us-districts-governments-dataset/1.0 (https://github.com/ge0r9b/us-districts; ge0r9b@users.noreply.github.com)'
DIR = os.path.join(CACHE, 'tceq_wdd')


def get(url, fname):
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, fname)
    if not os.path.exists(path):
        time.sleep(1)
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(10)
        open(path, 'wb').write(data)
    return open(path, encoding='utf-8', errors='replace').read()


def district_list():
    """[(wdd_id, name, number, status)] in list order, plus retrieval note."""
    out, url, n = [], BASE + 'fuseaction=ListDistricts&Command=list', 0
    while url:
        t = get(url, 'list_{:03d}.html'.format(n))
        for m in re.finditer(r'DetailDistrict&ID=(\d+)&[^"]*"[^>]*>\s*([^<]+?)\s*</a>\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>', t):
            out.append((m.group(1), html.unescape(m.group(2)), m.group(3), m.group(4).strip()))
        nx = re.search(r'href="(index\.cfm\?fuseaction=listdistricts&Command=NEXT[^"]+)"', t)
        url = BASE + html.unescape(nx.group(1)).split('?', 1)[1] if nx else None
        n += 1
        if n > 200:
            break
    return out


def detail(wdd_id):
    t = get(BASE + 'fuseaction=DetailDistrict&ID={}&command=list&name='.format(wdd_id), 'd_{}.html'.format(wdd_id))
    x = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' | ', t)))
    x = re.sub(r'(\s*\|\s*)+', ' | ', x)
    def g(lab):   # value cell after the label; an empty cell makes the regex reach the next label, which is no value
        v = (re.search(re.escape(lab) + r' \| ([^|]*?) \|', x) or [None, ''])[1].strip()
        return '' if v.endswith(':') else v
    return {'creation_date': g('Creation Date:'), 'activity_date': g('Activity Date:'), 'activity_status': g('Activity Status:'),
            'district_type': g('District Type:'), 'creation_type': g('Creation Type:'), 'primary_county': g('Primary County:'),
            'name': (re.search(r'District Name: \| ([^|]*?) \|', x) or [None, ''])[1].strip()}


if __name__ == '__main__':
    L = district_list()
    print(len(L))
    json.dump(L, open(os.path.join(DIR, 'list.json'), 'w'))
