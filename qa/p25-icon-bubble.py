# build 1597 (QA-076): in a chart view, tapping a thumbnail (or the gray 'Other' chip) shows the white name bubble right next to
# the photo: never over the photo, never over a value label ('49.9%'), on the photo's row, inside the screen, and close to it
# (not 270 px away mid-bar on iPad). Tight phone range rows may use the short 'Trump ’24' or sit right above/below the photo. Bar, pie and range bar; WebKit phones + iPad, Chromium 390.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
TG="""()=>[...document.querySelectorAll('#cands .cand img, #cands img.dmt, #cands .dmoc, .cpanel .sechip')].filter(e=>e.offsetWidth&&getComputedStyle(e).visibility!=='hidden').map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}).filter(r=>r[1]>0&&r[3]<innerHeight)"""
CHK="""t=>{ const e=document.getElementById('iconBub'); if(!e) return {none:1}; const b=e.getBoundingClientRect(); const ov=(q)=>q.left<b.right-1&&q.right>b.left+1&&q.top<b.bottom-1&&q.bottom>b.top+1;
  const lbl=[...document.querySelectorAll('.cpanel *, #cands *')].filter(x=>x!==e&&!x.children.length&&x.offsetWidth&&(x.textContent||'').trim()).filter(x=>ov(x.getBoundingClientRect())).map(x=>x.textContent.trim().slice(0,12));
  const ph={left:t[0],top:t[1],right:t[2],bottom:t[3]};
  return {txt:e.textContent,b:[b.left,b.top,b.right,b.bottom].map(Math.round),overPhoto:ov(ph),lbl,gap:Math.round(b.left>=t[2]-1?b.left-t[2]:b.right<=t[0]+1?t[0]-b.right:0),row:(b.top<t[3]&&b.bottom>t[1])||((Math.abs(b.bottom-t[1])<=8||Math.abs(b.top-t[3])<=8)&&b.left<t[2]&&b.right>t[0]),inside:b.left>=0&&b.right<=innerWidth&&b.top>=0} }"""
async def chart(pg,k):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def run(b,eng,W,H):
  for mode in ("bar","pie","range bar"):
    ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=(W<800 and eng=='chromium')); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    if mode=="range bar":
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); }"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
    await chart(pg,mode.split()[-1]); tg=await pg.evaluate(TG); tag=f"{eng} {W}x{H} {mode}"
    ck(len(tg)>=2,f"{tag}: thumbnails found ({len(tg)})",tg)
    for i,t in enumerate(tg):
      await pg.touchscreen.tap((t[0]+t[2])/2,(t[1]+t[3])/2); await pg.wait_for_timeout(450); r=await pg.evaluate(CHK,t)
      ok=not r.get('none') and not r['overPhoto'] and not r['lbl'] and r['row'] and r['inside'] and -1<=r['gap']<=(80 if mode!='range bar' else 130)
      ck(ok,f"{tag} icon {i}: bubble '{r.get('txt')}' beside the photo (gap {r.get('gap')}px), over no photo/label",r)
      await pg.wait_for_timeout(3200)
    ck(not er,f"{tag}: no page errors",er); await ctx.close()
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568),(1024,768)]: await run(b,'webkit',W,H)
    await b.close()
    b=await p.chromium.launch(); await run(b,'chromium',390,844); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
