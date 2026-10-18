# b1575: every state + DC: rendered thumbnail size vs flag size (QA-045). One Chromium, sizes in sequence.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from cmp import AB
M="""()=>{const f=document.querySelector('#crumbs .cic img');const fr=f?f.getBoundingClientRect():null;
 const t=[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>{const i=e.querySelector('img'),r=i?i.getBoundingClientRect():null;return r?[+r.width.toFixed(1),+r.height.toFixed(1)]:null});
 return {crumb:document.getElementById('crumbs').innerText,flag:f?(f.getAttribute('src')||'').split('/').pop().split('?')[0]:null,fnat:f?[f.naturalWidth,f.naturalHeight]:null,frend:fr?[+fr.width.toFixed(1),+fr.height.toFixed(1)]:null,thumbs:t,thw:getComputedStyle(document.documentElement).getPropertyValue('--thw')}}"""
async def main():
  names=dict(AB); out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    SZ={'1024x768':(1024,768),'390':(390,844)}
    for tag in sys.argv[1].split(','):
      W,H=SZ[tag]
      c,pg,log=await ctx(b,W,H,W<600)
      await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map&&document.getElementById('state').options.length>40",timeout=90000); await pg.wait_for_timeout(4000)
      R=out[tag]={'build':await pg.evaluate('window.BUILD'),'US':await pg.evaluate(M),'states':{}}
      R['opts']=await pg.evaluate("()=>[...document.getElementById('state').options].map(o=>o.value).filter(v=>/Col|DC/.test(v))")
      for i,(a,n) in enumerate([kv for kv in sorted(names.items(),key=lambda kv:kv[1]) if len(sys.argv)<3 or kv[0] in sys.argv[2].split(',')]):
        if i and i%8==0:
          prev=a
          await c.close(); c,pg,log=await ctx(b,W,H,W<600)
          await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map&&document.getElementById('state').options.length>40",timeout=90000); await pg.wait_for_timeout(3000)
          R.setdefault('fresh_before',[]).append(a)
        ok=await pg.evaluate("n=>{const s=document.getElementById('state');if(![...s.options].some(o=>o.value===n))return false;s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}));return true}",n)
        await pg.wait_for_timeout(300); early=await pg.evaluate(M)
        await pg.wait_for_timeout(2700); late=await pg.evaluate(M)
        R['states'][a]={'ok':ok,'early':early,'late':late}
        if a in ('AL','GA','DC','OH','NE') : await pg.screenshot(path=f'../shots/b1575-thumbs-ch-{tag}-{a}.png')
        json.dump(out,open(f'b1575-thumbs-{sys.argv[1]}{"-"+sys.argv[2][:8] if len(sys.argv)>2 else ""}.json','w'),indent=1)
        print(tag,a,ok,late['flag'],late['fnat'],late['frend'],late['thumbs'][:1],'early',early['thumbs'][:1],flush=True)
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='';s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(3000)
      R['back_US']=await pg.evaluate(M); R['err']=log['pageerr'][:5]
      await c.close()
    await b.close()
  json.dump(out,open(f'b1575-thumbs-{sys.argv[1]}{"-"+sys.argv[2][:8] if len(sys.argv)>2 else ""}.json','w'),indent=1)
asyncio.run(main())
