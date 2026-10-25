import json,glob,os
def mv(f):
  d=json.load(open(f)); o=[]
  for s in d['steps']:
    o.append((s['step'],sorted([(m['el'],m.get('dx'),m.get('dy'),m.get('dw'),m.get('dh')) if 'dx' in m else (m['el'],'gone' if 'gone' in m else 'new') for m in s.get('moved',[])],key=str),sorted(s.get('transient',{}).keys()), s.get('EXC')))
  return d,o
for f1 in sorted(glob.glob('b1618h1000-layout3-*.json')):
  k=f1.split('layout3-')[1]
  prev=[f for f in sorted(glob.glob('b16*-layout3-'+k),key=os.path.getmtime) if f!=f1]
  if not prev: print(k,'no prev'); continue
  f0=prev[-1]; d0,o0=mv(f0); d1,o1=mv(f1)
  print('==',k,'vs',f0,'build',d1.get('build'),'err',d1.get('err'),[x for x in d1.get('reqfail',[]) if 'arcgis' not in x][:3],'http',d1.get('http'))
  for x,y in zip(o0,o1):
    flag='SAME' if x[1:3]==y[1:3] else 'DIFF'
    if flag=='DIFF' or y[1]: print(flag,y[0],'now',y[1],y[2],y[3] or '','| was',x[1],x[2])
