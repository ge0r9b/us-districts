#!/usr/bin/env python3
"""v3 officeholders, US House (institutions lane; plan: data-v3/inst/OFFICEHOLDERS_PLAN.md on data/inst-audit).
Inputs (raw, untouched, sha256 recorded in every row):
  House Clerk MemberData.xml (public domain; current Congress, dated snapshot)
  unitedstates/congress-legislators legislators-current.yaml + legislators-historical.yaml (CC0 1.0)
Outputs (data-v3/inst/, one row per seat x term):
  officeholders_house_current.csv  Clerk snapshot (vacancies included), unit_vintage cd119
  officeholders_house_2024.csv     119th Congress as elected Nov 2024: congress-legislators terms starting 2025-01-03,
                                   unit_vintage cd119; Clerk bioguide/party cross-check
  officeholders_house_2020.csv     117th Congress as elected Nov 2020 (terms starting 2021-01-03), unit_vintage cd116;
                                   unit_geoid EMPTY, join_status=pending_geo_2020 until geo's 2020 GEOID tables land
Join: statedistrict (Clerk; AQ = American Samoa) / congress-legislators (state, district) -> data-v3/geo/ushouse.csv
geoid by (state, 2-digit code); at-large 00; DC -> 1198. No name joins. Territories other than DC have no data-v3
unit (v2 draws no territories): join_status=no_v3_unit.
usage: inst_officeholders_house.py <repo> --clerk MemberData.xml --cl DIR --gaz116 2020_Gaz_116CDs_national.txt --out DIR [--retrieved DATE]
"""
import sys, os, csv, json, hashlib, collections
import xml.etree.ElementTree as ET
import yaml

COLS = ["unit_geoid", "unit_vintage", "join_status", "entity_id", "seat", "statedistrict", "person_id", "name", "party", "caucus",
        "status", "term_start", "term_end", "elected_date", "note", "source", "source_url", "source_id", "retrieved_at", "sha256", "license"]
CLERK_URL = "https://clerk.house.gov/xml/lists/MemberData.xml"
CL_URL = "https://github.com/unitedstates/congress-legislators"

G116 = {}; gaz116 = None
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(d): return "%s-%s-%s" % (d[:4], d[4:6], d[6:]) if d and len(d) == 8 else ""

def main():
    global gaz116
    a = sys.argv[1:]; repo = a[0]; gaz116 = a[a.index("--gaz116") + 1]; clerk = a[a.index("--clerk") + 1]; cl = a[a.index("--cl") + 1]; out = a[a.index("--out") + 1]
    retrieved = a[a.index("--retrieved") + 1] if "--retrieved" in a else ""
    geo = {}; names = {}
    for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/ushouse.csv"))): geo[(r["state"], r["v2_name"])] = r["geoid"]
    root = ET.parse(clerk).getroot(); csha = sha(clerk); pub = root.get("publish-date")
    members = list(root.find("members")); post2name = {}
    for m in members: post2name[m.find("member-info/state").get("postal-code")] = m.findtext("member-info/state/state-fullname")
    post2name.setdefault("AS", post2name.get("AQ"))
    def join(post, d):
        st = post2name.get(post); k = (st, "%02d" % d)
        if k in geo: return geo[k], "joined"
        return "", "no_v3_unit"
    stats = {}
    # current snapshot
    rows = []
    for m in members:
        sd = m.findtext("statedistrict"); post = sd[:2]; d = int(sd[2:]); mi = m.find("member-info")
        g, js = join(post, d); bid = (mi.findtext("bioguideID") or "").strip()
        rows.append({"unit_geoid": g, "unit_vintage": "cd119", "join_status": js, "entity_id": "us-house", "seat": "", "statedistrict": sd,
                     "person_id": "bioguide:" + bid if bid else "", "name": mi.findtext("official-name") or "", "party": mi.findtext("party") or "",
                     "caucus": mi.findtext("caucus") or "", "status": "serving" if bid else "vacant", "term_start": iso(mi.find("sworn-date").get("date")),
                     "term_end": "", "elected_date": iso(mi.find("elected-date").get("date")), "note": (mi.findtext("footnote") or "").strip(),
                     "source": "House Clerk MemberData.xml (publish-date %s)" % pub, "source_url": CLERK_URL, "source_id": sd,
                     "retrieved_at": retrieved, "sha256": csha, "license": "public domain (US government work)"})
    write(os.path.join(out, "officeholders_house_current.csv"), rows); stats["current"] = summary(rows)
    clerk_by = {r["statedistrict"]: r for r in rows}
    # congress-legislators
    cur, hist = os.path.join(cl, "legislators-current.yaml"), os.path.join(cl, "legislators-historical.yaml")
    L = yaml.safe_load(open(cur)) + yaml.safe_load(open(hist)); ysha = "%s (current) %s (historical)" % (sha(cur), sha(hist))
    commit = open(os.path.join(cl, "COMMIT")).read().strip() if os.path.exists(os.path.join(cl, "COMMIT")) else ""
    for vint, start, uv, fn in (("2024", "2025-01-03", "cd119", "officeholders_house_2024.csv"), ("2020", "2021-01-03", "cd116", "officeholders_house_2020.csv")):
        seats = collections.defaultdict(list)
        for p in L:
            for t in p["terms"]:
                if t["type"] == "rep" and t["start"] == start: seats[(t["state"], t["district"])].append((p, t))
        rows = []
        # expected seats: the Clerk's 441 for 2024 (same apportionment for 2020: 435 + 6)
        if vint == "2024":
            exp = {(("AS" if r["statedistrict"][:2] == "AQ" else r["statedistrict"][:2]), int(r["statedistrict"][2:])) for r in clerk_by.values()}
        else:   # 116th-Congress lines (2010 apportionment): TIGER 2020 Gazetteer 116 CDs, plus the four island delegates
            exp = set(); G116.clear()
            for r in csv.DictReader(open(gaz116), delimiter="\t"):
                code = r["GEOID"].strip()[2:]
                if not code.isdigit(): continue
                d = 0 if code in ("00", "98") else int(code); exp.add((r["USPS"].strip(), d)); G116[(r["USPS"].strip(), d)] = r["GEOID"].strip()
            exp |= {k for k in seats if k[0] in ("AS", "GU", "MP", "VI")}
        for k in sorted(set(exp) | set(seats)):
            post, d = k; sd = ("AQ" if post == "AS" else post) + "%02d" % d
            if vint == "2024": g, js = join(post, d)
            else: g, js = "", ("pending_geo_2020" if k in G116 and post != "PR" else "no_v3_unit")
            base = {"unit_geoid": g, "unit_vintage": uv, "join_status": js, "entity_id": "us-house", "seat": "", "statedistrict": sd,
                    "source": "unitedstates/congress-legislators (commit %s)" % commit, "source_url": CL_URL, "retrieved_at": retrieved,
                    "sha256": ysha, "license": "CC0 1.0"}
            if not seats.get(k):
                rows.append(dict(base, status="vacant", note="no Representative term starting %s in congress-legislators (seat vacant when the Congress convened)" % start, source_id=""))
                continue
            for p, t in seats[k]:
                bid = p["id"]["bioguide"]; note = ""
                if vint == "2024":
                    c = clerk_by.get(sd)
                    if c and c["person_id"] != "bioguide:" + bid: note = "Clerk %s now shows %s (%s)" % (pub, c["person_id"] or "vacant", c["note"] or "elected %s" % c["elected_date"])
                if vint == "2020" and k in G116: note = "TIGER 2020 cd116 GEOID %s; join to data-v3 waits for geo's 2020 GEOID tables" % G116[k]
                rows.append(dict(base, person_id="bioguide:" + bid, name=p["name"].get("official_full") or " ".join(x for x in (p["name"].get("first"), p["name"].get("last")) if x),
                                 party=t.get("party", ""), caucus=t.get("caucus", ""), status="elected", term_start=t["start"], term_end=t["end"], elected_date="",
                                 note=note, source_id=bid))
        write(os.path.join(out, fn), rows); stats[vint] = summary(rows)
    json.dump(stats, open(os.path.join(out, "officeholders_house_summary.json"), "w"), indent=1)
    print(json.dumps(stats, indent=1))

def write(p, rows):
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in COLS})

def summary(rows):
    return {"rows": len(rows), "by_status": dict(collections.Counter(r["status"] for r in rows)),
            "by_join": dict(collections.Counter(r["join_status"] for r in rows)),
            "vacant": [r["statedistrict"] for r in rows if r["status"] == "vacant"],
            "not_joined": [r["statedistrict"] for r in rows if r["join_status"] == "no_v3_unit"]}

if __name__ == "__main__":
    main()
