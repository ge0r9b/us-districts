# hourly Oct 25 ~6AM (1618): time slider tick taps through every year in % and #, per place; map red/blue share; reload restore; pie/line charts (county + state senate district) with reload
import asyncio,sys,json,os
from playwright.async_api import async_playwright
from PIL import Image
from common import *
from gaps import typegq
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value||document.getElementById('gq').placeholder,ym:window.__ymode&&window.__ymode(),ysl:window.__ysl.get(),num:window.__numMode&&window.__numMode(),list:document.body.classList.contains('listmode')})"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
MP="()=>{const m=window.__map;return m?[m.getZoom(),+m.getCenter().lat.toFixed(3),+m.getCenter().lng.toFixed(3)]:null}"
BUSY="()=>[...document.querySelectorAll('.spin,.loading,.busy,[aria-busy=true],#ynote')].filter(e=>e.offsetParent&&(e.id!=='ynote'||e.innerText.trim())).map(e=>(e.id||e.className)+':'+e.innerText.slice(0,60))"
CH="()=>({mode:window.chartMode,lv:(document.getElementById('listView')||{innerText:''}).innerText.replace(/\\n/g,' | ').slice(0,400),svgtxt:[...document.querySelectorAll('#listView svg text')].map(t=>t.textContent).slice(0,30)})"
def rb(path,H):
  im=Image.open(path).convert('RGB'); w,h=im.size; im=im.crop((0,int(h*0.25),w,int(h*0.75))).resize((200,200)); r=bl=0
  for (R,G,B) in im.getdata():
    if R>G+40 and R>B+40: r+=1
    elif B>R+40 and B>G+10: bl+=1
  return [round(r/400,1),round(bl/400,1)]
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; places=sys.argv[3].split('|'); parts=sys.argv[4].split(',') if len(sys.argv)>4 else ['yrs','charts']; out={}
  tg0=f"{eng[:2]}-{W}x{H}"
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for pl in places:
      c,pg,log=await ctx(b,W,H,W<600,eng); R=out[pl]={}; tg=pl.replace(' ','').replace(',','').replace('>','-')
      pre=f"shotsh0600/b1618h6-{tg0}-yrs-{tg}"
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
      q,_,dist=pl.partition('>')
      await typegq(pg,q); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      if dist:  # state legislative district: senate type, list, pick named row
        await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(900)
        await pg.touchscreen.tap(*(await center(pg,'#lyrRow .lbtn[data-k=senate]'))); await pg.wait_for_timeout(4500)
        if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
        if not (await pg.evaluate(HDR))['list']: await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4500)
        xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.textContent.trim()===t||e.textContent.trim().startsWith(t+' '));if(!e)return null;e.scrollIntoView({block:'center'});return 1}",dist); await pg.wait_for_timeout(500)
        xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.textContent.trim()===t||e.textContent.trim().startsWith(t+' '));if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",dist)
        if not xy: xy=await pg.evaluate("()=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].filter(e=>e.offsetParent)[0];if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,e.textContent.trim()]}")
        R['distrow']=xy
        if xy: await pg.touchscreen.tap(xy[0],xy[1]); await pg.wait_for_timeout(5000)
        if (await pg.evaluate(HDR))['list']: await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4500)
      R['start']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(MP)]; print(pl,'start',R['start'],flush=True)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1200)
      if 'yrs' in parts:
        Y=R['yrs']=[]
        for mode in ['pct','num']:
          if mode=='num': await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
          for i in [0,1,2,0]:
            xy=await center(pg,f'#ysl .tk[data-i="{i}"]'); lat=await tap_latency(pg,*xy)
            busy=[]
            for k in range(8):
              await pg.wait_for_timeout(500); bz=await pg.evaluate(BUSY)
              if bz: busy.append((k,bz))
            h=await pg.evaluate(HDR); th=await pg.evaluate(TH); sp=f"{pre}-{mode}-{i}.png"; await safeshot(pg,sp)
            e={'mode':mode,'i':i,'lat':lat,'ym':h['ym'],'ysl':h['ysl'],'title':h['title'],'crumbs':h['crumbs'],'th':th,'busy_after_4s':busy[-1:] ,'rb':rb(sp,H),'shot':sp}
            Y.append(e); print(pl,json.dumps(e)[:700],flush=True)
          # reload in this state
          s1=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); h1=await pg.evaluate(HDR); t1=await pg.evaluate(TH)
          await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(8000)
          rl={'mode':mode,'same_state':s1==await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'hdr_b':h1,'hdr_a':await pg.evaluate(HDR),'th_b':t1,'th_a':await pg.evaluate(TH)}
          R.setdefault('reload',[]).append(rl); await safeshot(pg,f"{pre}-{mode}-reload.png"); print(pl,'RELOAD',json.dumps(rl)[:900],flush=True)
          if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1200)
        await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000)
      if 'charts' in parts:
        Cs=R['charts']={}
        for ch,rng,js in [('pie','24','window.__ySetYr(2)'),('pie','16','window.__ySetYr(0)'),('line','16-24','window.__ySet16(2)'),('line','20-24','window.__ySelectAll()')]:
          if 1:
            await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(2500)
            if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
            opts=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)")
            k=f"{ch}-{rng}"; G=Cs[k]={'opts':opts}
            xy=await center(pg,f'#chartBox .copts button[data-ch={ch}]')
            if not xy and await pg.evaluate("()=>window.chartMode")==ch: xy=None; G['already']=True
            if not xy and not G.get('already'): G['missing']=True; print(pl,k,G,flush=True); continue
            if xy: G['lat']=await tap_latency(pg,*xy); await pg.wait_for_timeout(2500)
            elif await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
            for m in ['pct','num']:
              await pg.evaluate(f"()=>window.__setNum('{m}')"); await pg.wait_for_timeout(1500); G[m]=[await pg.evaluate(CH),await pg.evaluate(TH),await pg.evaluate(HDR)]
              await safeshot(pg,f"{pre}-chart-{k}-{m}.png")
            s1=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(8000)
            G['reload']={'same_state':s1==await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'after':[await pg.evaluate(CH),await pg.evaluate(TH),await pg.evaluate(HDR)]}
            await safeshot(pg,f"{pre}-chart-{k}-reload.png")
            await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(800)
            if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1200)
            print(pl,k,json.dumps(G)[:1800],flush=True)
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]+[x for x in log['reqfail'] if 'arcgis' not in x.lower()][:4]+log['http'][:4]; print(pl,'err',R['err'],flush=True)
      await c.close()
      json.dump(out,open(f"b1618h0600-yrs-{eng}-{W}x{H}{os.environ.get('SUF','')}.json",'w'),indent=1)
    await b.close()
asyncio.run(main())
