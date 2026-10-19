# hourly ~5PM (1618): __stTot 2020/2024 for all states vs FEC (certified compiled) + state-map thumbnails % and # for 8 states
import asyncio,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
NAMES=dict(AL='Alabama',AK='Alaska',AZ='Arizona',AR='Arkansas',CA='California',CO='Colorado',CT='Connecticut',DE='Delaware',DC='District of Columbia',FL='Florida',GA='Georgia',HI='Hawaii',ID='Idaho',IL='Illinois',IN='Indiana',IA='Iowa',KS='Kansas',KY='Kentucky',LA='Louisiana',ME='Maine',MD='Maryland',MA='Massachusetts',MI='Michigan',MN='Minnesota',MS='Mississippi',MO='Missouri',MT='Montana',NE='Nebraska',NV='Nevada',NH='New Hampshire',NJ='New Jersey',NM='New Mexico',NY='New York',NC='North Carolina',ND='North Dakota',OH='Ohio',OK='Oklahoma',OR='Oregon',PA='Pennsylvania',RI='Rhode Island',SC='South Carolina',SD='South Dakota',TN='Tennessee',TX='Texas',UT='Utah',VT='Vermont',VA='Virginia',WA='Washington',WV='West Virginia',WI='Wisconsin',WY='Wyoming')
TH8=['NV','NC','NH','MN','TX','CA','FL','OH']
async def main():
  f={'2024':json.load(open('fec24.json')),'2020':json.load(open('fec20.json'))}; out={'tot':{},'th':{}}
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000); out['build']=await pg.evaluate("window.BUILD")
    for ab,n in NAMES.items():
      for y in ['2020','2024']:
        try: v=await pg.evaluate("([n,y])=>window.__stTot(n,y)",[n,y])
        except Exception as e: v=str(e)[:80]
        F=f[y]; D,R=('HARRIS','TRUMP') if y=='2024' else ('BIDEN','TRUMP'); fo=[F[D][ab],F[R][ab],F['TOTAL_VOTES'][ab]]
        if isinstance(v,list): d=[v[i]-fo[i] for i in range(3)]; pc=[round(100*d[i]/fo[i],4) for i in range(3)]
        else: d=pc=None
        out['tot'][f'{ab}{y}']={'app':v,'fec':fo,'diff':d,'pct':pc}
    bad={k:v for k,v in out['tot'].items() if not v['diff'] or any(v['diff'])}
    print('nonzero',json.dumps(bad),flush=True)
    for ab in TH8:
      await c.close(); c,pg,log2=await ctx(b,390,844,True); log['pageerr']+=log2['pageerr']; log['console']+=log2['console']
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,NAMES[ab]); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      T=out['th'][ab]={'crumbs':await pg.evaluate("document.getElementById('crumbs').innerText")}
      for i,y in [(1,'2020'),(2,'2024')]:
        await pg.evaluate(f"()=>window.__ySetYr({i})"); await pg.wait_for_timeout(2000)
        T[y+'pct']=await pg.evaluate(TH)
        await pg.evaluate("()=>window.__setNum&&window.__setNum('num')"); await pg.wait_for_timeout(1500); T['nm']=await pg.evaluate("()=>window.__numMode()")
        T[y+'num']=await pg.evaluate(TH); await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000)
      await safeshot(pg,f"shotsh1700/b1618h7-ch-390x844-tot-{ab}.png")
      print(ab,json.dumps(T),flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]
    await b.close()
  json.dump(out,open('b1618h1700-tot-chromium-390x844.json','w'),indent=1)
asyncio.run(main())
