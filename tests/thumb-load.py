# build 1581: map-view thumbnails never move from their first visible frame (fresh load + reload restoring MA / Worcester County, % and # modes)
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
INIT="""(()=>{ window.__tj=[]; const f=()=>{ const cb=document.getElementById('cands'); const vis=cb&&getComputedStyle(cb).visibility==='visible'&&getComputedStyle(cb).display!=='none';
  const cs=vis?[...document.querySelectorAll('#cands .cand')].filter(c=>c.getBoundingClientRect().width>0).map(c=>{ const i=c.querySelector('img'), r=(i||c).getBoundingClientRect(), s=c.querySelector('.cpt'), sr=s&&s.getBoundingClientRect(); return [c.className.replace(/\\s+on\\b/,''), r.left, r.top, sr&&sr.width?sr.left:null, sr&&sr.width?sr.width:null]; }):[];
  window.__tj.push(cs); if(window.__tj.length<1200) requestAnimationFrame(f); }; requestAnimationFrame(f); })()"""
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
def judge(tag,fr):
  vis=[x for x in fr if x]
  if not vis: ck(False,f"{tag}: thumbnails never visible"); return
  f0=vis[0]; bad=None
  for x in vis:
    if len(x)!=len(f0) or any(a[0]!=b[0] or abs(a[1]-b[1])>0.5 or abs(a[2]-b[2])>0.5 or (a[3] is not None and b[3] is not None and (abs(a[3]-b[3])>0.5 or abs(a[4]-b[4])>0.5)) for a,b in zip(x,f0)): bad=x; break
  ck(bad is None,f"{tag}: {len(vis)} visible frames, thumbnails/badges dx=dy=0 from first paint {'' if bad is None else json.dumps([f0,bad])[:300]}")
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in [(390,844),(375,667)]:
      for mode in ["pct","num"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},is_mobile=True,has_touch=True); await ctx.add_init_script(INIT); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
        if mode=="pct": judge(f"{W} fresh load US",await pg.evaluate("()=>window.__tj"))
        await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(3500)
        if mode=="num":
          await pg.evaluate("()=>window.__setNum&&window.__setNum('num')"); await pg.wait_for_timeout(800)
          await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Worcester County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(3000)
        await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()")
        await pg.reload(); await pg.wait_for_timeout(9000)
        judge(f"{W} reload {'MA %' if mode=='pct' else 'Worcester #'}",await pg.evaluate("()=>window.__tj"))
        txt=await pg.evaluate("()=>[...document.querySelectorAll('#cands .cand .cpt')].map(s=>s.textContent)")
        ck(len(txt)==2 and (('%' in txt[0]) if mode=='pct' else ('k' in txt[0] or 'M' in txt[0])),f"{W} reload: final badges {txt}")
        ck(not er,f"{W}: no page errors {er[:2]}")
        await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
