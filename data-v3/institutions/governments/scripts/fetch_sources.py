"""Download every source into ../cache (skips files already cached unless --refresh)."""
import json, os, sys
from common import SOURCES, fetch, CACHE

def main():
    refresh = '--refresh' in sys.argv
    for k in SOURCES:
        fetch(k, refresh)
        print('ok', k)
    # latest BIA list notice: the newest document in the FR search whose title is the list title
    docs = json.load(open(os.path.join(CACHE, 'bia_search.json')))['results']
    docs = [d for d in docs if d['title'].startswith('Indian Entities Recognized')]
    latest = max(docs, key=lambda d: d['publication_date'])
    fetch('bia_notice', refresh, url=latest['full_text_xml_url'], fname='bia_{}.xml'.format(latest['document_number']))
    json.dump(latest, open(os.path.join(CACHE, 'bia_latest.json'), 'w'), indent=1)
    print('ok bia_notice', latest['document_number'], latest['publication_date'])

if __name__ == '__main__':
    main()
