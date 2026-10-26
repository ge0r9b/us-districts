import asyncio,sys,time,collections
from playwright.async_api import async_playwright
def key(cf): return f"{cf['functionName'] or '(anon)'} @{cf['url'].split('/')[-1].split('?')[0][:20]}:{cf['lineNumber']+1}"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=await c.new_page(); cdp=await c.new_cdp_session(pg)
    await pg.goto("http://localhost:8844/v2/?v=%d"%time.time(),wait_until="networkidle"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Texas';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(9000)
    await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
    await cdp.send("Profiler.enable"); await cdp.send("Profiler.setSamplingInterval",{"interval":200}); await cdp.send("Profiler.start")
    t=await pg.evaluate("async()=>{const t0=performance.now();document.querySelector('#lyrRow .lbtn[data-k=schools]').click();await new Promise(r=>requestAnimationFrame(()=>setTimeout(r,0)));return performance.now()-t0}")
    pr=(await cdp.send("Profiler.stop"))['profile']
    nodes={n['id']:n for n in pr['nodes']}; par={}
    for n in pr['nodes']:
      for ch in n.get('children',[]): par[ch]=n['id']
    dt=collections.Counter()
    for sid,d in zip(pr['samples'],pr['timeDeltas']): dt[sid]+=d
    se=collections.Counter(); inc=collections.Counter()
    for i,us in dt.items():
      se[key(nodes[i]['callFrame'])]+=us; seen=set(); j=i
      while j is not None:
        k=key(nodes[j]['callFrame'])
        if k not in seen: inc[k]+=us; seen.add(k)
        j=par.get(j)
    print("tap->paint",round(t,1))
    for k,us in se.most_common(14): print(' self %7.1f %s'%(us/1000,k))
    for k,us in inc.most_common(40): print(' incl %7.1f %s'%(us/1000,k))
    await b.close()
asyncio.run(main())
