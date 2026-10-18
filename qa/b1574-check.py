import json,sys,re
f16=json.load(open('fec16.json')); f24=json.load(open('fec24.json')); f20=json.load(open('fec20.json'))
def m(yr,a):
  if yr==16: v=f16[a]; return (v['T']-v['C'])/v['TOT']*100, v['T']/v['TOT']*100, v['C']/v['TOT']*100, v['T'],v['C']
  f,dk=(f24,'HARRIS') if yr==24 else (f20,'BIDEN'); t=f['TOTAL_VOTES'][a]; return (f['TRUMP'][a]-f[dk][a])/t*100, f['TRUMP'][a]/t*100, f[dk][a]/t*100, f['TRUMP'][a], f[dk][a]
def num(s):
  s=s.replace('\u2212','-').replace('+','')
  mm=re.match(r'([RD]) ?(-?[\d.]+)',s)
  if mm: return (1 if mm.group(1)=='R' else -1)*float(mm.group(2))
  return float(s)
def check(rows,end):
  bad=[];n=0
  for r in rows:
    a=r[0]
    if a not in f16: continue
    try: app=num(r[1])
    except: bad.append((a,'unparsed',r)); continue
    exp=m(end,a)[0]-m(16,a)[0]; n+=1
    if abs(app-exp)>0.15: bad.append((a,'app',app,'exp',round(exp,2)))
  return n,bad
if __name__=='__main__':
  d=json.load(open(sys.argv[1]))
  for k,R in d.items():
    if 'States' not in R: continue
    end=24 if k.endswith('24') else 20
    print(k,'states margin',check(R['States']['all'],end))
