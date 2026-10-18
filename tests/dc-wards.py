# Build 1556: District of Columbia under the district types. DC has no state legislature: its 8 Council wards stand in for
# state house AND state senate districts, DCPS is its one school district. Official DCBOE certified ward totals, 2024 + 2020
# (no "no data" DC row in All States; tapping DC lists its wards / DCPS; back returns to All States).
import asyncio,sys,json,re
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
# official DCBOE certified results by ward [Harris/Biden, Trump]
W24={1:(36882,2056),2:(33571,2982),3:(39521,3544),4:(38628,2511),5:(41413,2309),6:(43262,3638),7:(33972,2092),8:(26936,1944)}
W20={1:(39041,1725),2:(29078,2918),3:(39397,3705),4:(42489,1913),5:(43320,1769),6:(56719,4337),7:(36382,1134),8:(30897,1085)}
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent).map(r=>({n:r.querySelector('.nmx').textContent.trim(),nd:/no\\s+(data|'\\d\\d data)/i.test(r.innerText),sg:[...r.querySelectorAll('.sg')].map(s=>s.innerText.trim())}))"
num=lambda t:int(re.sub(r'[^0-9]','',t) or 0)
async def setyr(pg,v): await pg.evaluate("v=>{const y=document.getElementById('yslider'); y.value=v; y.dispatchEvent(new Event('input',{bubbles:true}))}",v); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for k in ("statehouse","senate","schools"):
      c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("(k)=>document.querySelector('.lbtn[data-k='+k+']').click()",k); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      for yv,yr in ((2,'2024'),(0,'2020')):
        await setyr(pg,yv); await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
        dc=[r for r in await pg.evaluate(ROWS) if r['n']=='DC']
        ck(len(dc)==1 and not dc[0]['nd'] and any('%' in s for s in dc[0]['sg']),f"{k} {yr}: All States has a DC bar (not 'no data')",dc)
      await setyr(pg,2)
      await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='DC').click()"); await pg.wait_for_timeout(5000)
      info=await pg.evaluate("()=>({lv:window.__laInfo().lv,crumb:[...document.querySelectorAll('#crumbs .crumb.cur')].pop().textContent,noun:[...document.querySelectorAll('#crumbs .crumb.cur')].pop().getAttribute('data-noun'),back:window.__backDepth()})")
      ck(info['lv']=='dcdist' and info['crumb']=='District of Columbia' and info['noun']==('school districts' if k=='schools' else 'wards'),f"{k}: tapping DC lists District of Columbia {info['noun']}",info)
      if k=='schools':
        r=await pg.evaluate(ROWS); ck(len(r)==1 and r[0]['n'].startswith('District of Columbia Public') and not r[0]['nd'],"schools: DC = one district, DCPS, with data",r)
        await pg.screenshot(path='/workspace/dcw/dc-dcps-1556.png')
      else:
        for yv,yr,ref in ((2,'2024',W24),(0,'2020',W20)):
          await setyr(pg,yv); await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
          r=await pg.evaluate(ROWS); names=sorted(x['n'] for x in r)
          ck(names==['Ward %d'%i for i in range(1,9)] and not any(x['nd'] for x in r),f"{k} {yr}: 8 wards (Ward 1-8), all with data",r)
          ds=await pg.evaluate("([k,yr])=>Array.from({length:8},(_,i)=>{const x=window.__dsRow(k,['District of Columbia','Ward '+(i+1)]); return x&&x.v&&x.v[yr]?x.v[yr].slice(0,2):null})",[k,yr])
          ck(ds==[list(ref[i]) for i in range(1,9)],f"{k} {yr}: ward data = DCBOE certified ward totals (Dem, Rep)",ds)
          lab={x['n']:[s for s in x['sg'] if s] for x in r}
          bad=[n for n,v in lab.items() if not any(s.endswith('K') and abs(float(s[:-1])*1000-ref[int(n[5:])][0])<=500 for s in v)]
          ck(not bad,f"{k} {yr}: # mode bars label each ward's Democratic votes (rounded K)",[lab,bad])
        await setyr(pg,2); await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
        if k=='statehouse': await pg.screenshot(path='/workspace/dcw/dc-wards-1556.png')
      await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(5000)
      i2=await pg.evaluate("()=>({lv:window.__laInfo().lv,dc:[...document.querySelectorAll('#listView .lvrow.la .nmx')].some(e=>e.textContent==='DC')})")
      ck(i2['lv']=='states' and i2['dc'],f"{k}: back returns to All States",i2)
      ck(not er,f"{k}: no page errors",er[:2]); await c.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
