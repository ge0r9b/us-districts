# build 1595 (user): whenever a sub-state layer is shown, state outlines are drawn on top as their own non-interactive
# overlay, clearly thicker than the sub-unit lines (scaling with zoom). Checks the canvas stroke widths actually drawn
# per pane, the pane order, pointer-events, and pan frame time. Phones and wide.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
INIT="""(()=>{ window.__lw={}; const s=CanvasRenderingContext2D.prototype.stroke; CanvasRenderingContext2D.prototype.stroke=function(){ try{ const p=this.canvas.closest('.leaflet-pane'); const k=p?([...p.classList].find(c=>/^leaflet-.*-pane$/.test(c))||'?'):'?'; const a=__lw[k]||(__lw[k]=[]); if(a.length<4000) a.push(this.lineWidth); }catch(e){} return s.apply(this,arguments); }; })()"""
PAN="""async()=>{ const f=[]; let t=performance.now(), run=true; const loop=()=>{ const n=performance.now(); f.push(n-t); t=n; if(run) requestAnimationFrame(loop); }; requestAnimationFrame(loop); for(let i=0;i<40;i++){ map.panBy([i%20<10?30:-30,0],{animate:false}); await new Promise(r=>requestAnimationFrame(r)); } run=false; f.sort((a,b)=>a-b); return [Math.round(f.reduce((a,b)=>a+b,0)/f.length*10)/10, Math.round(f[Math.floor(f.length*.95)]*10)/10]; }"""
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568),(1280,800)]:
      for typ,st in [("ushouse",""),("ushouse","Pennsylvania"),("senate","Pennsylvania"),(None,"Pennsylvania")]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); await ctx.add_init_script(INIT); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if st: await pg.evaluate(f"()=>{{const s=document.getElementById('state');s.value={json.dumps(st)};s.onchange&&s.onchange()}}"); await pg.wait_for_timeout(3500)
        if typ:
          await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(700); await pg.evaluate(f"()=>document.querySelector('.lbtn[data-k={typ}]').click()"); await pg.wait_for_timeout(4500)
          await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(500)
        for z in [5,6,7]:
          await pg.evaluate(f"()=>{{ __lw={{}}; map.setView([41.0,-77.5],{z},{{animate:false}}); return 1 }}"); await pg.wait_for_timeout(2500)
          lw=await pg.evaluate("()=>{ const o={}; for(const k in __lw){ const a=__lw[k].filter(x=>x>0); if(a.length) o[k]=[Math.min(...a),Math.max(...a),a.length]; } return o }")
          stw=lw.get('leaflet-stLine-pane'); subs=[v for k,v in lw.items() if k in ('leaflet-type-pane','leaflet-lyr-pane','leaflet-nat-pane','leaflet-heat-pane')]
          sub=max([v[1] for v in subs] or [0]); tag=f"{W} {typ or 'counties'} {st or 'US'} z{z}"
          ck(stw and subs and stw[0]>=2.0 and stw[0]>=sub*1.4,f"{tag}: state lines {stw and stw[0]}px vs sub-unit lines <= {sub}px",lw)
        o=await pg.evaluate("()=>{ const g=n=>map.getPane(n); return {st:+g('stLinePane').style.zIndex, ty:+(g('typePane').style.zIndex||0), ly:+g('lyrPane').style.zIndex, pe:g('stLinePane').style.pointerEvents} }")
        ck(o['st']>max(o['ty'],o['ly']) and o['pe']=='none',f"{W} {typ or 'counties'} {st or 'US'}: state outline pane on top, pointer-events off",o)
        if typ=="ushouse" and not st:
          pan=await pg.evaluate(PAN); print(f"info {W} pan mean/p95 ms {pan}")
          if W in (390,1280): await pg.screenshot(path=f"/workspace/state-lines-{W}.png")
        ck(not er,f"{W} {typ} {st}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
