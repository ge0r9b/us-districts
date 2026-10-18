#!/usr/bin/env python3
"""Append 2016 [d,r,t] triples to the existing rows of v2's shared district files without reordering or editing them.
Row format before: [st, name, polys, v2024, v2020(, flag)]. After: [st, name, polys, v2024, v2020, flag|null, v2016|null(, "e16")].
"e16" = 2016 value is area-weighted (show ≈). null = no 2016 source (gray). Matching is by (state, name) on the file as it is now,
so run it after rebasing on the latest main (Geo renames school duplicates to 'Name (County)'). Idempotent: re-running replaces
the 2016 slots. Values come from build_layers2016.py (data-v3/results/2016/out/ds2016.js, keys 'State|Name').
usage: append2016.py <repo> <ds2016.js> [--check]"""
import sys,json,os
repo,dsf=sys.argv[1:3]
t=open(dsf).read(); DS=json.loads(t[t.index('(')+1:t.rindex(')')]); check='--check' in sys.argv
FILES={'ushouse':'v2/data/uscd.js','senate':'v2/data/ussldu.js','statehouse':'v2/data/ussldl.js','schools':'v2/data/ussch.js'}
for lay,f in FILES.items():
  vals=DS[lay]
  p=f'{repo}/{f}'; t=open(p).read(); i=t.index('[['); rows,end=json.JSONDecoder().raw_decode(t,i)
  keys=set(); hit=est=0
  for r in rows:
    k=r[0]+'|'+r[1]; keys.add(k)
    del r[6:]
    while len(r)<6: r.append(None)
    v=vals.get(k)
    if v is None: r.append(None); continue
    hit+=1; r.append(v[:3])
    if len(v)>3: r.append('e16'); est+=1
  # trim a trailing null flag only when nothing follows (keeps rows lean): never needed since slot 6 always exists
  orphans=[k for k in vals if k not in keys]
  out=t[:i]+json.dumps(rows,separators=(',',':'))+t[end:]
  print(f'{lay}: rows {len(rows)}, 2016 filled {hit}, e16 {est}, gray {len(rows)-hit}, orphan 2016 keys {len(orphans)} {orphans[:5]}, bytes {len(t)} -> {len(out)} (+{len(out)-len(t)})')
  if not check: open(p,'w').write(out)
