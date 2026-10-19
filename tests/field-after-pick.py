# QA-109: after a geography-filter pick the bottom field names the selection (never the county at the map centre); QA-110: 'Georgia' shows the US state flag. Chromium + WebKit 390.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400]),flush=True); (None if c else F.append(m))
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
ST="()=>({ph:document.getElementById('gq').placeholder,crumbs:(document.getElementById('crumbs')||{}).innerText||'',st:state.value,co:county.value,list:document.body.classList.contains('listmode')})"
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for sc,q,exp in [('fulton','Fulton','Fulton County, GA'),('ga','Georgia','Georgia'),('oh','Ohio','Ohio'),('nc','North Carolina','North Carolina'),('garow','Georgia','Georgia')]:
        c=await b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
        if sc=='garow':
          await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(4000)
          await pg.evaluate("()=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.textContent.trim()==='GA'||e.textContent.trim()==='Georgia'); e&&e.closest('.lvrow').click()}"); await pg.wait_for_timeout(5000)
          xy=await pg.evaluate(CEN,'#bGlobe')
          if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
        else:
          await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
          await pg.keyboard.type(q,delay=20); await pg.wait_for_timeout(2000)
          if sc=='ga':
            fl=await pg.evaluate("()=>{const l=[...document.querySelectorAll('li')].filter(l=>l.offsetParent&&/^Georgia\\s*$/.test((l.querySelector('.nm')||{}).textContent||'')).sort((a,b)=>b.getBoundingClientRect().top-a.getBoundingClientRect().top)[0]; const sv=l&&l.querySelector('svg'); const st=window.__stSil?window.__stSil('Georgia',null):''; return !!(sv&&st&&sv.outerHTML.slice(0,200)===st.slice(0,200))}")
            ck(fl,f"{eng} QA-110 the first 'Georgia' row (the one Enter picks) shows the US state, not the country",fl)
          if sc=='fulton':
            ok=await pg.evaluate("t=>{const l=[...document.querySelectorAll('li')].filter(e=>e.offsetParent&&e.textContent.includes(t)); if(l.length){l[0].click(); return true} return false}",exp)
            ck(ok,f"{eng} {sc}: result row '{exp}' tapped"); await pg.wait_for_timeout(4000)
            xy=await pg.evaluate(CEN,'#bGeo')
            if await pg.evaluate("()=>document.body.classList.contains('foldfs')||document.body.classList.contains('geofs')") and xy: await pg.touchscreen.tap(*xy)
          else: await pg.keyboard.press("Enter")
          await pg.wait_for_timeout(6000)
        a=await pg.evaluate(ST)
        ck(a['ph']==exp,f"{eng} {sc}: the field names the selection ({a['ph']!r}, want {exp!r})",a)
        await pg.wait_for_timeout(4000); a=await pg.evaluate(ST)
        ck(a['ph']==exp,f"{eng} {sc}: and still does 4 s later ({a['ph']!r})",a)
        ck(not er,f"{eng} {sc}: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
