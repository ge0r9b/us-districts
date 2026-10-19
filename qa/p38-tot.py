# pass 38: __stTot 2020/2024 for fresh states vs FEC (certified compiled) tables
import asyncio,json
from playwright.async_api import async_playwright
from common import *
S=dict(GA='Georgia',NC='North Carolina',OH='Ohio',MI='Michigan',AZ='Arizona',WI='Wisconsin',NV='Nevada',SC='South Carolina',TN='Tennessee',KY='Kentucky',IN='Indiana',MO='Missouri')
async def main():
  f={'2024':json.load(open('fec24.json')),'2020':json.load(open('fec20.json'))}; out={}
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000); out['build']=await pg.evaluate("window.BUILD")
    for ab,n in S.items():
      for y in ['2020','2024']:
        v=await pg.evaluate("([n,y])=>window.__stTot(n,y)",[n,y]); F=f[y]; D,R=('HARRIS','TRUMP') if y=='2024' else ('BIDEN','TRUMP')
        fo=[F[D][ab],F[R][ab],F['TOTAL_VOTES'][ab]]
        # __stTot order: [dem, rep, total]? detect
        d=[v[i]-fo[i] for i in range(3)]; pc=[round(100*d[i]/fo[i],4) for i in range(3)]
        out[f'{ab}{y}']={'app':v,'fec':fo,'diff':d,'pct':pc}; print(ab,y,v,fo,d,pc,flush=True)
    await b.close()
  json.dump(out,open('b1616p38-tot-chromium-390x844.json','w'),indent=1)
asyncio.run(main())
