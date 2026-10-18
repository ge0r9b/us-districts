import asyncio,json,sys,random
from playwright.async_api import async_playwright
from common import *
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); N=int(sys.argv[4]); random.seed(1569)
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    seq=[]; slow=[]
    for i in range(N):
      # bias towards buttons/rows half the time
      if random.random()<0.5:
        xy=await pg.evaluate("()=>{const els=[...document.querySelectorAll('button,li,.lvrow,.cand,.lbtn,.kn,.trk')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth});if(!els.length)return null;const e=els[Math.floor(Math.random()*els.length)];const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,(e.id||e.className||e.tagName).toString().slice(0,25)]}")
        if not xy: xy=[random.uniform(5,W-5),random.uniform(5,H-5),'rand']
      else: xy=[random.uniform(5,W-5),random.uniform(5,H-5),'rand']
      if random.random()<0.08:
        await pg.keyboard.press(random.choice(['Escape','Enter','Backspace'])); seq.append((i,'key')); continue
      try:
        lat=await tap_latency(pg,xy[0],xy[1])
      except Exception as e:
        log['pageerr'].append('harness:'+str(e)[:80]); lat=None
      seq.append((i,xy[2],lat))
      if lat and lat>100: slow.append((i,xy[2],lat))
      await pg.wait_for_timeout(random.choice([60,150,400,900]))
      if i%50==49: await pg.screenshot(path=f"../shots/b1569-{eng[:2]}-{W}-monkey-{i+1}.png")
    alive=await pg.evaluate("()=>!!window.map&&document.body.childElementCount")
    st=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot()).slice(0,250)")
    await c.close(); await b.close()
  lats=[s[2] for s in seq if len(s)>2 and s[2]]
  print(json.dumps({'taps':len(seq),'alive':alive,'state':st,'pageerr':log['pageerr'][:10],'console':log['console'][:10],'reqfail':[r for r in log['reqfail'] if 'arcgisonline' not in r][:10],'http':log['http'][:10],
   'lat_median':sorted(lats)[len(lats)//2] if lats else None,'n_slow':len(slow),'slow_top':sorted(slow,key=lambda x:-x[2])[:12]},indent=0))
asyncio.run(main())
