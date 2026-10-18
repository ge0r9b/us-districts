# b1583: QA-046 recount with the live ±90 clamp (marginColor stops end at ±0.9). Same method as b1575-clamp.py.
import re,os,json,collections,sys
D=sys.argv[1] if len(sys.argv)>1 else '/tmp/b1574/p24'
CL=float(os.environ.get('CL','0.9'))
row=re.compile(r'\["((?:[^"\\]|\\.)*)","((?:[^"\\]|\\.)*)",(\d+),(\d+),(\d+)')
out={}; allc=[]
for fn in sorted(os.listdir(D)):
  st=fn[:-3].replace('_',' ')
  s=open(os.path.join(D,fn)).read()
  C=collections.defaultdict(list)
  for cn,nm,d,r,t in row.findall(s):
    d,r,t=int(d),int(r),int(t)
    if t<=0: continue
    C[cn].append((r-d)/t)
  solid=[]
  for cn,ms in C.items():
    n=len(ms); R=sum(1 for m in ms if m>=CL); Dm=sum(1 for m in ms if m<=-CL); k=max(R,Dm); side='R' if R>=Dm else 'D'
    rec={'state':st,'county':cn,'n':n,'clamped':k,'side':side,'minabs':round(min(abs(m) for m in ms)*100,1)}
    allc.append(rec)
    if n>=2 and k>=n-1: solid.append(rec)
  out[st]={'counties':len(C),'solid':len(solid),'all':sum(1 for x in solid if x['clamped']==x['n']),'list':sorted(solid,key=lambda x:-x['n'])}
json.dump(out,open('b1583-clamp90.json','w'),indent=1)
tot=sum(v['solid'] for v in out.values()); print('states',len(out),'solid counties (all or all-but-one precincts beyond the clamp, n>=2):',tot)
for st,v in sorted(out.items(),key=lambda kv:-kv[1]['solid']): print(f"{st}: {v['solid']} of {v['counties']} ({v['all']} all) "+', '.join(f"{x['county']} {x['clamped']}/{x['n']}{x['side']}" for x in v['list'][:6]))
worst=sorted([x for x in allc if x['n']>=2 and x['clamped']>=x['n']-1],key=lambda x:(-(x['clamped']==x['n']),-x['n']))[:10]
print('WORST10'); [print(x) for x in worst]
