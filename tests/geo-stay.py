# usage: python3 tests/geo-stay.py URL tag -- typing a state in the geo field + Enter keeps that state (no county auto-select, no fall back to US, also when re-selected), state selected = COUNTY heat map (not precincts), LOD zoom steps with hysteresis
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
def chk(n,ok,info=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,info,flush=True)
S="()=>({st:state.value,co:county.value,gq:document.getElementById('gq').placeholder,lvl:(document.getElementById('heatlevel')||{}).value,z:window.__map.getZoom(),span:Math.round(window.__vspan()*10)/10,solid:window.__stSolid()})"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((390,844,'ph'),(1280,800,'dk')):
      for st in ('Florida','Texas','Pennsylvania','California'):
        pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e))); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
        async def enter():
          await pg.locator('#gq').click(); await pg.wait_for_timeout(700); await pg.locator('#gq').type(st.lower(),delay=40); await pg.wait_for_timeout(400); await pg.keyboard.press('Enter')
          await pg.evaluate("()=>{const g=document.getElementById('gq'); g.dispatchEvent(new Event('search'));}")  # iOS fires 'search' after Enter with the field already cleared
        await enter(); await pg.wait_for_timeout(7000); r=await pg.evaluate(S)
        chk(f'{t} {st} typed+Enter stays',r['st']==st and r['co']=='' and r['gq'].startswith(st) and ', ' not in r['gq'],json.dumps(r))
        chk(f'{t} {st} county heat map (not precincts)',r['lvl']=='county',json.dumps(r)); await pg.screenshot(path=f"/workspace/shots/gs-{tag}-{t}-{st}.png")
        await enter(); await pg.wait_for_timeout(5500); r=await pg.evaluate(S)
        chk(f'{t} {st} re-select stays',r['st']==st and r['co']=='' and r['gq'].startswith(st) and r['lvl']=='county',json.dumps(r)); await pg.screenshot(path=f"/workspace/shots/gs-{tag}-{t}-{st}-again.png")
        await pg.close()
      # institution list selection
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1800)
      await pg.evaluate("()=>{const l=[...document.querySelectorAll('.foldlist li')].find(l=>l.innerText.trim().startsWith('Florida')); l.click()}"); await pg.wait_for_timeout(7000)
      r=await pg.evaluate(S); chk(f'{t} institution list Florida county map',r['st']=='Florida' and r['co']=='' and r['lvl']=='county',json.dumps(r)); await pg.screenshot(path=f"/workspace/shots/gs-{tag}-{t}-inst.png"); await pg.close()
      # LOD per layer: zoomed-out / Texas-sized / state-level. Solid statewide when zoomed out (not for US House: district detail at every zoom); hysteresis on the way back out
      for lay in ('none','ushouse','senate','statehouse','schools'):
        pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if lay!='none': await pg.evaluate("(k)=>{const b=document.querySelector('#lyrRow .lbtn[data-k='+k+']'); b&&b.click();}",lay); await pg.wait_for_timeout(2500)
        ctr=[31.0,-99.3]; seq=[]
        for z in [3,3.5,4,4.5,5,5.5,6,6.5,7,7.5,8,7.5,7,6.5,6,5.5,5,4.5,4,3.5,3]:
          await pg.evaluate("([z,c])=>{ window.__map.setView(c,z,{animate:false}); }",[z,ctr]); await pg.wait_for_timeout(1200); r=await pg.evaluate(S); seq.append((z,r['span'],r['solid']))
        n=11; up=seq[:n]; dn=seq[n:]
        print(t,lay,seq,flush=True)
        if lay=='ushouse':
          chk(f'{t} {lay} district detail at every zoom (never solid)',not any(x[2] for x in seq),str(seq[:3]))
        else:
          off=next((x for x in up if not x[2]),None); on=next((x for x in dn if x[2]),None)
          chk(f'{t} {lay} solid statewide zoomed out',seq[0][2] and seq[-1][2])
          chk(f'{t} {lay} detail from a Texas-sized view (span<=15.5)',off is not None and off[1]<=15.6 and all(x[2] for x in up if x[1]>17),str(off))
          chk(f'{t} {lay} hysteresis (back to solid only at span>=19)',on is not None and on[1]>=18.9 and all(not x[2] for x in dn if x[1]<18.9),str(on))
        zs=[x[0] for x in up if x[2]]; zd=[x[0] for x in up if not x[2]]
        for labn,z in (('out',3.5),('texas',zd[0] if zd else 5),('state',7)):
          await pg.evaluate("([z,c])=>{ window.__map.setView(c,z,{animate:false}); }",[z,ctr]); await pg.wait_for_timeout(2500); await pg.screenshot(path=f"/workspace/shots/lod-{tag}-{t}-{lay}-{labn}.png")
        await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
