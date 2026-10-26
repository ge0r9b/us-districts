# Oct 26 ~9 AM (1622): first sort-chip tap right after switching a state list to US House; also Franklin OH town list sort/# at '24
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))"
NMX="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
EFP="()=>{const s=document.getElementById('laSort');const r=s.getBoundingClientRect();const e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return [Math.round(r.left),Math.round(r.top),Math.round(r.width),e?(e.id||e.className||e.nodeName):null,document.getElementById('lyrRow')?getComputedStyle(document.getElementById('lyrRow')).display+'/'+document.getElementById('lyrRow').getBoundingClientRect().height:null]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; st=sys.argv[3]; cty=sys.argv[4]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"../shots/b1622d26h09-{eng[:2]}-{W}x{H}-us"
    async def tap(sel,w=1500):
      xy=await center(pg,sel)
      if not xy: return 'nosel'
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    await tap('#bGeo',1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    xy=await pg.evaluate(NMX,st); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMX,st); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    for trial in range(2):
      T=out[f't{trial}']={}
      T['lyr_open']=await tap('#bLyr',900); T['efp_menu']=await pg.evaluate(EFP); await safeshot(pg,f'{pre}-t{trial}-menu.png')
      T['pick']=await tap('#lyrRow button[data-k=ushouse]',3000); T['crumbs']=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText")
      T['efp']=await pg.evaluate(EFP); T['rows0']=await pg.evaluate(ROWS); await safeshot(pg,f'{pre}-t{trial}-ush.png')
      T['sort1']=await tap('#laSort',1500); T['rows1']=await pg.evaluate(ROWS); await safeshot(pg,f'{pre}-t{trial}-sort1.png')
      T['sort2']=await tap('#laSort',1500); T['rows2']=await pg.evaluate(ROWS)
      print(trial,json.dumps(T),flush=True)
      await tap('#bLyr',900); await tap('#lyrRow button[data-k=ushouse]',3500)
    await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(500)
    xy=await pg.evaluate(NMX,cty); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMX,cty)
    if xy:
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(6000)
      T=out['town']={'crumbs':await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"),'rows':await pg.evaluate(ROWS),'efp':await pg.evaluate(EFP)}
      T['sort1']=await tap('#laSort',1500); T['flip']=await pg.evaluate(ROWS); T['sort2']=await tap('#laSort',1500); T['back']=await pg.evaluate(ROWS)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); T['num']=await pg.evaluate(ROWS); await safeshot(pg,f'{pre}-town-num.png')
      T['nsort']=await tap('#laSort',1500); T['nflip']=await pg.evaluate(ROWS); await tap('#laSort',1200); await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000); await safeshot(pg,f'{pre}-town-pct.png')
      print('town',json.dumps(T),flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]; print('err',out['err'])
    json.dump(out,open(f'b1622d26h09-ushsort-{eng}-{W}x{H}-{st}.json','w'),indent=1); await b.close()
asyncio.run(main())
