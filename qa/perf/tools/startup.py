# cold visit vs repeat visit after a build bump (index.html BUILD changes), prototype roots on the local GH-Pages-like server
# usage: startup.py <variant,...> <reps> <out.json>     (variants are dirs under /workspace/perf/proto)
import asyncio,json,sys,time,re
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8857/%s/v2/"; P='/workspace/perf/proto/%s/v2/index.html'
INIT=open(__file__.replace('startup.py','baseline.py')).read().split('INIT="""')[1].split('"""')[0]%""
def bump(v,b):
  s=open(P%v).read(); s=re.sub(r'window\.BUILD="\d+"','window.BUILD="%s"'%b,s,1); open(P%v,'w').write(s)
async def visit(pg,url,NET):
  NET.clear()
  await pg.goto(url+"?v=%d"%(time.time()*1000),wait_until="load",timeout=120000)
  await pg.wait_for_load_state("networkidle"); await pg.wait_for_timeout(1500)
  T=await pg.evaluate("""()=>{const n=performance.getEntriesByType('navigation')[0];const f=window.__fm;return {dcl:Math.round(n.domContentLoadedEventEnd),load:Math.round(n.loadEventEnd),first_map:Math.round(Math.max(f.vec||0,f.tile||0)),first_vector_map:Math.round(f.vec||0),longtasks_ms:__lt.reduce((a,x)=>a+x[1],0),longest_task:Math.max(0,...__lt.map(x=>x[1]))}}""")
  T['initial_enc']=sum(r.get('enc',0) for r in NET.values() if '127.0.0.1' in r.get('url',''))
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3000)
  await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'}).click()")
  await pg.wait_for_timeout(2000); await pg.wait_for_load_state("networkidle"); await pg.wait_for_timeout(4000)
  app=[r for r in NET.values() if '127.0.0.1' in r.get('url','')]
  T.update(pa_enc=sum(r.get('enc',0) for r in app),pa_req=len(app),pa_rows=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length"))
  return T
async def main():
  vs=sys.argv[1].split(','); reps=int(sys.argv[2]); out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for rep in range(reps):
      for v in vs:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); await c.add_init_script(INIT)
        pg=await c.new_page(); cdp=await c.new_cdp_session(pg); await cdp.send("Network.enable"); NET={}
        cdp.on("Network.responseReceived",lambda e: NET.setdefault(e['requestId'],{}).update(url=e['response']['url']))
        cdp.on("Network.loadingFinished",lambda e: NET.setdefault(e['requestId'],{}).update(enc=e['encodedDataLength']))
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)[:150]))
        bump(v,"202610181575"); cold=await visit(pg,BASE%v,NET)
        bump(v,"202610181576"); rep2=await visit(pg,BASE%v,NET); bump(v,"202610181575")
        out.setdefault(v,[]).append({'cold':cold,'after_bump':rep2,'errors':errs}); print(v,rep,json.dumps(out[v][-1]),flush=True); await c.close()
    await b.close()
  json.dump(out,open(sys.argv[3],'w'),indent=1)
asyncio.run(main())
