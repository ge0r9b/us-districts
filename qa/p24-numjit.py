# pass 24: after % > # on the All States list, sample positions per frame for 4 s + layout-shift sources
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
SAMP="""(ms)=>new Promise(res=>{const o=[];const t0=performance.now();let last='';const sel=['#laSort','#bNum','#bTime','#laCands','#listView'];
const f=()=>{const t=performance.now()-t0;const rows=[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).slice(0,4).map(e=>{const r=e.getBoundingClientRect();const v=[...e.querySelectorAll('*')].filter(x=>x.childElementCount===0&&x.textContent.trim()).map(x=>{const q=x.getBoundingClientRect();return x.textContent.trim().slice(0,8)+'@'+Math.round(q.left)+','+Math.round(q.top)}).join(' ');return Math.round(r.top)+'/'+Math.round(r.height)+' '+v});
const els=sel.map(s=>{const e=document.querySelector(s);if(!e)return s+':none';const r=e.getBoundingClientRect();return s+':'+Math.round(r.left)+','+Math.round(r.top)+','+Math.round(r.width)+'x'+Math.round(r.height)});
const k=JSON.stringify([rows,els]);if(k!==last){o.push([Math.round(t),k]);last=k}
if(t<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"""
LS="""()=>{window.__ls2=[];try{new PerformanceObserver(l=>{for(const e of l.getEntries())window.__ls2.push({v:+e.value.toFixed(4),hri:e.hadRecentInput,t:Math.round(e.startTime),src:(e.sources||[]).map(s=>{const n=s.node;const d=n&&n.nodeType===1?(n.id||n.className||n.nodeName):(n?('#text:'+(n.textContent||'').slice(0,10)+' in '+(n.parentElement&&(n.parentElement.id||n.parentElement.className))):'?');return String(d).slice(0,50)+' '+JSON.stringify([s.previousRect.x,s.previousRect.y,s.previousRect.width,s.previousRect.height].map(Math.round))+'>'+JSON.stringify([s.currentRect.x,s.currentRect.y,s.currentRect.width,s.currentRect.height].map(Math.round))})})}).observe({type:'layout-shift'})}catch(e){}}"""
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    if len(sys.argv)>4:
      await pg.touchscreen.tap(*(await center(pg,'#laSort'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'#laSort'))); await pg.wait_for_timeout(2200)
    out['pct_rest']=await pg.evaluate(SAMP,2000)
    await pg.evaluate(LS)
    await pg.touchscreen.tap(*(await center(pg,'#bNum'))); out['chooser_open']=await pg.evaluate(SAMP,3000); await pg.screenshot(path=f'../shots/b1596p24-{eng[:2]}-{W}-numjit-chooser.png')
    opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
    out['opt']=opt
    if opt: await pg.touchscreen.tap(*opt)
    out['num_mode']=await pg.evaluate("()=>window.__numMode()")
    out['after_num']=await pg.evaluate(SAMP,5000)
    await pg.wait_for_timeout(3000); out['num_rest_later']=await pg.evaluate(SAMP,3000)
    out['ls']=await pg.evaluate("()=>window.__ls2")
    await safeshot(pg,f'../shots/b1596p24-{eng[:2]}-{W}-numjit.png')
    out['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; out['build']=await pg.evaluate('window.BUILD')
    await c.close(); await b.close()
  json.dump(out,open(f'b1596p24-numjit{len(sys.argv)}-{eng}-{W}x{H}.json','w'),indent=1)
  for k in ('chooser_open','pct_rest','after_num','num_rest_later'): print(k,'changes',len(out[k]))
  print('ls',len(out['ls']),json.dumps(out['ls'][:6])[:1500]); print('mode',out['num_mode'],'opt',out['opt'],'err',out['err'],out['build'])
asyncio.run(main())
