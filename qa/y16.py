import asyncio,json,sys,re
from playwright.async_api import async_playwright
from common import *
from cmp import AB
from restore import slider_to, chart
ROWS="()=>{const rs=[...document.querySelectorAll('#listView .lvrow.la')];const v=rs.filter(r=>r.offsetParent);return {n:rs.length,nodigit:v.filter(r=>!/\\d/.test(r.innerText)).length,first:v.slice(0,6).map(r=>r.innerText.replace(/\\n/g,' | ').slice(0,90))}}"
PAGE="()=>({ym:window.__ymode(),chart:window.chartMode,lv:window.__laInfo().on?window.__laInfo().lv:'-',loading:/Loading 2016/.test(document.body.innerText),thumbs:[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')),cpanel:(()=>{const c=document.querySelector('.cpanel');return c?[getComputedStyle(c).display,c.getBoundingClientRect().height|0,c.innerText.replace(/\\n/g,' ').slice(0,120)]:null})(),hdr:(document.getElementById('crumbs')||{}).innerText})"
async def tapname(pg,n):
  return await pg.evaluate("n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n});if(!r)return false;r.querySelector('.nmx').click();return true}",n)
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2:]; o={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if sizes and tag not in sizes: continue
      s=tag.replace('iphone','').replace('ipad',''); R=o[tag]={}
      c,pg,log=await ctx(b,W,H,mob,eng); await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      sh=lambda n: pg.screenshot(path=f"../shots/b1571-{eng[:2]}-{s}-y16-{n}.png")
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      await slider_to(pg,0); await pg.wait_for_timeout(5000)
      R['states16']=[await pg.evaluate(PAGE),await pg.evaluate(ROWS)]; await sh('states-pct')
      if tag=='ipad1024x768':
        R['tot16']=await pg.evaluate("names=>{const o={};for(const [a,n] of Object.entries(names)){try{o[a]=window.__stTot(n,'2016')}catch(e){o[a]=String(e)}};return o}",AB)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
      R['states16num']=await pg.evaluate(ROWS); await sh('states-num')
      for k in ('pie','bar'):
        await chart(pg,k); R['chart16 '+k]=await pg.evaluate(PAGE); await sh('states-'+k)
        await slider_to(pg,0.5); await pg.wait_for_timeout(1500); R['chart16 '+k+' ->20']=(await pg.evaluate(PAGE))['chart']
        await slider_to(pg,1); await pg.wait_for_timeout(1500); R['chart16 '+k+' ->24']=(await pg.evaluate(PAGE))['chart']
        await slider_to(pg,0); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(9000)
      R['range']=[await pg.evaluate(PAGE),await pg.evaluate(ROWS)]; await sh('range')
      await chart(pg,'line'); R['range line']=(await pg.evaluate(PAGE))['chart']; await sh('range-line')
      await chart(pg,'bar'); await slider_to(pg,0); await pg.wait_for_timeout(4000)
      R['back16']=await pg.evaluate(PAGE)
      ok=await tapname(pg,'PA'); await pg.wait_for_timeout(7000)
      R['PA16']=[ok,await pg.evaluate(PAGE),await pg.evaluate(ROWS)]; await sh('PA-counties')
      ok=await tapname(pg,'Philadelphia'); 
      if not ok: ok=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la .nmx')].find(x=>/Philadelphia/.test(x.textContent));if(r){r.click();return r.textContent}return false}")
      await pg.wait_for_timeout(8000)
      R['Phila16']=[ok,await pg.evaluate(PAGE),await pg.evaluate(ROWS)]; await sh('phila')
      fr=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la .nmx')].filter(x=>x.offsetParent)[0];if(r){r.click();return r.textContent}return false}"); await pg.wait_for_timeout(8000)
      R['lvl4_16']=[fr,await pg.evaluate(PAGE),await pg.evaluate(ROWS)]; await sh('lvl4')
      R['err']=log['pageerr']+[x for x in log['console'] if 'error' in x][:5]; R['http']=log['http'][:5]
      await c.close(); print(tag,'done',flush=True)
    await b.close()
  json.dump(o,open(f'y16-{eng}.json','w'),indent=1)
  if 'ipad1024x768' in o and 'tot16' in o['ipad1024x768']:
    f=json.load(open('fec16.json')); bad=[]; app=o['ipad1024x768']['tot16']; sd=sr=0
    for a,v in app.items():
      if not isinstance(v,list): bad.append((a,'nodata',v)); continue
      sd+=v[0]; sr+=v[1]
      if v[0]!=f[a]['C'] or v[1]!=f[a]['T']: bad.append((a,v[:3],'fec C/T/TOT',f[a]['C'],f[a]['T'],f[a]['TOT'],'diff',v[0]-f[a]['C'],v[1]-f[a]['T']))
    print('2016 mismatches',len(bad)); [print(x) for x in bad]; print('app sums D R',sd,sr)
asyncio.run(main())
