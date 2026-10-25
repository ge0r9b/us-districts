import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
for sz in b:
  A=a.get(sz,{}); B=b[sz]
  diffs=[k for k in B if k not in('lat','t','notes') and A.get(k)!=B.get(k)]
  lat=B.get('lat',{}); slow={k:v for k,v in lat.items() if isinstance(v,(int,float)) and v>100}
  print(sz,'diff_fields',diffs,'| slow',slow,'| layout',json.dumps(B.get('layout'))[:300],'| notes',json.dumps(B.get('notes'))[:300])
  for k in diffs[:6]: print('   ',k,'OLD',json.dumps(A.get(k))[:250],'NEW',json.dumps(B.get(k))[:250])
