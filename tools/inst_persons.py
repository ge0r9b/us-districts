#!/usr/bin/env python3
"""Canonical person IDs for every officeholder file + data-v3/inst/persons.csv (institutions lane).

Spec (v3 Full Stack, 2026-10-18): person_id = 'scheme:id', one canonical ID per person, priority
  bioguide:<ID>  >  ocd-person:<uuid>  >  <st>-leg:<official id>.
* bioguide comes ONLY from OpenStates' own person records (other_identifiers scheme 'bioguide'); a state legislator
  gets bioguide canonical only if the same OpenStates person record (same ocd-person id, or one OpenStates merged into
  it via scheme 'openstates') lists a bioguide ID. No name matching across levels, ever.
* rows whose person_id is a bare official id (official-only members): matched to an OpenStates person when exactly
  one OpenStates person has a role in the same state + chamber + district label with the same last name and the same
  first initial (any role dates); each match is logged in person_id_matches.csv. Otherwise '<st>-leg:<official id>'.
* aliases: every former or alternate canonical ID (the ocd-person id after a bioguide promotion, OpenStates-merged
  ids, the <st>-leg id of an official row that was matched), so no previously published ID is orphaned.
* vacancies: person_id '' and status 'vacant'. State-legislature units of data-v3/geo with no member row at all get a
  vacant row (note says the source lists nobody). Partially vacant multi-member units are only marked where the
  official roster lists the vacancy (no seat counts in v3 geo).
* date_flags: term_start_missing when a non-vacant row has no term_start; term_end_open when it has no term_end
  (serving with no end date in the source).
Runs AFTER inst_officeholders_house.py, inst_officeholders_stateleg.py and inst_stateleg_official.py; edits their
outputs in place and is idempotent.
usage: inst_persons.py <repo> --os inst-raw/openstates-people --out data-v3/inst
"""
import sys, os, re, csv, glob, json, collections, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
import inst_officeholders_stateleg as L

def fold(s): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper())
def lastn(n):
    n = re.sub(r",?\s+(Jr|Sr|II|III|IV|V|Ph\.?\s?D|M\.?\s?D)\.?$", "", (n or "").strip(), flags=re.I)
    return fold(n.split(",")[0] if "," in n else (n.split()[-1] if n.split() else n))
def first_initial(n):
    n = (n or "").strip()
    if "," in n: n = n.split(",", 1)[1]
    w = [x for x in n.split() if len(x.strip(".")) > 1] or n.split()
    return fold(w[0])[:1] if w else ""

def ocd_uuid(pid):
    m = re.match(r"ocd-person[/:]([0-9a-f-]{36})$", pid or ""); return m.group(1) if m else None

def main():
    a = sys.argv[1:]; repo = a[0]; OS = a[a.index("--os") + 1]; out = a[a.index("--out") + 1]
    people = {}; merged = {}
    for f in glob.glob(os.path.join(OS, "data", "*", "*", "*.yml")):
        d = yaml.safe_load(open(f)); u = ocd_uuid(d["id"])
        oi = d.get("other_identifiers") or []
        bg = sorted({str(o["identifier"]) for o in oi if o.get("scheme") == "bioguide"})
        people[u] = dict(name=d.get("name", ""), bioguide=bg, roles=d.get("roles") or [], abbr=f.split(os.sep)[-3], file=os.path.relpath(f, OS))
        for o in oi:
            if o.get("scheme") == "openstates" and ocd_uuid(str(o["identifier"])): merged[ocd_uuid(str(o["identifier"]))] = u
    bio2ocd = collections.defaultdict(set)
    for u, p in people.items():
        for b in p["bioguide"]: bio2ocd[b].add(u)
    def bioguide_of(u):
        b = set(people.get(u, {}).get("bioguide", []))
        for m, tgt in merged.items():
            if tgt == u: b |= set(people.get(m, {}).get("bioguide", []))
        return sorted(b)
    # role index for official-id matching: (abbr, chamber, district label folded) -> uuids
    ridx = collections.defaultdict(set)
    for u, p in people.items():
        for r in p["roles"]:
            j = r.get("jurisdiction", ""); m = re.search(r"state:(\w\w)/", j)
            if not m: continue
            ch = "upper" if r.get("type") in ("upper", "legislature") else "lower" if r.get("type") == "lower" else None
            if ch: ridx[(m.group(1), ch, fold(str(r.get("district", ""))))].add(u)
    join, units = L.build_join(repo)
    files = ["officeholders_house_2020.csv", "officeholders_house_2024.csv", "officeholders_house_current.csv",
             "officeholders_stateleg_current.csv", "officeholders_stateleg_2024.csv"]
    P = collections.OrderedDict(); matches = []; stats = collections.Counter()
    def person(cid):
        return P.setdefault(cid, dict(person_id=cid, bioguide="", ocd_person="", official_ids=set(), name="", sources=set(), aliases=set()))
    for fn in files:
        path = os.path.join(out, fn)
        if not os.path.exists(path): continue
        rows = list(csv.DictReader(open(path))); cols = list(rows[0].keys())
        if "date_flags" not in cols: cols.append("date_flags")
        stateleg = "stateleg" in fn
        for r in rows:
            pid = r["person_id"]
            if r["status"] == "vacant" or not pid:
                r["person_id"] = ""; r["status"] = "vacant" if stateleg or r["status"] == "vacant" else r["status"]; r["date_flags"] = ""; continue
            ab = L.AB[L.ST.index(r["state"].replace(" ", "_"))].lower() if stateleg else ""
            aliases = set(); official = set(); ocd = None; bio = None
            if pid.startswith("bioguide:"):
                bio = pid.split(":", 1)[1]; o = sorted(bio2ocd.get(bio, ())); ocd = o[0] if o else None
            elif ocd_uuid(pid):
                ocd = ocd_uuid(pid)
            elif re.match(r"\w\w-leg:", pid):
                official.add(pid); ocd = None
                if r.get("note", "").find("matched to OpenStates") >= 0: pass
            else:   # bare official id
                lid = "%s-leg:%s" % (ab, pid); official.add(lid)
                ch = "upper" if r["chamber"] in ("upper", "legislature") else "lower"
                cand = [u for u in ridx.get((ab, ch, fold(r["district"])), ()) if lastn(people[u]["name"]) == lastn(r["name"]) and first_initial(people[u]["name"]) == first_initial(r["name"])]
                if len(cand) == 1:
                    ocd = cand[0]; aliases.add(lid); stats["official_id_matched"] += 1
                    matches.append(dict(file=fn, state=r["state"], chamber=r["chamber"], district=r["district"], official_id=lid, official_name=r["name"],
                                        ocd_person="ocd-person:" + ocd, openstates_name=people[ocd]["name"], openstates_file=people[ocd]["file"], rule="same state+chamber+district label, same last name and first initial; unique"))
                else:
                    stats["official_id_kept"] += 1
                    matches.append(dict(file=fn, state=r["state"], chamber=r["chamber"], district=r["district"], official_id=lid, official_name=r["name"], ocd_person="",
                                        openstates_name="; ".join(people[u]["name"] for u in cand), openstates_file="", rule="no unique OpenStates person (%d candidates); kept %s" % (len(cand), lid)))
            if ocd and ocd in merged: aliases.add("ocd-person:" + ocd); ocd = merged[ocd]
            if ocd:
                for m, tgt in merged.items():
                    if tgt == ocd: aliases.add("ocd-person:" + m)
                bg = bioguide_of(ocd)
                if not bio and bg: bio = bg[0]; stats["stateleg_bioguide_canonical" if stateleg else "house_bioguide"] += 1
            cid = "bioguide:" + bio if bio else "ocd-person:" + ocd if ocd else sorted(official)[0]
            if cid.startswith("bioguide:") and ocd: aliases.add("ocd-person:" + ocd)
            if r.get("official_check") == "official" and r.get("source_id"): official.add("%s-leg:%s" % (ab, r["source_id"]))
            r["person_id"] = cid
            p = person(cid); p["bioguide"] = bio or p["bioguide"]; p["ocd_person"] = ("ocd-person:" + ocd) if ocd else p["ocd_person"]
            p["official_ids"] |= official; p["aliases"] |= aliases - {cid}; p["name"] = p["name"] or r["name"]; p["sources"].add(fn.replace(".csv", ""))
            fl = []
            if not r.get("term_start"): fl.append("term_start_missing")
            if not r.get("term_end"): fl.append("term_end_open")
            r["date_flags"] = ";".join(fl)
        if stateleg:   # units with no member row at all -> vacant row
            have = {(r["state"], "upper" if r["chamber"] in ("upper", "legislature") else "lower", r["unit_geoid"]) for r in rows if r["unit_geoid"]}
            tmpl = {c: "" for c in cols}
            for (st, ch), gs in units.items():
                for g in sorted(gs):
                    if (st, ch, g) in have or st.replace(" ", "_") not in L.ST: continue   # DC has no state legislature
                    ab = L.AB[L.ST.index(st.replace(" ", "_"))].lower()
                    rows.append(dict(tmpl, unit_geoid=g, unit_vintage="sldu2024" if ch == "upper" else "sldl2024", join_status="joined", entity_id="%s-%s" % (ab, "senate" if ch == "upper" else "house"),
                                     state=st, chamber=ch, status="vacant", note="no member listed for this unit by the row source (%s)" % ("official roster or OpenStates" if "current" in fn else "OpenStates at the 2025-04-01 snapshot"),
                                     official_check=""))
                    stats["vacant_rows_added_" + fn] += 1
            rows.sort(key=lambda x: (x["state"], x["chamber"], x["unit_geoid"] or "~", x["district"], x["name"]))
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
            for r in rows: w.writerow({c: r.get(c, "") for c in cols})
        stats["rows_" + fn] = len(rows); stats["vacant_" + fn] = sum(r["status"] == "vacant" for r in rows)
        stats["term_start_missing_" + fn] = sum("term_start_missing" in r["date_flags"] for r in rows)
        stats["term_end_open_" + fn] = sum("term_end_open" in r["date_flags"] for r in rows)
    with open(os.path.join(out, "persons.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["person_id", "bioguide", "ocd_person", "official_ids", "name", "sources", "aliases"]); w.writeheader()
        for cid in sorted(P):
            p = P[cid]; w.writerow(dict(p, official_ids=";".join(sorted(p["official_ids"])), sources=";".join(sorted(p["sources"])), aliases=";".join(sorted(p["aliases"]))))
    with open(os.path.join(out, "person_id_matches.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "state", "chamber", "district", "official_id", "official_name", "ocd_person", "openstates_name", "openstates_file", "rule"]); w.writeheader()
        for m in matches: w.writerow(m)
    S = dict(stats); S["persons"] = len(P); S["persons_with_aliases"] = sum(1 for p in P.values() if p["aliases"]); S["aliases"] = sum(len(p["aliases"]) for p in P.values())
    S["by_scheme"] = dict(collections.Counter(c.split(":")[0] for c in P))
    S["stateleg_persons_bioguide_canonical"] = sorted(c for c, p in P.items() if c.startswith("bioguide:") and any("stateleg" in s for s in p["sources"]))
    json.dump(S, open(os.path.join(out, "persons_summary.json"), "w"), indent=1)
    print(json.dumps(S, indent=1))

if __name__ == "__main__":
    main()
