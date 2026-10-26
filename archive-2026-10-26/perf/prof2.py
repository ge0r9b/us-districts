# CPU-profile single taps (All States cold/warm, drill PA, back, US House pick) at 390x844; prints top self/inclusive functions
import asyncio,json,sys,time,collections
from playwright.async_api import async_playwright
U=sys.argv[1]
def key(cf): return f"{cf['functionName'] or '(anon)'} @{cf['url'].split('/')[-1].split('?')[0][:20]}:{cf['lineNumber']+1}:{cf['columnNumber']+1}"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page(); cdp=await c.new_cdp_session(pg)
    await pg.goto(U+"?v=%d"%time.time(),wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(3000)
    await cdp.send("Profiler.enable"); await cdp.send("Profiler.setSamplingInterval",{"interval":200})
    async def prof(name,js,wait=1500):
      await cdp.send("Profiler.start")
      t=await pg.evaluate("async js=>{const t0=performance.now();(0,eval)(js);await new Promise(r=>requestAnimationFrame(()=>setTimeout(r,0)));return performance.now()-t0}",js)
      pr=(await cdp.send("Profiler.stop"))["profile"]; await pg.wait_for_timeout(wait)
      nodes={n['id']:n for n in pr['nodes']}; par={}
      for n in pr['nodes']:
        for ch in n.get('children',[]): par[ch]=n['id']
      dt=collections.Counter()
      for sid,d in zip(pr['samples'],pr['timeDeltas']): dt[sid]+=d
      self_=collections.Counter(); inc=collections.Counter()
      for i,us in dt.items():
        self_[key(nodes[i]['callFrame'])]+=us; seen=set(); j=i
        while j is not None:
          k=key(nodes[j]['callFrame'])
          if k not in seen: inc[k]+=us; seen.add(k)
          j=par.get(j)
      print(f"== {name}: tap->paint {t:.1f} ms",flush=True)
      print(' self:'); [print('  %7.1f ms  %s'%(us/1000,k)) for k,us in self_.most_common(25) if '(idle)' not in k]
      print(' incl:'); [print('  %7.1f ms  %s'%(us/1000,k)) for k,us in inc.most_common(45) if '(idle)' not in k and '(root)' not in k]
    PA="[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'}).click()"
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await prof('all_states_cold',"document.querySelector('li.la-row').click()",3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await prof('all_states_warm',"document.querySelector('li.la-row').click()",3000)
    await prof('drill_PA',PA,5000)
    await prof('back',"document.getElementById('bBack').click()",3000)
    await pg.evaluate("()=>"+PA); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(1000)
    await prof('ushouse_pick',"document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()",4000)
    await b.close()
asyncio.run(main())
