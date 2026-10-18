"""Shared helpers for the brands/locations pipeline (data-v3/institutions/companies).

Raw downloads go to ../raw/ (gitignored). Nothing here estimates or invents values:
every output row carries the URL it came from and the date the raw file was retrieved.
"""
import datetime as dt
import gzip
import json
import os
import pathlib
import threading
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                       # data-v3/institutions/companies
RAW = pathlib.Path(os.environ.get("COMPANIES_RAW", ROOT / "raw"))
RAW.mkdir(parents=True, exist_ok=True)

# Identify the crawler with a contact address on every request.
CONTACT = os.environ.get("CONTACT_EMAIL", "ultredex@mail.grokbot.com")
USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT", f"us-districts-data {CONTACT}")

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
_last = [0.0]
_lock = threading.Lock()


def get(url, min_interval=0.0, tries=5, **kw):
    """GET with polite rate limiting and retry on 429/5xx."""
    for i in range(tries):
        with _lock:  # global spacing across threads
            wait = _last[0] + min_interval - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            r = _session.get(url, timeout=120, **kw)
        except requests.RequestException:
            time.sleep(2 ** i)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** i * 2)
            continue
        return r
    raise RuntimeError(f"giving up on {url}")


def today():
    return dt.date.today().isoformat()


def write_meta(name, meta):
    (RAW / f"{name}.meta.json").write_text(json.dumps(meta, indent=1))


def read_meta(name):
    p = RAW / f"{name}.meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


def gz_json_dump(path, obj):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def gz_json_load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
