import json,sys
d=json.load(open(sys.argv[1]))
for kk,R in d.items():
  print('##',kk,R['build'],'err',R.get('err'))
  print(' US map thumbs',[ (t['btn'][2:],t['img']) for t in R['US']['thumbs']])
  for st,A in R.items():
    if not isinstance(A,dict) or st=='US': continue
    if A.get('err'): print(' ',st,A['err'],A.get('menu'))
    for k in ('county','z1','z2','z3'):
      if k in A: m=A[k]['map']; print(' ',st,k,'z',m['z'],m['crumbs'],'lt',m['lt'],'paths',m['paths'],'canv',m['canv'],'ncol',A[k].get('ncol'),[ (t['btn'][2:],t['img']) for t in A[k].get('thumbs',[])])
  for k in ('US_list_thumbs_3s','US_list_thumbs'):
    if k in R: print(' ',k,[ (t['btn'][2:],t['img']) for t in R[k]])
