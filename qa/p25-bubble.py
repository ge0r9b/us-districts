# pass 25: QA-076 re-test on 1597. US bar (Trump + Harris thumbnails), range 2020>2024 bar (phones), PA drilled bar. Bounding boxes recorded.
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
TG="""()=>[...document.querySelectorAll('#cands .cand img, #cands img.dmt, #cands .dmoc')].filter(e=>e.offsetWidth&&getComputedStyle(e).visibility!=='hidden').map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)}).filter(r=>r[1]>0&&r[3]<innerHeight)"""
CHK="""([t,all])=>{ const e=document.getElementById('iconBub')||document.getElementById('partyBub'); if(!e) return {none:1}; const cs=getComputedStyle(e); const b=e.getBoundingClientRect(); const ov=(q)=>q.left<b.right-1&&q.right>b.left+1&&q.top<b.bottom-1&&q.bottom>b.top+1;
  const lbl=[...document.querySelectorAll('.cpanel *, #cands *')].filter(x=>x!==e&&!e.contains(x)&&!x.children.length&&x.offsetWidth&&(x.textContent||'').trim()).filter(x=>ov(x.getBoundingClientRect())).map(x=>x.textContent.trim().slice(0,14));
  const R=a=>({left:a[0],top:a[1],right:a[2],bottom:a[3]});
  const others=all.filter(a=>a.join()!==t.join()&&ov(R(a)));
  return {txt:e.textContent,op:cs.opacity,b:[b.left,b.top,b.right,b.bottom].map(Math.round),photo:t,overPhoto:ov(R(t)),overOther:others,lbl,gap:Math.round(b.left>=t[2]-1?b.left-t[2]:b.right<=t[0]+1?t[0]-b.right:(b.top>=t[3]-1?b.top-t[3]:(b.bottom<=t[1]+1?t[1]-b.bottom:0))),id:e.id,gq:(()=>{const g=document.getElementById('gq');if(!g)return null;let p=g;for(let k=0;k<3&&p.parentElement&&p.parentElement.getBoundingClientRect().width<innerWidth;k++)p=p.parentElement;const r=p.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)})(),inside:b.left>=0&&b.right<=innerWidth&&b.top>=0&&b.bottom<=innerHeight} }"""
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    scen=['us','range','pa'] if W<600 else ['us','pa']
    for sc in scen:
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      if sc=='pa':
        await typegq(pg,'Pennsylvania'); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      if sc=='range':
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(900)
        await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
        await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(900)  # close time row
      await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
      xy=await center(pg,'#chartBox .copts button[data-ch=bar]')
      await pg.touchscreen.tap(*(xy or await center(pg,'#chartBox .cmain')))
      await pg.wait_for_timeout(2500); out.setdefault('mode',{})[sc]=await pg.evaluate('()=>window.chartMode')
      tg=await pg.evaluate(TG); res=[]
      for i,t in enumerate(tg[:3]):
        await pg.touchscreen.tap((t[0]+t[2])/2,(t[1]+t[3])/2); await pg.wait_for_timeout(500)
        r=await pg.evaluate(CHK,[t,tg]); r['i']=i; res.append(r)
        ok=not r.get('none') and not r['overPhoto'] and not r['overOther'] and not r['lbl'] and r['inside'] and r['gap']<=60
        r['ok']=ok; print(eng,W,H,sc,i,'OK' if ok else 'FAIL',json.dumps(r),flush=True)
        await safeshot(pg,f'../shots/b1597p25-{eng[:2]}-{W}x{H}-bubble-{sc}-{i}.png')
        await pg.wait_for_timeout(3300)
      out[sc]={'thumbs':tg,'res':res,'err':log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3],'build':await pg.evaluate('()=>window.BUILD')}
      print(eng,W,H,sc,'err',out[sc]['err'],out[sc]['build'],flush=True)
      await c.close()
    await b.close()
  json.dump(out,open(f'b1597p25-bubble-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
