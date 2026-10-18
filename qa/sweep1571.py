import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from flow import LAYOUT
# extra: overlapping text leaves inside the list (text vs text)
TT="""()=>{const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.opacity!=='0'&&r.bottom>0&&r.top<innerHeight};
 const L=[...document.querySelectorAll('#listView *, .cpanel *, #laCands *')].filter(e=>e.childElementCount===0&&(e.textContent.trim()||e.tagName=='text')&&vis(e)).map(e=>[e,e.getBoundingClientRect()]);
 const out=[];for(let i=0;i<L.length;i++)for(let j=i+1;j<L.length;j++){const a=L[i][1],b=L[j][1];const ix=Math.min(a.right,b.right)-Math.max(a.left,b.left),iy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);if(ix>2&&iy>2&&!L[i][0].contains(L[j][0])&&!L[j][0].contains(L[i][0]))out.push(L[i][0].textContent.trim().slice(0,12)+' / '+L[j][0].textContent.trim().slice(0,12))}
 const trunc=[...document.querySelectorAll('#listView .nmx')].filter(vis).filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent.trim().slice(0,20));
 return {tt:[...new Set(out)].slice(0,10),trunc:trunc.slice(0,6),ntrunc:trunc.length}}"""
async def chart(pg,k):
  await pg.evaluate("()=>document.querySelector('#chartBox .cmain').click()"); await pg.wait_for_timeout(700)
  await pg.evaluate("k=>{const b=document.querySelector('#chartBox .copts button[data-ch='+k+']'); if(b) b.click(); else document.body.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  eng=sys.argv[1]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      s=tag.replace('iphone','').replace('ipad','')
      c,pg,log=await ctx(b,W,H,mob,eng); await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
      for lvl in ('states','PA'):
        if lvl=='PA':
          await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()==='PA'});r.querySelector('.nmx').click()}"); await pg.wait_for_timeout(6000)
        for nm in ('pct','num'):
          await pg.evaluate("m=>window.__setNum(m)",nm); await pg.wait_for_timeout(1200)
          # single year -> bar, pie ; range -> line, bar
          await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(2000)
          for k in ('bar','pie'):
            await chart(pg,k); await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(600)
            r=await pg.evaluate(LAYOUT); r.update(await pg.evaluate(TT)); r['mode']=await pg.evaluate("()=>window.chartMode")
            out[f'{tag} {lvl} {nm} {k}']=r; await pg.screenshot(path=f"../shots/b1571-{eng[:2]}-{s}-sw-{lvl}-{nm}-{k}.png")
          await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(2500)
          for k in ('line','bar'):
            await chart(pg,k); await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(600)
            r=await pg.evaluate(LAYOUT); r.update(await pg.evaluate(TT)); r['mode']=await pg.evaluate("()=>window.chartMode")
            out[f'{tag} {lvl} {nm} range-{k}']=r; await pg.screenshot(path=f"../shots/b1571-{eng[:2]}-{s}-sw-{lvl}-{nm}-range{k}.png")
      out[tag+' err']=log['pageerr']+log['console']; await c.close(); print(tag,'done',flush=True)
    await b.close()
  json.dump(out,open(f'sweep-{eng}.json','w'),indent=1)
  for k,v in out.items():
    if isinstance(v,dict):
      bad={a:b for a,b in v.items() if b and a not in('mode','ntrunc')}
      if bad: print(k,v.get('mode'),'ntrunc',v.get('ntrunc'),json.dumps(bad)[:500])
    elif v: print(k,v[:3])
asyncio.run(main())
