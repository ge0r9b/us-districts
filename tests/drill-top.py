# Build 1552: drilling into a county row (scrolled far down the counties list) opens its townships list at the top, not at the old offset
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8843/v2/'; bad=[]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); await c.add_init_script("try{localStorage.clear()}catch(e){}"); pg=await c.new_page()
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=20000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
    for st,co,scroll in (("Wisconsin","Dane",0),("Wisconsin","Milwaukee",600),("Michigan","Kent",900)):
      await pg.evaluate("s=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&(b.title||b.textContent).startsWith(s)}).click()",st); await pg.wait_for_timeout(7000)
      await pg.evaluate("y=>{document.getElementById('listView').scrollTop=y}",scroll); await pg.wait_for_timeout(800)
      pre=await pg.evaluate("()=>document.getElementById('listView').scrollTop")
      ok=await pg.evaluate("s=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&(b.title||b.textContent).startsWith(s)}); if(!r) return false; r.scrollIntoView({block:'center'}); r.click(); return true}",co)
      for t in (500,1500,4000,8000):
        await pg.wait_for_timeout(t if t==500 else t-[500,1500,4000][[1500,4000,8000].index(t)])
        d=await pg.evaluate("()=>{const lv=document.getElementById('listView'); return [lv.scrollTop, window.__LA&&window.__LA.title, document.querySelectorAll('#listView .lvrow.la').length]}")
        print(st,co,'pre',pre,'clicked',ok,'t',t,d,flush=True)
      if d[0]!=0 or 'townships' not in str(d[1]): bad.append((co,d))
      # a re-render of the same list keeps the scroll position
      await pg.evaluate("()=>{document.getElementById('listView').scrollTop=150}"); await pg.wait_for_timeout(400); await pg.evaluate("()=>window.dispatchEvent(new Event('resize'))"); await pg.wait_for_timeout(1500)
      k=await pg.evaluate("()=>document.getElementById('listView').scrollTop"); print(' same list after resize',k)
      if d[2]>25 and abs(k-150)>2: bad.append((co,'kept',k))
      # back to states
      await pg.evaluate("()=>{window.__filterBack&&window.__filterBack()}"); await pg.wait_for_timeout(4000); await pg.evaluate("()=>{window.__filterBack&&window.__filterBack()}"); await pg.wait_for_timeout(4000)
    await b.close()
  print('FAILS',len(bad),bad); sys.exit(1 if bad else 0)
asyncio.run(main())
