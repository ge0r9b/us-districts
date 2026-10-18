# usage: python3 tests/build-check.py URL -- build 1557: an open tab picks up a newer deployed build (iOS Safari kept running a pre-1551 page, t283).
# The page reads the deployed BUILD from the first 2 KB of index.html (cache-busting ?bc=, no-store, Range) on load, on visibilitychange and
# pageshow; a newer BUILD reloads ONCE to ?v=<build> keeping the view hash; the same build never reloads; a target that is still stale after the
# reload is not retried (no loop, sessionStorage guard); BUILD sits in the first 2 KB of v2/index.html.
import asyncio,sys,json,re,os
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
here=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","v2","index.html")
head=open(here,"rb").read(2048).decode("utf-8","ignore"); m=re.search(r'window\.BUILD="(\d+)"',head)
ck(m is not None,"BUILD is inside the first 2 KB of v2/index.html (the Range check reads only that)")
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    async def ctx(fake):
      c=await b.new_context(viewport={'width':390,'height':844}); hits=[]; navs=[]
      async def route(r):
        hits.append([r.request.url,r.request.headers.get('range')])
        f=fake[0] if isinstance(fake,list) else fake
        if f is None: await r.continue_(); return
        await r.fulfill(status=206,headers={"content-type":"text/html"},body='<!DOCTYPE html>\n<script>window.BUILD="%s";</script>\n'%f)
      await c.route(re.compile(r".*/v2/(index\.html)?\?bc=\d+$"),route)
      pg=await c.new_page(); pg.on("request",lambda r: navs.append(r.url.split("#")[0]) if r.is_navigation_request() and r.frame==pg.main_frame else None); return c,pg,hits,navs  # document loads only (hash replaceState is not a load)
    # 1) same build deployed: one check on load, Range + no reload
    c,pg,hits,navs=await ctx(None); await pg.goto(U,wait_until="load"); await pg.wait_for_timeout(2500)
    B=await pg.evaluate("window.BUILD"); seen=await pg.evaluate("window.__updSeen||null")
    ck(len(hits)>=1 and hits[0][1]=='bytes=0-2047',"load: checks the deployed build with a cache-busted Range request",hits)
    ck(seen==B and len(navs)==1,"same build deployed: no reload",[seen,B,navs]); await c.close()
    # 2) newer build deployed: reloads once to ?v=<new>, keeping the hash; afterwards (still 'newer' because the fake persists) no second reload
    NEW=str(int(B)+1)
    c,pg,hits,navs=await ctx(NEW); await pg.goto(U+"#s=eyJ2IjoxfQ",wait_until="load"); await pg.wait_for_timeout(6000)
    ck(any(("?v="+NEW) in u for u in navs),"newer build: reloads to ?v=%s"%NEW,navs)
    ck(sum(1 for u in navs if "?v=" in u)==1 and len(navs)==2,"newer build that stays stale after the reload: exactly one reload (no loop)",navs)
    ck("#s=" in pg.url,"the reload keeps the view hash",pg.url)
    # 3) returning to the tab re-checks (visibilitychange) but the guard still holds for the same target
    n0=len(hits); await pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{value:'visible',configurable:true}); document.dispatchEvent(new Event('visibilitychange'));}"); await pg.wait_for_timeout(1500)
    ck(len(hits)>n0 and len(navs)==2,"visibilitychange re-checks, guard prevents a second reload for the same build",[len(hits)-n0,navs]); await c.close()
    # 4) a later, even newer build (a new target) does reload again
    hold=[NEW]; c,pg,hits,navs=await ctx(hold); await pg.goto(U,wait_until="load"); await pg.wait_for_timeout(5000); n=len(navs)
    NEW2=str(int(NEW)+1); hold[0]=NEW2; await pg.evaluate("()=>window.__updCheck(true)"); await pg.wait_for_timeout(3000)
    ck(len(navs)==n+1 and navs[-1].endswith("?v="+NEW2),"a newer target build later reloads again (once)",navs); await c.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
