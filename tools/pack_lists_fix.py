#!/usr/bin/env python3
"""Build data-v3/inst/pack_lists_fix.json: a mechanical patch for PACK.lists in v2/index.html (orchestrator applies it;
this lane never edits index.html), and verify it on a copy of PACK.lists in /tmp.

usage: python3 tools/pack_lists_fix.py <repo checkout of data/geo> [--out data-v3/inst/pack_lists_fix.json]

Patch semantics (apply in this order to PACK.lists):
 1. schools.rename: for each entry, the k-th row (0-based, counting in array order) of PACK.lists.schools equal to
    [state, type, old_name] gets name := new_name.  `index` is also given (array position in the unpatched list).
 2. schools.remove: delete rows equal to [state, type, name] (all are 'School District Not Defined'); `index` given.
 3. statehouse.insert: insert `rows` (in order) at array position `insert_at` of the unpatched statehouse list
    (right after the last Montana row, before the first Nevada row; the list is sorted by state).
Result (checked here): schools (state, name) set == v2/data/ussch.js exactly (13,304 rows, no duplicates), PACK type ==
TIGER 2024 set of the row (data-v3/geo/schools.csv); statehouse Nebraska rows == the 49 ussldl.js Nebraska codes.
"""
import argparse, collections, csv, json, os, sys

def pack_lists(repo):
    for line in open(os.path.join(repo, "v2", "index.html"), encoding="utf-8"):
        if line.startswith("const PACK = { lists:"):
            return json.JSONDecoder().raw_decode(line, line.index('{"localities"'))[0]
    raise SystemExit("PACK.lists not found")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("repo")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data-v3", "inst", "pack_lists_fix.json"))
    a = ap.parse_args(); R = a.repo
    sys.path.insert(0, os.path.join(R, "tools")); import coverage_audit as ca
    P = pack_lists(R)
    json.dump(P, open("/tmp/pack_lists_orig.json", "w"), ensure_ascii=False)
    sch = ca.jsargs(os.path.join(R, "v2/data/ussch.js"), r'__usdist\("schools",')[0]
    data = [(r[0], r[1]) for r in sch]
    tset = {(r["state"], r["v2_name"]): r["tiger_set"] for r in csv.DictReader(open(os.path.join(R, "data-v3/geo/schools.csv")))}
    T = {"unsd": "unified", "elsd": "elementary", "scsd": "secondary"}
    col = list(csv.DictReader(open(os.path.join(R, "data-v3/geo/v2_name_collisions.csv"))))
    # group renames by (state, old_name, type)
    want = collections.defaultdict(list)
    for r in col: want[(r["state"], r["old_name"], T[tset[(r["state"], r["new_name"])]])].append(r)
    for k in want: want[k].sort(key=lambda r: int(r["row"]))  # ussch.js order
    seen = collections.Counter(); renames = []
    dset = set(data)
    for i, (st, ty, nm) in enumerate(P["schools"]):
        k = (st, nm, ty)
        if k in want:
            j = seen[k]; seen[k] += 1
            r = want[k][j]
            renames.append({"index": i, "state": st, "type": ty, "old_name": nm, "occurrence": j, "new_name": r["new_name"], "geoid": r["geoid"], "source": "v2_name_collisions.csv (9ff4c00)"})
        elif (st, nm) not in dset and nm != "School District Not Defined":
            # mojibake: UTF-8 bytes read as Latin-1
            try: fixed = nm.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError): fixed = None
            if fixed and (st, fixed) in dset:
                renames.append({"index": i, "state": st, "type": ty, "old_name": nm, "occurrence": 0, "new_name": fixed, "geoid": next((g["geoid"] for g in csv.DictReader(open(os.path.join(R, "data-v3/geo/schools.csv"))) if g["state"] == st and g["v2_name"] == fixed), ""), "source": "mojibake (UTF-8 read as Latin-1) -> v2/data/ussch.js name"})
    for k, v in want.items():
        if seen[k] != len(v): raise SystemExit("rename group not fully matched: %r %d/%d" % (k, seen[k], len(v)))
    remove = [{"index": i, "state": r[0], "type": r[1], "name": r[2]} for i, r in enumerate(P["schools"]) if r[2] == "School District Not Defined"]
    sh = P["statehouse"]
    last_mt = max(i for i, r in enumerate(sh) if r[0] == "Montana")
    ne_rows = [r for r in ca.jsargs(os.path.join(R, "v2/data/ussldl.js"), r'__usdist\("statehouse",')[0] if r[0] == "Nebraska"]
    ne_rows.sort(key=lambda r: int(r[1]))
    tname = {r["v2_name"]: r["tiger_name"] for r in csv.DictReader(open(os.path.join(R, "data-v3/geo/statehouse.csv"))) if r["state"] == "Nebraska"}
    ins = [["Nebraska", r[1], tname[r[1]]] for r in ne_rows]
    fix = {
      "for": "PACK.lists in v2/index.html (const PACK = { lists: ... } on one line); apply schools.rename, then schools.remove, then statehouse.insert",
      "built_from": os.popen("git -C %s log -1 --format='%%h %%s'" % R).read().strip(),
      "schools": {"rename": renames, "remove": remove},
      "statehouse": {"insert_at": last_mt + 1, "after": sh[last_mt], "before": sh[last_mt + 1], "rows": ins,
                     "label_source": "TIGER 2024 SLDU NAME (Nebraska is unicameral; same label as PACK.lists.senate Nebraska rows)"},
      "at_large_label": {
        "where": "v2/index.html, the national-district aname override in the '===== every district type fills nationwide' block (line ~2845 at build 1568): "
                 "{ const _an18=aname; aname=function(a){ if(a.kind!==\"natcd\") return _an18(a); const k=a.tk||\"ushouse\"; return k===\"schools\"?a.d[1]:\"District \"+String(a.d[1]).replace(/^0+(?=\\d)/,\"\"); }; }",
        "expression": "\"District \"+String(a.d[1]).replace(/^0+(?=\\d)/,\"\")  -> for code \"00\" the regex strips one leading 0 (the next char is a digit) and leaves \"0\": \"District 0\"",
        "affects": "US House rows with code \"00\": Alaska, Delaware, North Dakota, South Dakota, Vermont, Wyoming (uscd.js; TIGER 2024 GEOID SS00 = at-large). Earlier override at line ~2635 (\"District \"+a.d[1]) would give \"District 00\" but is shadowed by the one above.",
        "suggested_change": "k===\"ushouse\"&&String(a.d[1])===\"00\"?\"At large\":... (PACK.lists.ushouse already labels these rows \"At large\"; House Clerk MemberData.xml uses district \"At Large\"). 0 bytes of data.",
        "verified": "node -e 'console.log(\"District \"+String(\"00\").replace(/^0+(?=\\d)/,\"\"))' prints District 0"},
    }
    # ---- verify on a copy ----
    Q = json.load(open("/tmp/pack_lists_orig.json"))
    S = [list(r) for r in Q["schools"]]
    for r in fix["schools"]["rename"]:
        assert S[r["index"]] == [r["state"], r["type"], r["old_name"]], r
        S[r["index"]][2] = r["new_name"]
    rm = {r["index"] for r in fix["schools"]["remove"]}
    for i in rm: assert S[i][2] == "School District Not Defined"
    S = [r for i, r in enumerate(S) if i not in rm]
    H = Q["statehouse"][:fix["statehouse"]["insert_at"]] + fix["statehouse"]["rows"] + Q["statehouse"][fix["statehouse"]["insert_at"]:]
    pk = [(r[0], r[2]) for r in S]
    ok_s = len(S) == len(data) and collections.Counter(pk) == collections.Counter(data)
    tmis = sum(1 for r in S if T[tset[(r[0], r[2])]] != r[1])
    ne_ok = [r[1] for r in H if r[0] == "Nebraska"] == [r[1] for r in ne_rows] and len(ne_rows) == 49
    sorted_ok = all(H[i][0] <= H[i + 1][0] for i in range(len(H) - 1))
    shk = {(r[0], r[1]) for r in H}
    sh_data = {(r[0], r[1]) for r in ca.jsargs(os.path.join(R, "v2/data/ussldl.js"), r'__usdist\("statehouse",')[0]}
    fix["verification"] = {"schools_rows_after": len(S), "ussch_rows": len(data), "schools_exact_match": ok_s, "type_mismatches": tmis,
                           "renames": len(renames), "renames_collisions": sum(1 for r in renames if r["source"].startswith("v2_name")), "renames_mojibake": sum(1 for r in renames if r["source"].startswith("mojibake")),
                           "removed": len(rm), "statehouse_rows_after": len(H), "statehouse_equals_ussldl_keys": shk == sh_data,
                           "nebraska_rows": sum(1 for r in H if r[0] == "Nebraska"), "nebraska_match": ne_ok, "statehouse_sorted_by_state": sorted_ok,
                           "schools_bytes_before_after": [len(json.dumps(Q["schools"], ensure_ascii=False, separators=(",", ":")).encode()), len(json.dumps(S, ensure_ascii=False, separators=(",", ":")).encode())],
                           "statehouse_bytes_before_after": [len(json.dumps(Q["statehouse"], ensure_ascii=False, separators=(",", ":")).encode()), len(json.dumps(H, ensure_ascii=False, separators=(",", ":")).encode())]}
    json.dump({"schools": S, "statehouse": H}, open("/tmp/pack_lists_patched.json", "w"), ensure_ascii=False)
    json.dump(fix, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(fix["verification"], indent=1))
    if not (ok_s and tmis == 0 and ne_ok and shk == sh_data): sys.exit(1)

if __name__ == "__main__":
    main()
