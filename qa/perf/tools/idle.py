# main-thread cost while the user does nothing (polling timers): CDP Performance metrics delta over 10 s idle, map view and All States list view
import asyncio,json,sys,time
from playwright.async_api import async_playwright
U=sys.argv[1]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page(); cdp=await c.new_cdp_session(pg)
    await cdp.send("Performance.enable")
    await pg.goto(U+"?v=%d"%time.time(),wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    async def m():
      r=await cdp.send("Performance.getMetrics"); return {x['name']:x['value'] for x in r['metrics']}
    async def idle(name,sec=10):
      a=await m(); await pg.wait_for_timeout(sec*1000); z=await m()
      d={k:round(z[k]-a[k],3) for k in ('TaskDuration','ScriptDuration','LayoutDuration','RecalcStyleDuration','LayoutCount','RecalcStyleCount')}
      d['busy_pct']=round(100*d['TaskDuration']/sec,1); print(name,json.dumps(d),flush=True); return d
    out={'map':await idle('map_idle')}
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    out['list']=await idle('allstates_list_idle')
    await b.close(); print(json.dumps(out))
asyncio.run(main())
