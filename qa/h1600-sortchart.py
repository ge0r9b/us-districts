# Oct 25 1PM (1618) copy of h0800-sortchart.py, levels states>OH>Franklin; was: Oct 25 8AM (1618): sort chip flip, % / #, chart menu options (pie/bar/line) on All States + a state counties list, district-type menu overlay (map rect / dimming) at iPad and 320
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
TH="()=>[...document.querySelectorAll('#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' '))"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,6).map(r=>r.innerText.replace(/\\n/g,' | '))"
RECT="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height),cs.opacity,cs.filter]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsh1600/b1620h16-{eng[:2]}-{W}x{H}-sc"
    async def tap(sel,w=1500):
      xy=await center(pg,sel)
      if not xy: return 'nosel'
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    # district-type menu overlay on the map
    m0=await pg.evaluate(RECT,'#map'); out['lyr_lat']=await tap('#bLyr',900); m1=await pg.evaluate(RECT,'#map')
    out['lyr']={'map_before':m0,'map_open':m1,'row':await pg.evaluate(RECT,'#lyrRow'),'btns':await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow .lbtn')].map(b=>b.dataset.k)"),'bodyfilter':await pg.evaluate("()=>[getComputedStyle(document.body).filter,getComputedStyle(document.getElementById('map')).opacity]")}
    await safeshot(pg,pre+'-lyr-open.png'); await tap('#bLyr',800)
    await tap('#bGeo',1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for lvl in ['states',sys.argv[3],sys.argv[4]]:
      if lvl!='states':
        xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300)
        xy=await pg.evaluate(NMXY,lvl)
        if not xy: out[lvl]='notfound'; print(lvl,'notfound'); break
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000); await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(500)
      L=out[lvl]={}
      L['hdr']=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"); L['th_pct']=await pg.evaluate(TH); L['rows_pct']=await pg.evaluate(ROWS); L['chip']=await pg.evaluate(CHK)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); L['rows_num']=await pg.evaluate(ROWS); L['th_num']=await pg.evaluate(TH); L['chip_num']=await pg.evaluate(CHK)
      await safeshot(pg,f'{pre}-{lvl}-num.png')
      L['sort_lat']=await tap('#laSort',1500); L['rows_flip']=await pg.evaluate(ROWS); L['sort2_lat']=await tap('#laSort',1500); L['rows_back']=await pg.evaluate(ROWS)
      await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
      L['ch_open_lat']=await tap('#chartBox .cmain',900); L['ch_opts']=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.getBoundingClientRect().width).map(b=>b.dataset.ch)")
      L['list_rect_open']=await pg.evaluate(RECT,'#listView'); await safeshot(pg,f'{pre}-{lvl}-chartmenu.png')
      L['charts']={}
      for ch in L['ch_opts']:
        if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',900)
        lat=await tap(f'#chartBox .copts button[data-ch={ch}]',2500)
        L['charts'][ch]={'lat':lat,'mode':await pg.evaluate("()=>window.chartMode"),'rows':(await pg.evaluate(ROWS))[:3],'chip':(await pg.evaluate(CHK))['rows'][:2],'list':await pg.evaluate(RECT,'#listView')}
        await safeshot(pg,f'{pre}-{lvl}-chart-{ch}.png')
      print(lvl,json.dumps(L)[:3500],flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
    print('lyr',json.dumps(out['lyr']),'err',out['err'],flush=True)
    json.dump(out,open(f'b1620h1600-sortchart-{eng}-{W}x{H}-{sys.argv[3]}.json','w'),indent=1); await b.close()
asyncio.run(main())
