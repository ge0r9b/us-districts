# User (1617): with no district type selected (default, or after deselecting one) the heat shades states, then counties, then precincts as you zoom in, in every year and range mode, also after a reload. PA + CA, z 4/7/10/12. Chromium + WebKit 390.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
COL="""()=>{ const cs=[...document.querySelectorAll('#map canvas, .leaflet-pane canvas')].filter(c=>c.width&&c.offsetParent!==null); let n=0,t=0; for(const c of cs){ let d; try{ d=c.getContext('2d').getImageData(0,0,c.width,c.height).data; }catch(e){ continue; } for(let i=0;i<d.length;i+=4*97){ t++; const r=d[i],g=d[i+1],b=d[i+2],a=d[i+3]; if(a>60&&((b>r+40&&b>g+20)||(r>b+40&&r>g+40)||(Math.abs(r-g)<12&&Math.abs(g-b)<12&&r>150&&r<235))) n++; } } return t?n/t:0 }"""
import io
from PIL import Image
async def heat(pg):
  im=Image.open(io.BytesIO(await pg.screenshot())).convert('RGB'); w,h=im.size; px=im.load(); n=t=0
  for x in range(0,w,6):
    for y in range(int(h*0.33),int(h*0.7),6):
      r,g,b=px[x,y]; t+=1
      if (b>r+40 and b>g+20) or (r>b+40 and r>g+40): n+=1
  return n/t
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for how in (os.environ.get('HOW','geo,deselect,deselect-nt,default').split(',')):
        c=await (b.new_context(viewport={'width':390,'height':844}) if how.endswith('-nt') else b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)); pg=await c.new_page()
        await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
        if how.startswith('deselect'):
          for k in (['ushouse'] if how.endswith('-nt') else ['schools','ushouse']):
            await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
            await pg.evaluate("k=>document.querySelector('#lyrRow .lbtn[data-k='+k+']').click()",k); await pg.wait_for_timeout(3000)
            await pg.evaluate("k=>document.querySelector('#lyrRow .lbtn[data-k='+k+']').click()",k); await pg.wait_for_timeout(2500)
          if not how.endswith('-nt'): await pg.evaluate("()=>{ if(!document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(800)
        if how=='geo':
          await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
          await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3000)
          await pg.evaluate("()=>{ if(!document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(800)
          await pg.evaluate("()=>{const g=document.getElementById('gq'); g.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); g.focus()}"); await pg.wait_for_timeout(600)
          await pg.keyboard.type('Pennsylvania',delay=20); await pg.wait_for_timeout(1500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
          lt=await pg.evaluate("()=>[window.__stateSnapshot().lt,[...document.querySelectorAll('#lyrRow .lbtn.on')].map(b=>b.dataset.k),state.value]")
          ck(lt[0] in ('none','') and not lt[1] and lt[2]=='Pennsylvania',f"{eng} geo: a geo-filter entry deselects the district type {lt}",lt)
          await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(2500)
          lt2=await pg.evaluate("()=>[window.__stateSnapshot().lt,[...document.querySelectorAll('#lyrRow .lbtn.on')].map(b=>b.dataset.k),document.body.classList.contains('listmode')]")
          ck(lt2[0] in ('none','') and not lt2[1],f"{eng} geo: list view has no district type either {lt2}",lt2)
          await pg.evaluate("()=>{ if(document.body.classList.contains('foldfs')) document.getElementById('bGeo').click() }"); await pg.wait_for_timeout(1500)
          await pg.evaluate("()=>{ if(document.body.classList.contains('listmode')) document.getElementById('bGlobe').click() }"); await pg.wait_for_timeout(2500)
        for yr in (['as-is',2,1,0,'r'] if how=='deselect' else ['as-is'] if how in ('deselect-nt','geo') else [2]):
          if yr=='as-is': pass
          elif yr=='r': await pg.evaluate("()=>window.__ySelectAll()")
          else: await pg.evaluate(f"()=>window.__ySetYr({yr})")
          await pg.wait_for_timeout(2500)
          for nm,ll in [('PA',[40.27,-76.88]),('CA',[34.05,-118.25])]:
            for z in [4,7,10,12]:
              await pg.evaluate(f"()=>{{map.setView({ll},{z},{{animate:false}})}}"); await pg.wait_for_timeout(5500 if z>=10 else 3500)
              h=await heat(pg); (await pg.screenshot(path=f"/tmp/hz-{how}-{nm}{z}.png")) if h<0.2 else None; ck(h>0.2,f"{eng} {how} yr {yr} {nm} z{z}: shaded ({h:.2f})",h)
        if how.startswith('deselect') or how=='geo':
          await pg.evaluate("()=>window.__ySetYr(2)"); await pg.evaluate("()=>{map.setView([40.27,-76.88],10,{animate:false})}"); await pg.wait_for_timeout(5000)
          await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(400)
          await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(10000)
          h=await heat(pg); ck(h>0.2,f"{eng} after reload PA z10: shaded ({h:.2f})",h)
          await pg.evaluate("()=>{map.setView([34.05,-118.25],12,{animate:false})}"); await pg.wait_for_timeout(6000)
          h=await heat(pg); ck(h>0.2,f"{eng} after reload CA z12: shaded ({h:.2f})",h)
        await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
