# b1583 QA-046 recheck (env QAT targets, QAP prefix, QAZ zooms): screenshots of 3 of the worst solid counties (all precincts beyond the +-60 clamp). Derived from b1575-saf.py.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import URL,INIT,UA,UAI,safeshot
import os
URL=os.environ.get("QAURL",URL); TAG=os.environ.get("QATAG","")
MAC="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
SZ={'1440':(1440,900,'desk'),'1024x768':(1024,768,'ipad'),'390':(390,844,'phone')}
THUMB="""()=>{const fl=(()=>{const f=document.querySelector('#crumbs .cic img');if(!f)return {lab:'FLAG none',btn:[0,0,0,0],img:null};const r=f.getBoundingClientRect();return {lab:'FLAG '+(f.getAttribute('src')||'').split('/').pop().slice(0,30),btn:[0,0,+r.width.toFixed(1),+r.height.toFixed(1)],img:[f.naturalWidth,f.naturalHeight]}})();
 return [fl].concat([...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect(),i=e.querySelector('img'),ir=i?i.getBoundingClientRect():null;return {lab:e.getAttribute('aria-label'),btn:[Math.round(r.left),Math.round(r.top),+r.width.toFixed(1),+r.height.toFixed(1)],img:ir?[+ir.width.toFixed(1),+ir.height.toFixed(1)]:null}}))}"""
MAPI="""()=>{const m=window.__map;const c=m.getCenter();let paths=0,canv=0;document.querySelectorAll('.leaflet-overlay-pane path').forEach(p=>paths++);document.querySelectorAll('.leaflet-overlay-pane canvas, .leaflet-pane canvas').forEach(x=>canv++);
 return {z:m.getZoom(),c:[+c.lat.toFixed(4),+c.lng.toFixed(4)],paths,canv,crumbs:document.getElementById('crumbs').innerText,lt:window.__stateSnapshot&&window.__stateSnapshot().lt,svgRend:!!document.querySelector('.leaflet-overlay-pane svg'),prec:Object.keys(window.__prec||{}).length}}"""
VISTXT="(t)=>{const L=[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent&&e.innerText);const nm=e=>e.innerText.trim().split('\\n').map(x=>x.replace('›','').trim()).filter(x=>x.length>1)[0]||'';let e=L.filter(e=>nm(e)===t);if(!e.length)return null;const r=e[e.length-1];r.scrollIntoView({block:'nearest'});const b=r.getBoundingClientRect();return [b.left+Math.min(40,b.width/2),b.top+b.height/2]}"
import os
TARGETS=[tuple(x.split(':')) for x in os.environ['QAT'].split(';')]
def colors(path,box):
  from PIL import Image
  im=Image.open(path).convert('RGB'); W,H=im.size; l,t,r,b=[int(v) for v in (box[0]*W,box[1]*H,box[2]*W,box[3]*H)]
  cr=im.crop((l,t,r,b)).resize((120,120)); q=set()
  for p in cr.getdata(): q.add((p[0]//24,p[1]//24,p[2]//24))
  return len(q)
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2].split(','); tg=TARGETS if len(sys.argv)<4 else [t for t in TARGETS if t[0] in sys.argv[3].split(',')]
  out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for s in sizes:
      W,H,kind=SZ[s]; kw=dict(viewport={'width':W,'height':H},device_scale_factor=2)
      if kind=='desk': kw.update(user_agent=MAC,has_touch=False)
      else:
        kw.update(user_agent=UA if kind=='phone' else UAI,has_touch=True)
        if eng=='chromium': kw['is_mobile']=True
      c=await b.new_context(**kw); await c.add_init_script(INIT); pg=await c.new_page(); errs=[]
      pg.on('pageerror',lambda e: errs.append(str(e)[:150])); pg.on('console',lambda m: errs.append('c:'+m.text[:150]) if m.type=='error' else None)
      async def tap(xy):
        if kind=='desk': await pg.mouse.click(*xy)
        else: await pg.touchscreen.tap(*xy)
      async def center(sel): return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",sel)
      await pg.goto(URL,wait_until="load",timeout=90000); await pg.wait_for_function("()=>window.__ymode&&window.__map",timeout=90000); await pg.wait_for_timeout(5000)
      R=out[f'{eng}-{s}']={'build':await pg.evaluate('window.BUILD'),'US':{'thumbs':await pg.evaluate(THUMB)}}
      pre=f"../shots/{os.environ["QAP"]}-{eng[:2]}-{s}"
      await safeshot(pg,pre+"-US.png")
      for st,co in tg:
        k=st[:2]; X=R[st]={}
        await tap(await center('#bGeo')); await pg.wait_for_timeout(1500)
        if (await pg.evaluate("()=>document.getElementById('crumbs').innerText"))!='All countries':
          pass
        xy=await pg.evaluate(VISTXT,st)
        if not xy:
          X['err']='state not in geo menu'; await tap(await center('#bGeo')); continue
        await tap(xy); await pg.wait_for_timeout(5000)
        await safeshot(pg,f"{pre}-{k}-menu.png")
        xy=await pg.evaluate(VISTXT,co)
        if not xy: X['err']='county not in menu'; X['menu']=await pg.evaluate("()=>[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent).slice(0,8).map(e=>e.innerText.slice(0,30))"); await tap(await center('#bGeo')); continue
        await tap(xy); await pg.wait_for_timeout(7000)
        X['county']={'thumbs':await pg.evaluate(THUMB),'map':await pg.evaluate(MAPI)}; f=f"{pre}-{k}-county.png"; await safeshot(pg,f); X['county']['ncol']=colors(f,(.3,.35,.7,.7))
        for dz in range(1,int(os.environ.get("QAZ","2"))+1):
          await pg.evaluate("()=>{window.__map.setZoom(window.__map.getZoom()+1,{animate:false});return 1}"); await pg.wait_for_timeout(5000)
          f=f"{pre}-{k}-county-z{dz}.png"; await safeshot(pg,f)
          X['z%d'%dz]={'map':await pg.evaluate(MAPI),'ncol':colors(f,(.3,.35,.7,.7))}
        await c.close(); c=await b.new_context(**kw); await c.add_init_script(INIT); pg=await c.new_page()
        pg.on('pageerror',lambda e: errs.append(str(e)[:150]))
        await pg.goto(URL,wait_until="load",timeout=90000); await pg.wait_for_function("()=>window.__ymode&&window.__map",timeout=90000); await pg.wait_for_timeout(4000)
        print(eng,s,st,'done',flush=True)
      # list view thumbs for comparison
      await tap(await center('#bGlobe')); await pg.wait_for_timeout(3000); R['US_list_thumbs_3s']=await pg.evaluate(THUMB); await safeshot(pg,pre+'-US-list.png'); await pg.wait_for_timeout(5000); R['US_list_thumbs']=await pg.evaluate(THUMB)
      R['err']=errs[:8]; await c.close()
      json.dump(out,open(f"{os.environ["QAP"]}-{s}-{eng}.json",'w'),indent=1)
    await b.close()
asyncio.run(main())
