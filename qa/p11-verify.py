# pass 11 verify: (A) '#' pick at 375 All States list -> cpanel shift; (B) address Enter from Allegheny County pie view (restored state)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
BOX="""()=>{const o={};const add=(k,e)=>{if(!e)return;const r=e.getBoundingClientRect();if(!r.width)return;o[k]=[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]};
add('cpanel',document.querySelector('.cpanel'));add('chartBtn',document.querySelector('#chartBox .cmain'));add('bNum',document.getElementById('bNum'));
[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).forEach((e,i)=>add('thumb'+i,e));add('firstRow',[...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent));add('laSort',document.getElementById('laSort'));return o}"""
SAMPLE="(ms)=>new Promise(res=>{const fr=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;fr.push([Math.round(t),(%s)()]);if(t<ms)requestAnimationFrame(f);else res(fr)};requestAnimationFrame(f)})"%BOX
def moves(fr):
  out=[];prev=fr[0][1]
  for t,b in fr[1:]:
    for k,v in b.items():
      if k in prev and prev[k]!=v: out.append((t,k,prev[k],v))
    prev=b
  return out
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); tag=f"{W}x{H}"; o={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for run in range(2):
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      xy=await center(pg,'#bGeo'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1500)
      xy=await center(pg,'li.la-row'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>{window.__cls=0;window.__shifts=[]}")
      xy=await center(pg,'#bNum'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1500)
      opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
      o[f'A{run}_opt']=opt
      if opt:
        await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{tag}-num-before.png")
        fut=asyncio.ensure_future(pg.evaluate(SAMPLE,1500)); await pg.wait_for_timeout(30); await pg.touchscreen.tap(*opt); fr=await fut
        o[f'A{run}_moves']=moves(fr)[:12]
        await pg.wait_for_timeout(1000); await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{tag}-num-after.png")
      o[f'A{run}_num']=await pg.evaluate("()=>window.__numMode()"); o[f'A{run}_cls']=await pg.evaluate("()=>[window.__cls,window.__shifts]")
      await c.close()
    # B: address from restored Allegheny state
    c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await typegq(pg,"Allegheny County, PA"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000)
    o['B_before']=await pg.evaluate(ST)
    await typegq(pg,"1600 Pennsylvania Ave NW, Washington, DC 20500"); o['B_sugg']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,60)).slice(0,4)")
    await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000); o['B_enter']=await pg.evaluate(ST); await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{tag}-addr-from-county.png")
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000); o['B_reload']=await pg.evaluate(ST)
    await typegq(pg,"350 5th Ave, New York, NY 10118"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000); o['B_enter_after_reload']=await pg.evaluate(ST)
    await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{tag}-addr-after-reload.png")
    o['err']=log['pageerr']+log['console'][:5]; await c.close()
  json.dump(o,open(f'b1576p11-verify-{eng}-{tag}.json','w'),indent=1); print(json.dumps(o)[:4000])
if __name__=='__main__': asyncio.run(main())
