import json,sys
def mv(f):
  d=json.load(open(f)); o=[]
  for s in d['steps']:
    o.append((s['step'],sorted([(m['el'],m.get('dx'),m.get('dy'),m.get('dw'),m.get('dh')) if 'dx' in m else (m['el'],'gone' if 'gone' in m else 'new') for m in s.get('moved',[])],key=str),sorted(s.get('transient',{}).keys()), s.get('EXC')))
  return d,o
for a,b in [('chromium-390','chromium-390'),('chromium-320','chromium-320'),('chromium-1024x768','chromium-1024x768'),('webkit-375','webkit-375'),('webkit-1024x576','webkit-1024x576')]:
  try:
    d0,o0=mv(f'b1618h1600-layout3-{a}.json'); d1,o1=mv(f'b1618h1700-layout3-{b}.json')
  except Exception as e: print(a,'missing',e); continue
  print('==',b,'build',d1.get('build'),'err',d1.get('err'),'reqfail',len(d1.get('reqfail',[])),[x for x in d1.get('reqfail',[]) if 'arcgis' not in x][:3],'http',d1.get('http'))
  for x,y in zip(o0,o1):
    flag='SAME' if x[1:3]==y[1:3] else 'DIFF'
    if flag=='DIFF' or y[1]: print(flag,y[0],'now',y[1],y[2],y[3] or '','| was',x[1],x[2])
