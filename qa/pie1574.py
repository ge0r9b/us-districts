# QA pass 6 (build 1573): independent checks of the 1573 pie (thumbnails only, rank order, touch tap -> bubble, no overlap) and 1572 2016 per-unit map colours
import asyncio,sys,json,math
from playwright.async_api import async_playwright
from common import *
from restore import slider_to
PICK="""async(k)=>{const m=document.querySelector('button.rbtn.cmain');if(!m)return 'nomain';if(window.chartMode===k)return k;m.click();await new Promise(r=>setTimeout(r,350));const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch===k);if(b)b.click();else if(m.dataset.ch===k)m.click();return window.chartMode}"""
GEO="""()=>{const sv=[...document.querySelectorAll('.cpanel svg')].find(e=>e.getBoundingClientRect().width>60);
 const th=[...document.querySelectorAll('#cands .cand')].filter(b=>b.offsetParent).map(b=>{const r=b.getBoundingClientRect();const im=b.querySelector('img');return {t:b.title,r:[r.left,r.top,r.right,r.bottom].map(Math.round),img:im?[im.naturalWidth,Math.round(im.getBoundingClientRect().width),Math.round(im.getBoundingClientRect().height)]:null,txt:[...b.querySelectorAll('*')].filter(e=>e.childElementCount===0&&e.textContent.trim()&&e.getBoundingClientRect().width>0&&getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).opacity!=='0').map(e=>e.textContent.trim())}});
 const btn=[...document.querySelectorAll('button.rbtn,#laSort,#bBack')].filter(b=>b.offsetParent).map(b=>{const r=b.getBoundingClientRect();return {id:b.id||b.className,r:[r.left,r.top,r.right,r.bottom].map(Math.round)}});
 const sl=[...document.querySelectorAll('.cpanel svg text')].filter(e=>e.getBoundingClientRect().width>0).map(e=>e.textContent);
 if(!sv)return {pie:null,th,btn};const q=sv.getBoundingClientRect();
 return {pie:[q.left+q.width/2,q.top+q.height/2,Math.min(q.width,q.height)/2].map(Math.round),svgtext:sl,th,btn,cpanel:(()=>{const c=document.querySelector('.cpanel');if(!c)return null;const r=c.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)})()}}"""
BUB="()=>{const b=[...document.querySelectorAll('body *')].filter(e=>e.childElementCount===0&&/ · .*\\d/.test(e.textContent)&&e.getBoundingClientRect().width>0&&getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).opacity!=='0').pop();if(!b)return null;const r=b.getBoundingClientRect();return {t:b.textContent.trim(),cls:b.className||b.id,r:[r.left,r.top,r.right,r.bottom].map(Math.round),off:r.left<0||r.right>innerWidth||r.top<0||r.bottom>innerHeight}}"
FILLS="""()=>{const o={};document.querySelectorAll('.leaflet-pane').forEach(p=>{const ps=[...p.querySelectorAll(':scope > svg path, :scope > svg g path')];const cv=p.querySelectorAll(':scope > canvas').length;if(!ps.length&&!cv)return;const f={};ps.forEach(e=>{const c=e.getAttribute('fill');f[c]=(f[c]||0)+1});o[p.className.replace('leaflet-pane ','').slice(0,40)]={vis:getComputedStyle(p).display!=='none'&&getComputedStyle(p).visibility!=='hidden',paths:ps.length,canvas:cv,distinct:Object.keys(f).length,top:Object.entries(f).sort((a,b)=>b[1]-a[1]).slice(0,4)}});return o}"""
async def main():
  eng=sys.argv[1]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in [v for v in VPS if not sys.argv[2:] or v[0] in sys.argv[2:]]:
      s=tag.replace('iphone','').replace('ipad','')
      c,pg,log=await ctx(b,W,H,mob,eng); R={}
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000)
      R['build']=await pg.evaluate("()=>window.BUILD")
      for scope in ('US','MA','PA'):
        if scope!='US':
          await pg.evaluate("n=>{const s=document.getElementById('state');s.value=n;s.onchange&&s.onchange()}",{'MA':'Massachusetts','PA':'Pennsylvania'}[scope]); await pg.wait_for_timeout(5000)
        for nm in ('num','pct'):
          await pg.evaluate("m=>window.__setNum(m)",nm); await pg.wait_for_timeout(700)
          R[f'{scope} {nm} mode']=await pg.evaluate(PICK,'pie'); await pg.wait_for_timeout(2200)
          g=await pg.evaluate(GEO); bad=[]
          if not g['pie']: bad.append('no pie svg')
          else:
            cx,cy,r=g['pie']
            def hit(q): nx=min(max(cx,q[0]),q[2]); ny=min(max(cy,q[1]),q[3]); return math.hypot(nx-cx,ny-cy)<r-1
            bad+= ['thumb over pie: '+x['t'][:20] for x in g['th'] if hit(x['r'])]
            bad+= ['btn over pie: '+x['id'][:20] for x in g['btn'] if hit(x['r'])]
          bad+= ['text beside thumb: '+x['t'][:15]+' '+str(x['txt']) for x in g['th'] if x['txt']]
          ys=[x['r'][1] for x in g['th']]
          if ys!=sorted(ys): bad.append('thumbs not top-down '+str(ys))
          bad+= ['thumb clipped '+x['t'][:15]+' '+str(x['r']) for x in g['th'] if x['r'][0]<0 or x['r'][2]>W or x['r'][3]>H]
          R[f'{scope} {nm} geo']={'n':len(g['th']),'order':[x['t'][:40] for x in g['th']],'svgtext':g.get('svgtext'),'bad':bad}
          await safeshot(pg,f"../shots/b1574-{eng[:2]}-{s}-pie-{scope}-{nm}.png")
          # touch tap each thumb -> bubble
          taps=[]
          for i in range(len(g['th'])):
            q=g['th'][i]['r']; x,y=(q[0]+q[2])/2,(q[1]+q[3])/2
            lat=await tap_latency(pg,x,y); await pg.wait_for_timeout(500); bb=await pg.evaluate(BUB)
            taps.append({'thumb':g['th'][i]['t'][:40],'lat':lat,'bub':bb})
            if i==0: await safeshot(pg,f"../shots/b1574-{eng[:2]}-{s}-pie-{scope}-{nm}-tap.png")
          R[f'{scope} {nm} taps']=taps
      # 2016 per-unit colours: back to US, states list, '16
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
      for yr,pos in (('2024',1),('2016',0)):
        await slider_to(pg,pos); await pg.wait_for_timeout(7000)
        R[f'fills states {yr}']=await pg.evaluate(FILLS); R[f'ymode {yr}']=await pg.evaluate("()=>window.__ymode&&window.__ymode()")
        await safeshot(pg,f"../shots/b1574-{eng[:2]}-{s}-map16-states-{yr}.png")
      R['err']=log['pageerr']+log['console']; out[tag]=R; await c.close(); print(tag,'done',flush=True)
    await b.close()
  json.dump(out,open(f'pie1574-{eng}.json','w'),indent=1)
asyncio.run(main())
