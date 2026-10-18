import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from flow import LAYOUT
# What the sort chip (#laSort) and back chevron (#bBack) cover in the first rows, plus positions of the fixed elements for stability
COV="""()=>{const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'&&cs.opacity!=='0'};
 const R=s=>{const e=document.querySelector(s);if(!e||!vis(e))return null;const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};
 const chips=[['sort','#laSort'],['back','#bBack']].map(([k,s])=>[k,document.querySelector(s)]).filter(([k,e])=>e&&vis(e));
 const lv=document.getElementById('listView'); const rows=[...document.querySelectorAll('#listView .lvgrid > .lvrow, #listView .lvrow')].filter(vis).slice(0,3);
 const cov=[];
 for(const row of rows){ const leaves=[...row.querySelectorAll('*')].filter(e=>vis(e)&&(e.childElementCount===0||e.tagName==='svg'||e.tagName==='IMG'||e.tagName==='CANVAS'));
  for(const e of leaves){const r=e.getBoundingClientRect(); for(const [k,c] of chips){const q=c.getBoundingClientRect();const ix=Math.min(r.right,q.right)-Math.max(r.left,q.left), iy=Math.min(r.bottom,q.bottom)-Math.max(r.top,q.top);
    if(ix>1&&iy>1){const t=(e.textContent||'').trim().slice(0,14)||e.tagName+'.'+(e.getAttribute('class')||'').toString().slice(0,15); cov.push(k+': '+t+' '+Math.round(ix)+'x'+Math.round(iy)+'/'+Math.round(r.width)+'x'+Math.round(r.height))}}}}
 const r0=rows[0]&&rows[0].getBoundingClientRect();
 return {sort:R('#laSort'),back:R('#bBack'),thumbs:R('#laCands'),geo:R('#barGeo'),time:R('#barTime'),slider:R('#yslider')||R('.trk'),chart:R('#chartBox .cmain'),bottom:R('#bottomBar')||R('.bbar'),
   row0:r0?[Math.round(r0.left),Math.round(r0.top),Math.round(r0.right),Math.round(r0.bottom)]:null,row0txt:rows[0]?rows[0].innerText.replace(/\\n/g,' | ').slice(0,60):null,cov:[...new Set(cov)].slice(0,14),st:lv?lv.scrollTop:null}}"""
async def chart(pg,k):
  await pg.evaluate("()=>document.querySelector('#chartBox .cmain').click()"); await pg.wait_for_timeout(700)
  await pg.evaluate("k=>{const b=document.querySelector('#chartBox .copts button[data-ch='+k+']'); if(b) b.click(); else document.body.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2:]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      s=tag.replace('iphone','').replace('ipad','')
      if sizes and s not in sizes: continue
      try:
        c,pg,log=await ctx(b,W,H,mob,eng); await pg.goto(URL,wait_until="networkidle",timeout=90000); await pg.wait_for_timeout(4000)
        out[tag+' build']=await pg.evaluate("()=>window.BUILD")
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
        await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
        async def rec(name,shot=True):
          await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(500)
          r=await pg.evaluate(COV); r['lay']=await pg.evaluate(LAYOUT); r['mode']=await pg.evaluate("()=>window.chartMode"); out[f'{tag} {name}']=r
          if shot: await safeshot(pg,f"../shots/b1575-{eng[:2]}-{s}-{name}.png")
        for lvl in ('states','PA','Phila'):
          if lvl=='PA':
            await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()==='PA'});r.querySelector('.nmx').click()}"); await pg.wait_for_timeout(6000)
          if lvl=='Phila':
            await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&/Philadelphia/.test(x.textContent)});r.querySelector('.nmx').click()}"); await pg.wait_for_timeout(6000)
          for nm in ('pct','num'):
            await pg.evaluate("m=>window.__setNum(m)",nm); await pg.wait_for_timeout(1200)
            await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(2000)
            for k in ('bar','pie'):
              await chart(pg,k); await rec(f'{lvl}-{nm}-{k}', k=='bar' or lvl=='states')
            await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(2500)
            for k in ('line','bar'):
              await chart(pg,k); await rec(f'{lvl}-{nm}-range{k}')
        # back to states via back chevron, record position
        for i in range(2):
          await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(4000)
        await rec('back-states')
        out[tag+' err']=log['pageerr']+log['console']; await c.close(); print(tag,'done',flush=True)
      except Exception as e:
        print(tag,'FAIL',str(e)[:200],flush=True)
        try: await c.close()
        except: pass
    await b.close()
  json.dump(out,open(f'b1575-rows-{eng}-{"_".join(sizes) or "all"}.json','w'),indent=1)
asyncio.run(main())
