#!/usr/bin/env python3
"""State legislature officeholders (v3; institutions lane), OFFICEHOLDERS_PLAN.md step 2.

Source: OpenStates people (github.com/openstates/people, CC0 1.0), one YAML per person, cited per row (file path at
the pinned commit + file sha256 + the official legislature URL OpenStates lists for that person, when it lists one).
OpenStates is the plan's fallback; the official legislature rosters (50 formats) were not fetched this round, so every
row says so in `note` and the coverage table lists it as the open item.

Vintages (both on the 2024 district plans, TIGER 2024 SLDU/SLDL via data-v3/geo/senate.csv and statehouse.csv):
  current   roles in force on the retrieval date (no end_date, or end_date after it; start_date on/before it or absent)
  2024      roles in force on SNAP_2024 = 2025-04-01, i.e. the chambers seated after the Nov 2024 elections (odd-year
            states LA, MS, NJ, VA: the members elected in 2023 who were serving then). Searched in legislature/ and
            retired/. A role with no start_date is kept and flagged (`start date not recorded`). April, not February: OpenStates
            closes many outgoing members' roles on 2025-02-03 (the date its scrapers saw the change), e.g. Nebraska, so
            an earlier date double-counts seats.
Join (by district label, never by person name): OpenStates `district` vs the TIGER name or code in the geo tables,
normalized (case, punctuation, the words District/Senatorial/State House/..., 'and', leading zeros). Fallbacks:
a trailing seat letter (Idaho '10A' = district 10, seat A) when the full label has no unit; MA 'Barnstable, Dukes and
Nantucket' = TIGER 'Cape and Islands District' (25D40, the only Senate district containing Dukes and Nantucket
counties). Nebraska's unicameral 'legislature' roles join to senate.csv. Labels with no unit -> join_status no_v3_unit.
usage: inst_officeholders_stateleg.py <repo> --os DIR --out DIR --retrieved YYYY-MM-DD
"""
import sys, os, re, csv, glob, json, hashlib, subprocess, collections
import yaml

SNAP_2024 = "2025-04-01"
ST = ("Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky "
      "Louisiana Maine Maryland Massachusetts Michigan Minnesota Mississippi Missouri Montana Nebraska Nevada New_Hampshire New_Jersey New_Mexico "
      "New_York North_Carolina North_Dakota Ohio Oklahoma Oregon Pennsylvania Rhode_Island South_Carolina South_Dakota Tennessee Texas Utah Vermont "
      "Virginia Washington West_Virginia Wisconsin Wyoming").split()
AB = "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
NAME = {a: s.replace("_", " ") for a, s in zip(AB, ST)}
ALIAS = {("Massachusetts", "upper", "Barnstable, Dukes and Nantucket"): "25D40"}
COLS = ["unit_geoid", "unit_vintage", "join_status", "entity_id", "seat", "state", "chamber", "district", "person_id", "name", "party", "status",
        "term_start", "term_end", "note", "source", "source_url", "upstream_url", "source_id", "retrieved_at", "sha256", "license"]

def nk(s):
    s = s.upper()
    s = re.sub(r"\b(STATE SENATE|STATE HOUSE|STATE ASSEMBLY|ASSEMBLY|HOUSE|SENATE|SENATORIAL|LEGISLATIVE|GENERAL ASSEMBLY|AND)\b", " ", s)
    s = re.sub(r"\b(DISTRICT|DIST|NO)\b\.?", " ", s)
    s = re.sub(r"\b0+(\d)", r"\1", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def main():
    a = sys.argv[1:]; repo = a[0]; osd = a[a.index("--os") + 1]; out = a[a.index("--out") + 1]; retrieved = a[a.index("--retrieved") + 1]
    commit = subprocess.run(["git", "-C", osd, "log", "-1", "--format=%H %cI"], capture_output=True, text=True).stdout.split()
    G = collections.defaultdict(dict); amb = collections.defaultdict(set); units = collections.defaultdict(set)
    for fn, ch in (("senate.csv", "upper"), ("statehouse.csv", "lower")):
        for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo", fn))):
            if r["state"] == "Nebraska" and ch == "lower": continue
            units[(r["state"], ch)].add(r["geoid"])
            for k in {nk(r["tiger_name"]), nk(r["v2_name"])}:
                if k in G[(r["state"], ch)] and G[(r["state"], ch)][k] != r["geoid"]: amb[(r["state"], ch)].add(k)
                G[(r["state"], ch)][k] = r["geoid"]
    for key, ks in amb.items():
        for k in ks: G[key].pop(k, None)
    def join(st, ch, d):
        if (st, ch, d) in ALIAS: return ALIAS[(st, ch, d)], "", "joined_alias"
        g = G[(st, ch)].get(nk(d))
        if g: return g, "", "joined"
        m = re.match(r"^(.*\d)\s*([A-Z])$", d.strip())
        if m:
            g = G[(st, ch)].get(nk(m.group(1)))
            if g: return g, m.group(2), "joined"
        return "", "", "no_v3_unit"
    people = []
    for ab in AB:
        for sub in ("legislature", "retired"):
            for f in sorted(glob.glob(os.path.join(osd, "data", ab.lower(), sub, "*.yml"))):
                people.append((ab, sub, f))
    files = {}
    def up(p):
        for s in p.get("sources", []) + p.get("links", []):
            u = s.get("url", "")
            if re.search(r"https?://([^/]*\.)?(legis|leg\.|senate|house|assembly|legislature|capitol|gov\b|\.gov/|\.us/)", u) and "ballotpedia" not in u and "wikipedia" not in u and "votesmart" not in u:
                return u
        return ""
    rows = {"current": [], "2024": []}
    for ab, sub, f in people:
        p = yaml.safe_load(open(f)); rel = os.path.relpath(f, osd)
        st = NAME[ab]
        for r in p.get("roles", []):
            if r.get("type") not in ("upper", "lower", "legislature"): continue
            s0, e0 = str(r.get("start_date") or ""), str(r.get("end_date") or "")
            for vint, day in (("current", retrieved), ("2024", SNAP_2024)):
                if vint == "current" and sub != "legislature": continue
                if s0 and s0 > day: continue
                if e0 and e0 <= day: continue
                if vint == "current" and e0 and e0 <= retrieved: continue
                ch = "upper" if r["type"] in ("upper", "legislature") else "lower"
                g, seat, js = join(st, ch, str(r["district"]))
                if f not in files: files[f] = hashlib.sha256(open(f, "rb").read()).hexdigest()
                note = ["official roster not fetched this round; OpenStates (CC0) fallback"]
                if not s0: note.append("start date not recorded in OpenStates")
                if js == "joined_alias": note.append("district label 'Barnstable, Dukes and Nantucket' = TIGER 'Cape and Islands District' (the only MA Senate district containing Dukes and Nantucket counties)")
                if js == "no_v3_unit": note.append("district label '%s' matches no unit of data-v3/geo/%s.csv (TIGER 2024 %s)" % (r["district"], "senate" if ch == "upper" else "statehouse", "SLDU" if ch == "upper" else "SLDL"))
                party = p.get("party") or []
                pty = next((x["name"] for x in party if (not x.get("start_date") or str(x["start_date"]) <= day) and (not x.get("end_date") or str(x["end_date"]) > day)), party[0]["name"] if party else "")
                rows[vint].append({"unit_geoid": g, "unit_vintage": "sldu2024" if ch == "upper" else "sldl2024", "join_status": "joined" if js.startswith("joined") else js,
                    "entity_id": "%s-%s" % (ab.lower(), "legislature" if r["type"] == "legislature" else ("senate" if ch == "upper" else "house")), "seat": seat,
                    "state": st, "chamber": r["type"], "district": r["district"], "person_id": p["id"], "name": p["name"], "party": pty,
                    "status": "serving" if vint == "current" else "serving_at_%s" % SNAP_2024, "term_start": s0, "term_end": e0, "note": "; ".join(note),
                    "source": "OpenStates people (commit %s %s), %s" % (commit[0][:12], commit[1], rel),
                    "source_url": "https://github.com/openstates/people/blob/%s/%s" % (commit[0], rel), "upstream_url": up(p),
                    "source_id": p["id"], "retrieved_at": retrieved, "sha256": files[f], "license": "CC0 1.0"})
    S = {}
    for vint, rs in rows.items():
        rs.sort(key=lambda x: (x["state"], x["chamber"], x["unit_geoid"] or "~", x["district"], x["name"]))
        with open(os.path.join(out, "officeholders_stateleg_%s.csv" % vint), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
            for r in rs: w.writerow(r)
        per = {}
        for st in [NAME[x] for x in AB]:
            mine = [r for r in rs if r["state"] == st]; d = {}
            for ch in ("upper", "lower"):
                m = [r for r in mine if (r["chamber"] in ("upper", "legislature")) == (ch == "upper")]
                if st == "Nebraska" and ch == "lower": continue
                filled = {r["unit_geoid"] for r in m if r["unit_geoid"]}
                d[ch] = {"members": len(m), "joined": sum(r["join_status"] == "joined" for r in m), "no_v3_unit": sorted({r["district"] for r in m if r["join_status"] == "no_v3_unit"}),
                         "units": len(units[(st, ch)]), "units_with_member": len(filled & units[(st, ch)]), "units_without_member": sorted(units[(st, ch)] - filled),
                         "no_start_date": sum("start date not recorded" in r["note"] for r in m)}
            per[st] = d
        S[vint] = {"rows": len(rs), "joined": sum(r["join_status"] == "joined" for r in rs), "no_v3_unit": sum(r["join_status"] == "no_v3_unit" for r in rs), "by_state": per}
    S["openstates_commit"] = commit; S["snapshot_2024"] = SNAP_2024
    json.dump(S, open(os.path.join(out, "officeholders_stateleg_summary.json"), "w"), indent=1)
    for vint in ("current", "2024"):
        print(vint, S[vint]["rows"], "joined", S[vint]["joined"], "no_v3_unit", S[vint]["no_v3_unit"])
        for st, d in S[vint]["by_state"].items():
            for ch, x in d.items():
                if x["no_v3_unit"] or x["units_without_member"] or x["no_start_date"]:
                    print("  ", st, ch, "members", x["members"], "units %d/%d" % (x["units_with_member"], x["units"]), "nounit", x["no_v3_unit"][:6], "empty", x["units_without_member"][:6], "nostart", x["no_start_date"])

if __name__ == "__main__":
    main()
