"""Latest BIA list of federally recognized Indian entities (Federal Register) -> tribes.csv.

One row per list line of the notice (both sections). entity_id = bia:<slug of the current name>; the notice
carries no numeric ID, so a rename produces a new slug (the former name stays in `alias` for several years per BIA
practice, which lets a refresh link the two). Lines that only point to another entry ("X (See Y)") are kept and
marked in `subtype` = cross_reference with parent_id pointing at Y.

AIANNH GEOIDs (TIGER 2024, as-is strings such as 0010R / 0010T / 6085R) are assigned only by an exact rule:
  * contiguous 48: a federal AIANNH reservation part's (MTFCC G2101) full legal name (NAMELSAD, e.g. 'Agua Caliente Indian Reservation',
    'Acoma Pueblo' or 'Pueblo of Acoma') appears verbatim (normalized, the word INDIAN ignored) inside the tribe's
    listed name. The longest such name wins; if two different areas tie, nothing is assigned.
  * Alaska: the village core of the name (e.g. 'Akiachak' from 'Akiachak Native Community') equals exactly one
    ANVSA NAME.
A reservation and its off-reservation trust land (R and T parts) both go to the crosswalk; geoid holds the R part
(or the T part when there is no R part). Areas shared by several tribes are listed for each tribe.
Everything else is left blank with geoid_match = no_name_match / ambiguous: BIA tribes do not map one-to-one to
land areas, and some have none.
"""
import collections, json, os, re, xml.etree.ElementTree as ET
from common import CACHE, COLUMNS, PUBLIC_DOMAIN, meta, norm, read_dbf

AK_PREFIX = ['NATIVE VILLAGE OF', 'TRADITIONAL VILLAGE OF', 'ORGANIZED VILLAGE OF', 'VILLAGE OF', 'CHINIK ESKIMO COMMUNITY',
             'INUPIAT COMMUNITY OF THE', 'NATIVE COUNCIL OF', 'COMMUNITY OF']
AK_SUFFIX = ['NATIVE VILLAGE', 'NATIVE COMMUNITY', 'NATIVE ASSOCIATION', 'TRADITIONAL COUNCIL', 'TRIBAL COUNCIL',
             'IRA COUNCIL', 'COMMUNITY ASSOCIATION', 'TRADITIONAL VILLAGE', 'VILLAGE', 'TRIBE', 'COMMUNITY']


def slug(s):
    return norm(s).lower().replace(' ', '-')


def entries():
    root = ET.parse(os.path.join(CACHE, meta('bia_notice')['file'])).getroot()
    sec, out = None, []
    for el in root.iter():
        if el.tag == 'HD' and el.get('SOURCE') == 'HD1':
            sec = 'alaska_native' if 'Alaska' in ''.join(el.itertext()) else 'contiguous_48'
        elif el.tag == 'FP' and sec:
            out.append((sec, ' '.join(''.join(el.itertext()).split()).replace('( See', '(See')))
    return out


def split_name(line):
    """'Current Name (previously listed as Old) (See X)' -> current, [aliases], see_target"""
    depth, cut = 0, None
    for i, ch in enumerate(line):           # current name = text before the first top-level '('
        if ch == '(' and depth == 0 and cut is None:
            cut = i
        depth += ch == '('
        depth -= ch == ')'
    cur = line[:cut].strip() if cut else line
    rest = line[cut:] if cut else ''
    groups, depth, buf = [], 0, ''
    for ch in rest:
        if ch == '(':
            depth += 1
            if depth == 1:
                buf = ''
                continue
        if ch == ')':
            depth -= 1
            if depth == 0:
                groups.append(buf.strip())
                continue
        if depth >= 1:
            buf += ch
    see, aliases = '', []
    for g in groups:
        if g.startswith('See ') and 'Supplementary Information' not in g:
            see = g[4:].strip()
        elif g.lower().startswith(('previously listed as ', 'formerly ', 'aka ', 'also known as ')):
            a = re.sub(r'^(previously listed as|formerly known as|formerly|aka|also known as)\s+', '', g, flags=re.I)
            aliases.append(re.sub(r'\s*\(\s*See .*$', '', a).strip())
        elif 'Supplementary Information' not in g:
            aliases.append(g)
    return cur, aliases, see


def ak_core(name):
    n = norm(re.sub(r'\([^)]*\)', ' ', name))
    for p in AK_PREFIX:
        if n.startswith(p + ' '):
            n = n[len(p) + 1:]
            break
    for s in AK_SUFFIX:
        if n.endswith(' ' + s):
            n = n[:-len(s) - 1]
            break
    return n


def build():
    m, bl = meta('bia_notice'), json.load(open(os.path.join(CACHE, 'bia_latest.json')))
    tm = meta('tiger_aiannh')
    areas = read_dbf(os.path.join(CACHE, 'tl_2024_us_aiannh.dbf'))
    by_ce = collections.defaultdict(list)
    for a in areas:
        by_ce[a['AIANNHCE']].append(a)
    noind = lambda s: ' '.join(w for w in norm(s).split() if w != 'INDIAN')
    keys = collections.defaultdict(set)         # normalized legal name -> {AIANNHCE}  (federal R/T areas, lower 48)
    anvsa = collections.defaultdict(set)        # ANVSA NAME -> {AIANNHCE}
    for a in areas:
        if a['MTFCC'] == 'G2130':
            anvsa[norm(a['NAME'])].add(a['AIANNHCE'])
        elif a['AIANNHR'] == 'F' and a['MTFCC'] == 'G2101':   # federal reservation / rancheria / colony / pueblo part
            nl = a['NAMELSAD']
            keys[noind(nl)].add(a['AIANNHCE'])
            if nl.endswith(' Pueblo'):
                keys[noind('Pueblo of ' + nl[:-7])].add(a['AIANNHCE'])

    src = 'Federal Register {}, {} ({}), "{}"'.format(bl['citation'], bl['document_number'], bl['publication_date'], bl['title'])
    rows, xw, seen = [], [], collections.Counter()
    ents = entries()
    for sec, line in ents:
        cur, aliases, see = split_name(line)
        eid = 'bia:' + slug(cur)
        seen[eid] += 1
        if seen[eid] > 1:
            eid += '-{}'.format(seen[eid])
        row = {'entity_id': eid, 'name': cur, 'type': 'tribe', 'subtype': 'cross_reference' if see else sec,
               'gov_status': 'federally_recognized', 'parent_id': 'bia:' + slug(see) if see else '',
               'alias': ';'.join(aliases), 'state_fips': '02' if sec == 'alaska_native' else '',
               'state': 'AK' if sec == 'alaska_native' else '',
               'note': 'listed as: ' + line if line != cur else '',
               'source': src, 'source_url': bl.get('html_url') or m['url'], 'source_date': bl['publication_date'],
               'retrieved_at': m['retrieved_at'], 'license': PUBLIC_DOMAIN, 'geoid_match': ''}
        ces = set()
        if see:
            row['geoid_match'] = 'cross_reference'
        elif sec == 'alaska_native':
            c = anvsa.get(ak_core(cur), set())
            if len(c) == 1:
                ces, how = c, 'name_core_anvsa'
            else:
                row['geoid_match'] = 'ambiguous' if c else 'no_name_match'
        else:
            t = ' ' + noind(cur) + ' '
            hits = [(len(k), k) for k in keys if ' ' + k + ' ' in t]
            if hits:
                best = max(hits)[0]
                c = set().union(*(keys[k] for L, k in hits if L == best))
                if len(c) == 1:
                    ces, how = c, 'legal_name_in_tribe_name'
                else:
                    row['geoid_match'] = 'ambiguous'
            else:
                row['geoid_match'] = 'no_name_match'
        if ces:
            parts = sorted(by_ce[next(iter(ces))], key=lambda a: a['GEOID'])
            prim = next((p for p in parts if p['GEOID'].endswith('R')), parts[0])
            row.update(geoid=prim['GEOID'], geoid_layer='aiannh', geoid_vintage='2024', geoid_match=how,
                       gnis_id=prim['AIANNHNS'])
            for p in parts:
                xw.append({'entity_id': eid, 'unit_layer': 'aiannh', 'geoid': p['GEOID'], 'vintage': '2024',
                           'relation': 'primary' if p is prim else ('trust_land' if p['GEOID'].endswith('T') else 'area_part'),
                           'match': how, 'source': 'bia:{};tiger2024_aiannh'.format(bl['document_number']),
                           'source_date': bl['publication_date']})
        rows.append(row)
    # areas matched by more than one tribe
    users = collections.defaultdict(set)
    for x in xw:
        users[x['geoid']].add(x['entity_id'])
    for x in xw:
        if len(users[x['geoid']]) > 1:
            x['relation'] += ';shared_area'
    return rows, xw, len(ents)
