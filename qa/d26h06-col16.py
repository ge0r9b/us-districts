# Oct 26 ~6 AM (1622) copy of h0400-col16.py
# pass 20 (build 1589): '16 district map colours by touch: share of blue vs red pixels on the map, sample points, tap a district and read the thumbnails
import asyncio,sys,json,io
from PIL import Image
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
LBL="()=>[...document.querySelectorAll('#cands .cand')].filter(e=>e.offsetParent).map(e=>[e.getAttribute('aria-label')||'',(e.querySelector('.cpt')||e).innerText.replace(/\\n/g,' ').trim()])"
PTS={"Philadelphia":(39.985,-75.15,"D"),"Pittsburgh":(40.44,-79.99,"D"),"rural PA":(40.75,-77.6,"R"),"Lancaster":(40.04,-76.25,"R")}
async def main():
  eng=sys.argv[1]; which=sys.argv[2:]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      s=tag.replace('iphone','').replace('ipad',''); pre=f"../shots/b1622d26h06c16-{eng[:2]}-{s}"
      for st,typ in [("",'ushouse'),("Pennsylvania",None),("Pennsylvania","ushouse"),("Pennsylvania","senate"),("Pennsylvania","statehouse")]:
        k=f"{st or 'US'}-{typ or 'map'}"; R=out[f"{tag} {k}"]={}
        c,pg,log=await ctx(b,W,H,mob,eng)
        async def tap(sel,w=1500):
          xy=await center(pg,sel)
          if xy: l=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return l
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
        if st: await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
        if typ:
          await tap('#bLyr',900); R['lat_layer']=await tap(f'.lbtn[data-k={typ}]',5000)
          if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',700)
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
        for i,yr in [(0,'2016'),(2,'2024')]:
          xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
          R[f'lat_{yr}']=await tap_latency(pg,*xy); await pg.wait_for_timeout(8000)
          img=Image.open(io.BytesIO(await pg.screenshot())).convert('RGB'); sc=img.width/W
          mr=await pg.evaluate("()=>{const r=document.getElementById('map').getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}")
          bl=rd=gr=0
          for X in range(int(mr[0])+5,int(mr[2])-5,6):
            for Y in range(int(mr[1])+150,int(mr[3])-150,6):
              q=img.getpixel((int(X*sc),int(Y*sc))); r_,g_,b_=q
              if b_>r_+25: bl+=1
              elif r_>b_+25: rd+=1
              elif abs(r_-g_)<8 and abs(g_-b_)<8 and r_<235: gr+=1
          tot=bl+rd or 1; R[f'px_{yr}']={'blue%':round(bl/tot*100,1),'red%':round(rd/tot*100,1),'gray_n':gr}
          R[f'lbl_{yr}']=await pg.evaluate(LBL)
          if yr=='2016': await pg.screenshot(path=f'{pre}-col16-{k}.png')
        # sample points at 2016 after pan
        xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",0)
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(7000); res={}
        for nm,(la,lo,win) in PTS.items():
          X,Y=await pg.evaluate(f"()=>{{ window.__map.setView([{la},{lo}],9,{{animate:false}}); const q=window.__map.latLngToContainerPoint([{la},{lo}]); const r=window.__map.getContainer().getBoundingClientRect(); return [q.x+r.left,q.y+r.top]}}")
          await pg.wait_for_timeout(2200); img=Image.open(io.BytesIO(await pg.screenshot())).convert('RGB'); sc=img.width/W
          px=[img.getpixel((int((X+dx)*sc),int((Y+dy)*sc))) for dx in (-6,0,6) for dy in (-6,0,6)]
          r_=sorted(q[0] for q in px)[4]; b_=sorted(q[2] for q in px)[4]; got='D' if b_>r_+25 else 'R' if r_>b_+25 else '?'
          res[nm]=[got,win,px[4]]
        R['pts16']=res; R['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; R['build']=await pg.evaluate('window.BUILD')
        print(tag,k,json.dumps(R)[:1500],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1622d26h06-col16-{eng}-'+'_'.join(which)+'.json','w'),indent=1)
asyncio.run(main())
