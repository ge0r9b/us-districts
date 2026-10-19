import json,sys
d=json.load(open(sys.argv[1]))
for tag,R in d.items():
  slow={k:v for k,v in R['lat'].items() if v is None or v>100}
  lay={k:v for k,v in R['layout'].items() if any(v.values())}
  print(tag,'slow',slow,'notes',R['notes'][:4])
  print('  layout issues',json.dumps(lay)[:400])
  for k in ['county_rows','ushouse_rows','restore','addr_sugg','rows_default','err','log','cls','shifts']:
    if k in R: print('  ',k,json.dumps(R[k])[:300])
  print('  keys-extra',[k for k in R if k not in ('lat','layout','notes','t')][-8:])
