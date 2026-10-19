# build 1592 (QA-079): turning the chart off (tap the chart button, then the same chart again) returns to the view the user
# came from: the map when it was opened from the map (never the empty gray list); a reload restores that view too.
# Opened from a list of places, it stays on that list.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300])); (None if c else F.append(m))
ST="()=>({lm:document.body.classList.contains('listmode'), la:document.body.classList.contains('listall'), ch:window.chartMode||null, rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).length, map:!!document.querySelector('.leaflet-container')&&getComputedStyle(document.getElementById('listView')).visibility!=='visible'})"
async def chart(pg,k=None):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
  if k: await pg.evaluate(f"()=>{{const b=[...document.querySelectorAll('#chartBox .copts button')].find(b=>b.dataset.ch==='{k}'); b?b.click():document.querySelector('[aria-label=Chart]').click()}}")
  else: await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()")
  await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      for st in ["","Pennsylvania","All States"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150])); tag=f"{W} {st or 'US'}"
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if st=="Pennsylvania": await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(3500)
        if st=="All States":
          await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
        s0=await pg.evaluate(ST)
        await chart(pg,"bar" if st=="All States" else "pie"); s1=await pg.evaluate(ST)
        ck(s1['lm'] and s1['ch'],f"{tag}: chart on shows the chart view",s1)
        await chart(pg); s2=await pg.evaluate(ST)
        if st=="All States": ck(s2['lm'] and s2['la'] and s2['rows']>=10 and not s2['ch'],f"{tag}: chart off from a list stays on the list rows",s2)
        else: ck(not s2['lm'] and not s2['ch'],f"{tag}: chart off returns to the map (never the empty list)",s2)
        await pg.wait_for_timeout(1500); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000); s3=await pg.evaluate(ST)
        if st=="All States": ck(s3['lm'] and s3['rows']>=10,f"{tag}: reload restores the list",s3)
        else: ck(not s3['lm'] and not s3['ch'],f"{tag}: reload restores the map",s3)
        ck(not er,f"{tag}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
