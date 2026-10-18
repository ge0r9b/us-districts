# pass 13: which numeric labels in list rows are covered by the sort chip, back chevron, or right-hand buttons
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
COV="""()=>{const vis=e=>{if(!e)return false;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&+cs.opacity>0};
 const covs=[['sort','#laSort'],['back','#bBack'],['time','#bTime'],['chart','#chartBox .cmain'],['lyr','#bLyr'],['num','#bNum'],['globe','#bGlobe'],['search','#bSearch'],['geoBar','#barGeo']].map(([k,s])=>[k,document.querySelector(s)]).filter(([k,e])=>vis(e)).map(([k,e])=>[k,e.getBoundingClientRect()]);
 const out=[];const rows=[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent);
 for(const row of rows.slice(0,12)){const w=document.createTreeWalker(row,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){const t=n.textContent.trim();if(!t)continue;const rg=document.createRange();rg.selectNodeContents(n);const r=rg.getBoundingClientRect();if(!r.width)continue;
  if(r.bottom<0||r.top>innerHeight)continue;
  for(const [k,c] of covs){const ix=Math.min(r.right,c.right)-Math.max(r.left,c.left),iy=Math.min(r.bottom,c.bottom)-Math.max(r.top,c.top);if(ix>2&&iy>2)out.push({row:row.innerText.split('\\n')[0].trim().slice(0,20),text:t.slice(0,24),by:k,px:[Math.round(ix),Math.round(iy)],r:[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]})}}}
 return {crumb:document.getElementById('crumbs').innerText.replace(/\\n/g,' '),n:rows.length,first:rows[0]?rows[0].innerText.replace(/\\n/g,' | ').slice(0,90):null,cov:out}}"""
async def main():
  eng=sys.argv[1]; res={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      c,pg,log=await ctx(b,W,H,mob,eng); R=res[tag]={}
      await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__map&&document.getElementById('state').options.length>40",timeout=90000); await pg.wait_for_timeout(3500)
      R['build']=await pg.evaluate('window.BUILD')
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
      async def probe(k):
        R[k]=await pg.evaluate(COV); await safeshot(pg,f"../shots/b1582p14-{eng[:2]}-{tag.replace('iphone','').replace('ipad','')}-lbl-{k}.png")
        print(tag,k,R[k]['crumb'],R[k]['n'],[(x['row'],x['text'],x['by'],x['px']) for x in R[k]['cov']][:8],flush=True)
      await probe('states-pct')
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(900)
      await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.querySelector('#chartBox .cmain').click()"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>{const b=document.querySelector('#chartBox .copts button[data-ch=line]'); b&&b.click()}"); await pg.wait_for_timeout(3000)
      await probe('states-rline-pct')
      await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(2000); await probe('states-rline-num')
      await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>{const b=document.querySelector('#chartBox .cmain');b.click()}"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>{const b=document.querySelector('#chartBox .copts button[data-ch=bar]'); b&&b.click()}"); await pg.wait_for_timeout(2500)
      await probe('states-rbar-pct')
      await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(2000); await probe('states-rbar-num')
      await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>window.__ySet16 && (document.querySelectorAll('.kn').length) && 0"); 
      await pg.evaluate("()=>{const t=document.querySelectorAll('#ysl .tk'); }")
      await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(2000); await probe('states-num')
      await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(2000)
      for st in ['Delaware','Pennsylvania']:
        await pg.evaluate("n=>{const s=document.getElementById('state');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}))}",st); await pg.wait_for_timeout(4500); await probe(st[:2]+'-pct')
        await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(2000); await probe(st[:2]+'-num')
        await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(2000)
      R['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; await c.close()
  json.dump(res,open(f'b1582p14-labels-{eng}.json','w'),indent=1)
asyncio.run(main())
