import json,sys
for f in sys.argv[1:]:
  print('==',f)
  for l in open(f):
    if ' {' not in l: print(l[:200]); continue
    k,j=l.split(' ',1)
    try: R=json.loads(j)
    except: print(k,'TRUNC'); continue
    def s(x):
      if not isinstance(x,dict): return str(x)[:150]
      sn=json.loads(x['snap']) if x.get('snap') else {}
      sel=sn.get('sel') or {}
      return f"crumbs={x['hdr'].get('crumbs')!r} th={[t.split(' / ')[-1] for t in x['th']]} fld={x['hdr'].get('gq')!r} sel={sel.get('k')}:{sel.get('co')}/{sel.get('p')} ll={sn.get('ll')} pop={x['pop'][:1]}"
    print(k,'| sugg',R.get('sugg',[])[:1])
    for kk in ['res','tomap','reload']:
      if kk in R: print('   ',kk,s(R[kk]))
    print('    popc',R.get('popc'),'| after',R.get('after_pop',{}).get('hdr',{}).get('crumbs') if isinstance(R.get('after_pop',{}).get('hdr'),dict) else R.get('after_pop'),'err',R.get('err'))
