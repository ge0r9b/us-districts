import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
POS="""()=>['laCands','bBack','laSort'].map(id=>{const e=document.getElementById(id); if(!e) return 'none'; const cs=getComputedStyle(e); if(e.hidden||cs.display==='none'||cs.visibility==='hidden'||cs.opacity==='0') return 'hidden'; const r=e.getBoundingClientRect(); if(!r.width) return 'hidden'; return Math.round(r.left)+','+Math.round(r.top)}).join(' | ')"""
# tap a row by real touch; record per-frame: positions + row count + first row name, from the touch event to 1.5 s
REC="""()=>{window.__fr=[];window.__t0=null;const pos=%s;const snap=()=>{const rows=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent);return {t:Math.round(performance.now()-(window.__t0||performance.now())),p:pos(),n:rows.length,f:rows[0]?(rows[0].querySelector('.nmx')||rows[0]).textContent.trim().slice(0,22):''}};
 let done=false;const g=e=>{if(done)return;done=true;window.__t0=e.timeStamp;const loop=()=>{window.__fr.push(snap());if(performance.now()-window.__t0<1500)requestAnimationFrame(loop)};requestAnimationFrame(loop)};
 ['pointerup','touchend','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}));}"""%POS
async def tap_row(pg,name):
  xy=await pg.evaluate("n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+q.width*0.3,q.top+q.height/2]}",name)
  if not xy: return None
  await pg.wait_for_timeout(500); await pg.evaluate(REC); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1800)
  return await pg.evaluate("()=>window.__fr")
def summarize(fr):
  if not fr: return {'err':'row not found'}
  first_new=next((f['t'] for f in fr if f['n']>0 and f['f']!=fr[0]['f']),None)
  seq=[]; 
  for f in fr:
    if not seq or seq[-1]!=f['p']: seq.append(f['p'])
  return {'first_frame_ms':fr[0]['t'],'new_rows_ms':first_new,'pos_seq':seq,'end':fr[-1]}
async def main():
  eng=sys.argv[1]; which=sys.argv[2:]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      c,pg,log=await ctx(b,W,H,mob,eng); R={}; s=tag.replace('iphone','').replace('ipad','')
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      R['build']=await pg.evaluate("()=>window.BUILD")
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      # range + line (QA-011 setting)
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>{document.querySelector('#chartBox .cmain').click()}"); await pg.wait_for_timeout(700)
      await pg.evaluate("()=>{const b=document.querySelector('#chartBox .copts button[data-ch=line]'); b&&b.click()}"); await pg.wait_for_timeout(2500)
      R['chart']=await pg.evaluate("()=>window.chartMode")
      for step,name in (('PA','PA'),('county','Philadelphia'),('town','Philadelphia city')):
        R[step]=summarize(await tap_row(pg,name)); await pg.wait_for_timeout(3000)
        await pg.screenshot(path=f"../shots/b1567-{eng[:2]}-{s}-drill-{step}.png")
        R[step+'_rows']=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,6).map(r=>{const n=r.querySelector('.nmx');return n?{t:n.textContent.trim(),full:n.title||n.getAttribute('aria-label')||'',sw:n.scrollWidth,cw:n.clientWidth}:r.innerText.slice(0,30)})")
        R[step+'_pos']=await pg.evaluate(POS)
      # back chevron x3
      for i in range(3):
        xy=await center(pg,'#bBack')
        if not xy: R['back%d'%i]='no chevron'; break
        await pg.evaluate(REC); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1800)
        R['back%d'%i]=summarize(await pg.evaluate("()=>window.__fr")); await pg.wait_for_timeout(1500)
      await pg.screenshot(path=f"../shots/b1567-{eng[:2]}-{s}-back.png")
      R['cls']=await pg.evaluate("()=>window.__cls"); R['shifts']=await pg.evaluate("()=>window.__shifts.slice(0,8)")
      R.update({k:v for k,v in log.items() if v}); out[tag]=R; await c.close(); print(tag,'done',flush=True)
    await b.close()
  json.dump(out,open(f'drill-{eng}.json','w'),indent=1)
asyncio.run(main())
