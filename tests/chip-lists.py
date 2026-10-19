# QA-099: the sort chip never covers a label of the first rows in FL/TX county lists and the Miami-Dade/Harris cities lists, time row open or closed. WebKit + Chromium 390/375/320.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500]),flush=True); (None if c else F.append(m))
NMX="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.textContent.trim()===t||e.textContent.trim().startsWith(t)); if(e){e.closest('.lvrow').click(); return true} return false}"
HIT="""()=>{ const s=document.getElementById('laSort'); if(getComputedStyle(s).display==='none') return {shown:false}; const c=s.getBoundingClientRect(); const lv=document.getElementById('listView'); const clip=lv.getBoundingClientRect().top; const r1=lv.querySelector('.lvrow.la'); const band=r1?r1.getBoundingClientRect().top-lv.getBoundingClientRect().top:0;
 const els=[...lv.querySelectorAll('.lvrow.la b, .lvrow.la em, .lvrow.la .cbv, .lvrow.la .net, .lvrow.la .nmx')].filter(e=>e.offsetParent);
 const bad=[]; for(const e of els){ const r=e.getBoundingClientRect(); if(!r.width||!r.height||!(e.textContent||'').trim()) continue; const top=Math.max(r.top,clip); if(top>=r.bottom) continue; if(r.left<c.right&&r.right>c.left&&top<c.bottom&&r.bottom>c.top) bad.push([e.className||e.tagName,(e.textContent||'').slice(0,12),Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]); }
 return {shown:true,band,chip:[c.left,c.top,c.right,c.bottom].map(Math.round),clip:Math.round(clip),bad:bad.slice(0,5),n:els.length} }"""

async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['webkit','chromium'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for W,H in ([(390,844),(375,667),(320,568)] if eng=='webkit' else [(390,844)]):
        for st,co in [('Florida','Miami-Dade'),('Texas','Harris')]:
          ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page()
          await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
          await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type(st); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
          await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
          await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
          for lvl in ['counties','cities']:
            if lvl=='cities': ck(await pg.evaluate(NMX,co),f"{eng} {W} open {co}"); await pg.wait_for_timeout(5000)
            for tm in [False,True]:
              hid=await pg.evaluate("()=>document.getElementById('barTime').hidden")
              if hid==tm: await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
              for num in ['pct','num']:
                await pg.evaluate(f"()=>window.__setNum('{num}')"); await pg.wait_for_timeout(1200)
                await pg.evaluate("()=>{document.getElementById('listView').scrollTop=0}"); await pg.wait_for_timeout(500)
                h=await pg.evaluate(HIT)
                ck(h['shown'] and not h['bad'],f"{eng} {W} {st} {lvl} time {'open' if tm else 'closed'} {num}: chip covers nothing",h)
          await ctx.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
