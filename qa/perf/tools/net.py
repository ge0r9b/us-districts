# network + startup timing probe (one context, one viewport)
import asyncio,json,sys,time
from playwright.async_api import async_playwright
U=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3])
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=True,has_touch=True)
    pg=await c.new_page(); cdp=await c.new_cdp_session(pg)
    await cdp.send("Network.enable"); await cdp.send("Network.setCacheDisabled",{"cacheDisabled":True})
    R={}
    def onresp(e): R.setdefault(e['requestId'],{})['url']=e['response']['url']
    def ondata(e): r=R.setdefault(e['requestId'],{}); r['dec']=r.get('dec',0)+e['dataLength']
    def onfin(e): r=R.setdefault(e['requestId'],{}); r['enc']=e['encodedDataLength']; r['t']=time.time()
    cdp.on("Network.responseReceived",onresp); cdp.on("Network.dataReceived",ondata); cdp.on("Network.loadingFinished",onfin)
    t0=time.time()
    await pg.goto(U+("&" if "?" in U else "?")+"v=%d"%time.time(),wait_until="networkidle",timeout=120000)
    await pg.wait_for_timeout(3000)
    rs=sorted([dict(v,t=round(v.get('t',0)-t0,2)) for v in R.values() if 'url' in v],key=lambda x:-x.get('dec',0))
    for r in rs[:25]: print(r.get('enc'),r.get('dec'),r['t'],r['url'][:110])
    print('TOTAL enc',sum(r.get('enc',0) for r in rs),'dec',sum(r.get('dec',0) for r in rs),len(rs))
    await b.close()
asyncio.run(main())
