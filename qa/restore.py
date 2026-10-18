import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import fresh,typegq
VIS="""()=>JSON.stringify({snap:window.__stateSnapshot(),ym:window.__ymode(),knob:(()=>{const k=[...document.querySelectorAll('.kn')].filter(e=>e.offsetParent).map(e=>Math.round(e.getBoundingClientRect().left));return k})(),
 cands:[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')),chart:window.chartMode,num:window.__numMode(),list:document.body.classList.contains('listmode'),
 st:state.value,co:county.value,lt:__stateSnapshot().lt,la:window.__laInfo().on?window.__laInfo().lv:'-',z:map.getZoom(),c:[+map.getCenter().lat.toFixed(3),+map.getCenter().lng.toFixed(3)],ph:document.getElementById('gq').placeholder,crumb:document.getElementById('crumbs').innerText.replace(/\\n/g,' ')})"""
async def slider_to(pg,frac):
  await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
  x,y,w=await pg.evaluate("()=>{const t=document.querySelector('.trk').getBoundingClientRect();return [t.left,t.top+t.height/2,t.width]}")
  await pg.touchscreen.tap(x+2+frac*(w-4),y); await pg.wait_for_timeout(2500)
async def chart(pg,k):
  await pg.evaluate("()=>document.querySelector('#chartBox .cmain').click()"); await pg.wait_for_timeout(700)
  await pg.evaluate("k=>{const b=document.querySelector('#chartBox .copts button[data-ch='+k+']'); if(b) b.click(); else document.body.click()}",k); await pg.wait_for_timeout(2500)
async def cycle(pg,name,o):
  a=json.loads(await pg.evaluate(VIS)); await pg.wait_for_timeout(1500); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000); b=json.loads(await pg.evaluate(VIS))
  diff={k:(a[k],b[k]) for k in a if k!='snap' and a[k]!=b[k]}
  o[name]={'diff':diff,'snapdiff':{k:(a['snap'].get(k),b['snap'].get(k)) for k in set(a['snap'])|set(b['snap']) if a['snap'].get(k)!=b['snap'].get(k)}}
  await pg.screenshot(path=f"../shots/b1569-ch-390-restore-{name}.png")
async def main():
  o={}
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await fresh(b)
    # 1 list All States + '16
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await slider_to(pg,0); await cycle(pg,'y2016-list',o)
    await slider_to(pg,0.5); await cycle(pg,'y2020-list',o)
    await pg.evaluate("()=>{window.__setNum('num')}"); await pg.wait_for_timeout(1500); await chart(pg,'pie'); await cycle(pg,'num-pie',o)
    await pg.evaluate("()=>{window.__ySelectAll&&window.__ySelectAll()}"); await pg.wait_for_timeout(2500); await chart(pg,'line'); await cycle(pg,'range-line',o)
    await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()==='OH'});r.querySelector('.nmx').click()}"); await pg.wait_for_timeout(6000)
    await cycle(pg,'OH-counties',o)
    xy=await center(pg,'#bLyr'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
    xy=await center(pg,'#lyrRow .lbtn[data-k=senate]'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1000)
    await cycle(pg,'senate-type',o)
    # map view with pan/zoom
    await pg.evaluate("()=>{if(document.body.classList.contains('listmode'))document.getElementById('bGlobe').click()}"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>{map.setView([41.5,-81.7],10,{animate:false})}"); await pg.wait_for_timeout(3000)
    await cycle(pg,'map-view-cleveland',o)
    o['err']=log['pageerr']+log['console']; await c.close(); await b.close()
  for k,v in o.items(): print(k,':',json.dumps(v)[:900])
if __name__=='__main__': asyncio.run(main())
