import yaml, glob, os, json, collections
import openstates_metadata as M
TODAY = "2026-10-18"
ST50 = [a for a in M.STATES_BY_ABBR if a.upper() not in ("DC","PR","GU","VI","AS","MP","US","ZA")]
ST50 = sorted(a.upper() for a in ST50)
assert len(ST50) == 50, ST50
out = {}
for st in ST50:
    meta = M.lookup(abbr=st)
    chambers = {"legislature": meta.legislature} if meta.unicameral else {"upper": meta.upper, "lower": meta.lower}
    members = collections.defaultdict(list)
    for f in glob.glob(f"people/data/{st.lower()}/legislature/*.yml"):
        p = yaml.load(open(f), Loader=yaml.BaseLoader)
        for r in p.get("roles", []):
            if r.get("end_date") and r["end_date"] < TODAY: continue
            if r.get("start_date") and r["start_date"] > TODAY: continue
            if r["type"] not in chambers: continue
            party = [x for x in p.get("party", []) if not x.get("end_date") or x["end_date"] >= TODAY]
            members[r["type"]].append(dict(name=p["name"], district=str(r["district"]), party=party[-1]["name"] if party else None,
                id=p["id"], image=p.get("image"), start=r.get("start_date"), end=r.get("end_date"),
                links=[l["url"] for l in p.get("links", [])][:2], file=os.path.basename(f)))
    out[st] = {}
    for ch, c in chambers.items():
        seats = {d.name: d.num_seats for d in c.districts}
        mem = members[ch]
        byd = collections.Counter(m["district"] for m in mem)
        over = {d: n for d, n in byd.items() if n > seats.get(d, 0)}
        out[st][ch] = dict(name=c.name, num_seats=c.num_seats, title=c.title, members=mem, district_seats=seats, over=over)
json.dump(out, open("openstates_current.json", "w"), indent=0)
# summary
tot = 0
for st in ST50:
    for ch, d in out[st].items():
        pc = collections.Counter(m["party"] for m in d["members"])
        tot += d["num_seats"]
        flag = "" if len(d["members"]) <= d["num_seats"] else " OVER"
        print(st, ch, d["num_seats"], len(d["members"]), dict(pc), ("over:" + str(d["over"])) if d["over"] else "", flag)
print("total seats", tot)
