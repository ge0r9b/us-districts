import asyncio,json,time,statistics as st
from playwright.async_api import async_playwright
# A/B startup (DCL/first map/longest task) of two index.html roots on the local GH-Pages-like server (tools/serve.py /tmp/ab 8871, roots /tmp/ab/{a,b} = repo symlinks + one index.html each), 390x844, alternating order, 7 reps
INIT=open('/workspace/w/perf-wt/qa/perf/tools/baseline.py').read().split('INIT="""')[1].split('"""')[0]%""
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
async def main():
  out={'a':[],'b':[]}
  async with async_playwright() as p:
    b=await p.chromium.launch(args=["--enable-precise-memory-info"])
    for rep in range(7):
      for v in ('a','b') if rep%2==0 else ('b','a'):
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True,user_agent=UA); await c.add_init_script(INIT)
        pg=await c.new_page(); await pg.goto(f"http://127.0.0.1:8871/{v}/v2/?v={int(time.time()*1000)}",wait_until="load",timeout=120000)
        try: await pg.wait_for_load_state("networkidle",timeout=30000)
        except Exception: pass
        await pg.wait_for_timeout(2000)
        T=await pg.evaluate("""()=>{const n=performance.getEntriesByType('navigation')[0];const f=window.__fm;return {build:window.BUILD,html_done:Math.round(n.responseEnd),dcl:Math.round(n.domContentLoadedEventEnd),first_map:Math.round(Math.max(f.vec||0,f.tile||0)),longest_task:Math.max(0,...__lt.map(x=>x[1])),lt_ms:__lt.reduce((a,x)=>a+x[1],0)}}""")
        out[v].append(T); print(v,rep,T,flush=True); await c.close()
    await b.close()
  for v in out: print(v,{k:round(st.median([t[k] for t in out[v]])) for k in ['dcl','first_map','longest_task','lt_ms']})
asyncio.run(main())
