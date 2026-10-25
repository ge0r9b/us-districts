# Oct 25 (1621): QA-132 repro attempt - rapid district-type switching leaves map unshaded
import asyncio,sys,json,random,io
from playwright.async_api import async_playwright
from PIL import Image
from common import *
from gaps import typegq
ENG=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; N=int(sys.argv[3]) if len(sys.argv)>3 else 50
TYPES=['ushouse','senate','statehouse','schools','none']
LS="""()=>{let tot=0,filled=0,vis=0,cols={};try{map.eachLayer(l=>{if(l.options&&l.options.fillColor!==undefined||l.feature){tot++;const o=l.options||{};if(o.fillOpacity>0&&o.fill!==false&&o.fillColor){filled++;const c=String(o.fillColor);cols[c]=(cols[c]||0)+1;}}});}catch(e){return {err:String(e)}}
 const on=document.querySelector('#lyrRow .lbtn.on');const top=Object.entries(cols).sort((a,b)=>b[1]-a[1]).slice(0,4);
 return {tot,filled,ncol:Object.keys(cols).length,top,on:on&&on.dataset.k,z:+map.getZoom().toFixed(2),build:window.BUILD}}"""
def pix(png):
  im=Image.open(io.BytesIO(png)).convert('RGB'); w,h=im.size; im=im.crop((0,int(h*.12),int(w*.8),int(h*.8))).resize((160,160))
  r=b=n=0
  for (R,G,B) in im.get_flattened_data():
    n+=1
    if R>170 and G<150 and B<140 and R>G+50: r+=1
    elif B>150 and R<130 and B>R+60 and B>G+20: b+=1
  return round(r/n,3),round(b/n,3)
async def main():
  out=[]; tag=f'shotsb1621/q132-{ENG[:2]}-{W}x{H}'
  async with async_playwright() as p:
    br=await getattr(p,ENG).launch()
    c,pg,log=await ctx(br,W,H,True,ENG)
    if ENG=='chromium':
      cd=await c.new_cdp_session(pg); await cd.send('Emulation.setCPUThrottlingRate',{'rate':4})
    slow={'on':False}
    async def rt(route):
      if slow['on']: await asyncio.sleep(random.uniform(.2,1.5))
      await route.continue_()
    await pg.route('**/*',rt)
    await pg.goto(URL+'?cb=q132',wait_until='networkidle',timeout=180000); await pg.wait_for_timeout(3000)
    async def pick(k):
      if not await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"):
        xy=await center(pg,'#bLyr'); 
        if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(120)
      if k=='none':
        xy=await center(pg,'#lyrRow .lbtn.on')
      else: xy=await center(pg,f'#lyrRow .lbtn[data-k={k}]')
      if xy: await pg.touchscreen.tap(*xy)
      await pg.wait_for_timeout(random.choice([30,80,150,300]))
    async def goto_view(v):
      await pg.evaluate("v=>map.setView(v[0],v[1],{animate:false})",V[v]); await pg.wait_for_timeout(4000)
    V={'US':[[39,-97],4],'Pennsylvania':[[40.9,-77.7],7],'Texas':[[31,-99],6],'California':[[37,-119.5],6],'Allegheny County, PA':[[40.45,-80],10]}
    views=['US','Pennsylvania','Texas','California','Allegheny County, PA']
    fails=0
    for i in range(N):
      v=views[(i//10)%len(views)]
      if i%10==0 or i%10==5:
        slow['on']=False
        try: await goto_view(v)
        except Exception as e: print('view err',e)
      slow['on']=(i%2==0)
      mode=i%4
      if mode==0: seq=[random.choice(TYPES) for _ in range(6)]
      elif mode==1: a,b=random.sample(TYPES[:4],2); seq=[a,b]*4
      elif mode==2: a=random.choice(TYPES[:4]); seq=[a,a,a]
      else: seq=[random.choice(TYPES) for _ in range(10)]
      for k in seq:
        try: await pick(k)
        except Exception as e: pass
      xy=await center(pg,'#bLyr')
      if xy and await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): pass
      slow['on']=False; await pg.wait_for_timeout(3000)
      s=await pg.evaluate(LS); png=await pg.screenshot(); s['red'],s['blue']=pix(png)
      s.update(i=i,view=v,seq=seq,slow=(i%2==0))
      bad=(s['red']+s['blue']<0.02) or s.get('filled',1)==0 or s.get('ncol',2)<=1
      s['bad']=bad
      if bad:
        fails+=1; open(f'{tag}-FAIL-{i:02d}.png','wb').write(png)
        # recovery tries
        await pg.touchscreen.tap(*(await center(pg,'#bLyr')) or (W//2,H//2)); await pg.wait_for_timeout(200)
        await pg.mouse.wheel(0,-200); await pg.wait_for_timeout(3000)
        r=await pg.evaluate(LS); png2=await pg.screenshot(); r['red'],r['blue']=pix(png2); s['after_zoom']=r
        open(f'{tag}-FAIL-{i:02d}-after.png','wb').write(png2)
      elif i%10==0: open(f'{tag}-pass-{i:02d}.png','wb').write(png)
      out.append(s); print(json.dumps(s),flush=True)
    print('FAILS',fails,'/',N,'pageerr',log['pageerr'][:5],'console',log['console'][:5],flush=True)
    json.dump({'runs':out,'log':{k:v[:20] for k,v in log.items()}},open(f'b1621y-q132-{ENG}-{W}x{H}.json','w'),indent=1)
    await br.close()
asyncio.run(main())
