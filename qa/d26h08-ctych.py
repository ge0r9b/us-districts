# Oct 26 ~8 AM (1622) copy of d26h07-ctych.py + single-year chart options (pie)
# Oct 26 ~7 AM (1622): big-county MAP views (list view freezes, QA-138) (All States > state > county): thumbnails % and # vs ELECTION2024 data, then slider ranges '16-'20 / '20-'24 / '16-'24 x every chart-menu option, label overlap/clip check inside #chartBox, list rows, reload restore
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
TH="()=>[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' '))"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,5).map(r=>r.innerText.replace(/\\n/g,' | '))"
OVL="""()=>{const B=document.getElementById('chartBox');if(!B)return null;const br=B.getBoundingClientRect();const L=[];const w=document.createTreeWalker(B,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){const t=n.textContent.trim();if(!t)continue;const p=n.parentElement;if(!p||!p.getClientRects().length)continue;const cs=getComputedStyle(p);if(cs.visibility==='hidden'||+cs.opacity===0)continue;const rg=document.createRange();rg.selectNodeContents(n);const r=rg.getBoundingClientRect();if(!r.width||!r.height)continue;L.push([t.slice(0,24),r.left,r.top,r.right,r.bottom])}
const ov=[];for(let i=0;i<L.length;i++)for(let j=i+1;j<L.length;j++){const a=L[i],b=L[j];const ix=Math.min(a[3],b[3])-Math.max(a[1],b[1]),iy=Math.min(a[4],b[4])-Math.max(a[2],b[2]);if(ix>1&&iy>1)ov.push([a[0],b[0],Math.round(ix),Math.round(iy)])}
const clip=L.filter(a=>a[1]<-1||a[3]>innerWidth+1).map(a=>[a[0],Math.round(a[1]),Math.round(a[3])]);return {box:[Math.round(br.left),Math.round(br.top),Math.round(br.width),Math.round(br.height)],labels:L.map(a=>a[0]).slice(0,30),ov:ov.slice(0,10),clip:clip.slice(0,6)}}"""
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for st,ab,cty in [s.split(':') for s in sys.argv[3].split(',')]:
      c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"../shots/b1622d26h08-{eng[:2]}-{W}x{H}-cc-{cty.replace(' ','')}"; L=out[cty]={}
      async def tap(sel,w=1500):
        xy=await center(pg,sel)
        if not xy: return 'nosel'
        v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); L['build']=await pg.evaluate("window.BUILD")
      L['data']=await pg.evaluate("k=>[window.ELECTION2024[k]]",st+'|'+cty+' County')
      await tap('#bGeo',1200); L['lat_states']=await tap_latency(pg,*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
      ok=True; print(cty,'states list',flush=True)
      for lvl in [ab,cty]:
        xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl)
        if not xy: L['nf']=lvl; ok=False; break
        L['lat_'+lvl]=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
      if not ok: print(cty,'notfound',L.get('nf'),await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"),(await pg.evaluate(ROWS))[:3],flush=True); await safeshot(pg,pre+'-nf.png'); await c.close(); continue
      await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(400)
      L['crumbs']=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"); L['title']=await pg.evaluate("()=>(document.getElementById('vtitle')||{}).innerText")
      L['th_pct']=await pg.evaluate(TH); L['rows']=await pg.evaluate(ROWS)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); L['th_num']=await pg.evaluate(TH); L['rows_num']=await pg.evaluate(ROWS); await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000)
      L['lat_tomap']=await tap('#bGlobe',4500); L['view']='map'  # QA-138: list view freezes on first '16
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): L['lat_time']=await tap('#bTime',1000)
      L['ranges']={}; print(cty,'at county',L['crumbs'],L['th_num'],flush=True)
      for nm,js in [('y16','window.__ySetYr(0)'),('y20','window.__ySetYr(1)'),('y24','window.__ySetYr(2)'),('16-20','window.__ySet16(1)'),('20-24','window.__ySelectAll()'),('16-24','window.__ySet16(2)')]:
        await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(3000); G=L['ranges'][nm]={'ysl':await pg.evaluate("()=>window.__ysl.get()"),'th':await pg.evaluate(TH),'rows':await pg.evaluate(ROWS),'charts':{}}
        print(cty,nm,'ysl',G['ysl'],flush=True); await tap('#chartBox .cmain',900); opts=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.getBoundingClientRect().width).map(b=>b.dataset.ch)"); G['opts']=opts
        for ch in opts:
          if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',900)
          lat=await tap(f'#chartBox .copts button[data-ch={ch}]',2500)
          for nmode in ['pct','num']:
            await pg.evaluate(f"()=>window.__setNum('{nmode}')"); await pg.wait_for_timeout(1300)
            G['charts'][ch+'-'+nmode]={'lat':lat,'mode':await pg.evaluate("()=>window.chartMode"),'txt':await pg.evaluate("()=>document.getElementById('chartBox').innerText.replace(/\\n/g,' | ').slice(0,300)"),'ovl':await pg.evaluate(OVL),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3],'chip':(await pg.evaluate(CHK))['rows'][:2]}
            await safeshot(pg,f"{pre}-r{nm}-{ch}-{nmode}.png")
          await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(800)
        print(cty,'range',nm,json.dumps(G)[:4000],flush=True)
      s1=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
      L['reload']={'before':s1,'after':await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'crumbs':await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"),'th':await pg.evaluate(TH),'ysl':await pg.evaluate("()=>window.__ysl.get()")}
      await safeshot(pg,f"{pre}-reload.png")
      L['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]+log['reqfail'][:4]+log['http'][:4]
      print(cty,'base',json.dumps({k:L[k] for k in L if k!='ranges'})[:3000],flush=True)
      await c.close()
      json.dump(out,open(f"b1622d26h08-ctych-{eng}-{W}x{H}.json",'w'),indent=1)
    await b.close()
asyncio.run(main())
