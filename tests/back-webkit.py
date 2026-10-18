# QA-071: WebKit + touch: the back chevron works at every depth (All States > PA > Allegheny > Pittsburgh precincts), one tap = one step back
import asyncio,sys
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "http://localhost:8844/v2/"
ENG="chromium" if "chromium" in sys.argv else "webkit"
VPS=[(390,844),(375,667),(320,568),(1024,576)]
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
ST="()=>[ [...document.querySelectorAll('#crumbs .crumb')].map(c=>c.textContent.trim()).join('>'), document.querySelectorAll('#listView .lvrow.la').length, (document.querySelector('#listView .lvrow.la .nmx')||{}).textContent||'' ]"
async def row(pg,txt):
  xy=await pg.evaluate("t=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()===t}); if(!r) return null; r.scrollIntoView({block:'center'}); const q=r.getBoundingClientRect(); return [q.left+60,q.top+q.height/2]}",txt)
  if not xy: return False
  await pg.wait_for_timeout(300)
  xy=await pg.evaluate("t=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()===t}); const q=r.getBoundingClientRect(); return [q.left+60,q.top+q.height/2]}",txt)
  await pg.touchscreen.tap(*xy); return True
async def back(pg):
  xy=await pg.evaluate("()=>{const b=document.getElementById('bBack'); if(!b) return null; const r=b.getBoundingClientRect(); if(!r.width||getComputedStyle(b).display==='none') return null; return [r.left+r.width/2,r.top+r.height/2]}")
  if not xy: return False
  await pg.touchscreen.tap(*xy); return True
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch()
    if ENG=='chromium': VPS[:]=VPS[:1]
    for W,H in VPS:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      xy=await pg.evaluate("()=>{const r=document.getElementById('bGeo').getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}"); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
      xy=await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); const r=l.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}"); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3000)
      seq=[await pg.evaluate(ST)]
      for t,w in [("PA",6000),("Allegheny",6000),("Pittsburgh",8000)]:
        ok=await row(pg,t)
        if not ok and t=="Pittsburgh": ok=await row(pg,"Pittsburgh city")
        await pg.wait_for_timeout(w); seq.append(await pg.evaluate(ST))
        if not ok: print("INFO",W,"row not found:",t,seq[-1][:2]); break
      print("INFO",W,"path",[s[0][:60]+" #"+str(s[1]) for s in seq])
      for i in range(len(seq)-1,0,-1):
        okb=await back(pg); await pg.wait_for_timeout(3500); now=await pg.evaluate(ST)
        same=lambda a,b: a.split('>')[-1]==b.split('>')[-1] and a.count('>')==b.count('>')
        ck(okb and same(now[0],seq[i-1][0]) and now[1]==seq[i-1][1],f"{W}x{H} {ENG} touch back {i}: '{seq[i][0][:50]}' -> '{now[0][:50]}' (want '{seq[i-1][0][:50]}')")
      ck(len(seq)>=4,f"{W}x{H}: reached the Pittsburgh precincts ({len(seq)-1} levels)")
      ck(not er,f"{W}x{H}: no page errors {er[:2]}")
      await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
