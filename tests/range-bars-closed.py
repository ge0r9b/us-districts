# build 1591 (QA-077): a range in the single-place Bar view always shows the range bars on the icon rows, time row open
# or closed (never the old labelled 'Republican +3.1 pts ... R+5.9 shift' block), wide, and clear of the button column.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
Q="""()=>{ const x=document.querySelector('#cands > .dmx, .dmx'); const vis=e=>e&&e.offsetParent&&e.getBoundingClientRect().width>0; const col=Math.min(...[...document.querySelectorAll('.rbtn')].map(b=>b.getBoundingClientRect()).filter(r=>r.width>0&&r.left>innerWidth-90).map(r=>r.left));
 const old=[...document.querySelectorAll('.cfoot,.lsh,.cpanel')].filter(vis).map(e=>e.textContent.slice(0,40)); const rows=x?[...x.querySelectorAll('.dmr')].filter(vis).map(r=>r.getBoundingClientRect()):[];
 return {dm:document.body.classList.contains('dmerge'), n:rows.length, right:rows.length?Math.max(...rows.map(r=>r.right)):0, w:x?x.getBoundingClientRect().width:0, col, old} }"""
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      for st in ["","Pennsylvania"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if st: await pg.evaluate(f"()=>{{const s=document.getElementById('state');s.value={json.dumps(st)};s.onchange&&s.onchange()}}"); await pg.wait_for_timeout(3500)
        await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
        await pg.evaluate("()=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch==='bar'); b&&b.click()}"); await pg.wait_for_timeout(2500)
        await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll() }"); await pg.wait_for_timeout(3000)
        for tm in ["open","closed","reopened"]:
          if tm!="open": await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
          q=await pg.evaluate(Q); tag=f"{W} {st or 'US'} range, time {tm}"
          ck(q['dm'] and q['n']==3 and not q['old'],f"{tag}: range bars on the icon rows, no old labelled block",q)
          ck(q['w']>=W*0.6 and q['right']<=q['col']-2,f"{tag}: bars wide ({q['w']:.0f}px) and clear of the button column",q)
        ck(not er,f"{W} {st or 'US'}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
