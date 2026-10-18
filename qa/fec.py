import re,json,sys
L=open(sys.argv[1]).read().split('\n')
def col(word):
  out={}
  for i,l in enumerate(L):
    if l.startswith('STATE') and word in l:
      p=l.index(word); c=p+len(word)/2
      for l2 in L[i+1:i+60]:
        m=re.match(r'^([A-Z]{2})\s',l2)
        if not m: 
          if l2.startswith('Total'): break
          continue
        best=None
        for t in re.finditer(r'[\d,]{2,}',l2):
          d=abs((t.start()+t.end())/2-c)
          if d<12 and (best is None or d<best[0]): best=(d,int(t.group().replace(',','')))
        if best: out[m.group(1)]=best[1]
      break
  return out
w=sys.argv[2:]
print(json.dumps({k:col(k.replace('_',' ')) for k in w}))
