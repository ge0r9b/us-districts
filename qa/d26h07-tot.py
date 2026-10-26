# Oct 26 ~6 AM (1622): __stTot 2016/2020/2024 vs certified (FEC compiled from state offices) for 18 not-recently-covered states + UI thumbnails % and #
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('h1700-tot.py').read().split('TH8=')[0].split('from gaps import typegq')[1])
ST=['NV','NM','OR','KY','GA','FL','TX','IL','NJ','NY','MA','CT','RI','VT','HI','AK','CA','PA']
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]
  f={'2024':json.load(open('fec24.json')),'2020':json.load(open('fec20.json')),'2016':json.load(open('fec16.json'))}; out={'tot':{},'th':{}}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000); out['build']=await pg.evaluate("window.BUILD")
    for ab in ST:
      n=NAMES[ab]
      for y in ['2016','2020','2024']:
        try: v=await pg.evaluate("([n,y])=>window.__stTot(n,y)",[n,y])
        except Exception as e: v=str(e)[:80]
        F=f[y]
        if y=='2016': fo=[F[ab]['C'],F[ab]['T'],F[ab]['TOT']]
        else:
          D=('HARRIS' if y=='2024' else 'BIDEN'); fo=[F[D][ab],F['TRUMP'][ab],F['TOTAL_VOTES'][ab]]
        if isinstance(v,list): d=[v[i]-fo[i] for i in range(3)]; pc=[round(100*d[i]/fo[i],4) for i in range(3)]
        else: d=pc=None
        out['tot'][f'{ab}{y}']={'app':v,'fec':fo,'diff':d,'pct':pc}
        print(ab,y,v,fo,d,pc,flush=True)
    for ab in ST:
      await c.close(); c,pg,log2=await ctx(b,W,H,W<600,eng); log['pageerr']+=log2['pageerr']; log['console']+=log2['console']
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000)
      await typegq(pg,NAMES[ab]); await pg.wait_for_timeout(400); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      T=out['th'][ab]={'crumbs':await pg.evaluate("document.getElementById('crumbs').innerText")}
      for i,y in [(0,'2016'),(1,'2020'),(2,'2024')]:
        await pg.evaluate(f"()=>window.__ySetYr({i})"); await pg.wait_for_timeout(1800)
        T[y+'pct']=await pg.evaluate(TH)
        await pg.evaluate("()=>window.__setNum&&window.__setNum('num')"); await pg.wait_for_timeout(1200)
        T[y+'num']=await pg.evaluate(TH); await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(800)
      await safeshot(pg,f"../shots/b1622d26h07-{eng[:2]}-{W}x{H}-tot-{ab}.png")
      print(ab,json.dumps(T),flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]
    print('err',out['err'])
    await b.close()
  json.dump(out,open(f'b1622d26h07-tot-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
