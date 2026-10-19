# pass 29 (build 1607): White House address from the map, the All States list and PA > Philadelphia townships; compare with tapping DC in All States.
# New: DC row selected + visible on screen, per-frame chrome positions during the scroll (thumbnails, top fields, right buttons, bottom bar).
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
src=open('p28-addr.py').read(); exec(src[src.index('NMXY='):src.index('ADDR=')])
src=open('p28b-lay3.py').read(); exec(src[src.index('BOX='):src.index('SAMPLE=')]); exec(src[src.index('TH=2'):src.index('async def main')])
DCST="""()=>{const lv=document.getElementById('listView');const r=[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent);
 const dc=r.find(x=>/^DC\\b/.test(x.innerText.trim()));let vis=null,box=null;
 if(dc){const b=dc.getBoundingClientRect();box=[Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height)];const L=lv?lv.getBoundingClientRect():{top:0,bottom:innerHeight};
  const cx=b.left+b.width/2,cy=b.top+b.height/2;const hit=document.elementFromPoint(cx,Math.min(innerHeight-1,Math.max(0,cy)));
  vis={inViewport:b.top>=0&&b.bottom<=innerHeight,inList:b.top>=L.top-1&&b.bottom<=L.bottom+1,listTop:Math.round(L.top),listBottom:Math.round(L.bottom),hitIsRow:!!(hit&&dc.contains(hit))}}
 const sel=r.filter(x=>/lasel/.test(x.className)).map(x=>x.innerText.split('\\n')[0]);
 return {nrows:r.length,dc:dc?{txt:dc.innerText.replace(/\\n/g,' | '),cls:dc.className,box,vis}:null,sel,scroll:lv?Math.round(lv.scrollTop):null,
  vtitle:(document.getElementById('vtitle')||{}).innerText,back:!!document.querySelector('#listView .lvback'),gq:document.getElementById('gq').value}}"""
REC="""(ms)=>{window.__fr=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;window.__fr.push([Math.round(t),(%s)(),(document.getElementById('listView')||{}).scrollTop|0]);if(t<ms)requestAnimationFrame(f)};requestAnimationFrame(f)}"""%BOX
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2].split(','); R={'eng':eng}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for sz in sizes:
     W,H=map(int,sz.split('x'))
     for i,sc in enumerate(sys.argv[3].split(',') if len(sys.argv)>3 else ['tapdc','allstates','phila','map']):
      c,pg,log=await ctx(b,W,H,True,eng); key=f"{sz}-{sc}"+(f"-r{i}" if len(sys.argv)>3 else '')
      try:
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
        if sc!='map':
          await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        if sc=='phila':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3500)
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Philadelphia'))); await pg.wait_for_timeout(3500)
        if sc=='tapdc':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'DC'))); await pg.wait_for_timeout(4000); before=None; fr=[]
        else:
          await pg.evaluate("()=>{const l=document.getElementById('listView');if(l)l.scrollTop=0}"); await pg.wait_for_timeout(400)
          before=await pg.evaluate(BOX)
          await pg.touchscreen.tap(*(await center(pg,"#gq"))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
          await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500)
          await pg.evaluate("()=>document.activeElement&&document.activeElement.blur&&0")
          await pg.evaluate(REC,7000); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7500)
          fr=await pg.evaluate("()=>window.__fr")
        after=await pg.evaluate(BOX)
        st=await pg.evaluate(ST); dcst=await pg.evaluate(DCST)
        await pg.screenshot(path=f"../shots/b{R['build'][-4:]}p29-{eng[:2]}-{sz}-addr-{sc}"+(f"-r{i}" if len(sys.argv)>3 else "")+".png")
        frames=[[t,o] for t,o,s in fr]; scrolls=[(t,s) for t,s in [(f[0],f[2]) for f in fr]]
        sc_ch=[];last=None
        for t,s in scrolls:
          if s!=last: sc_ch.append((t,s)); last=s
        R[key]={'st':st,'dc':dcst,'diff_before_after':diff(before,after) if before else None,
                'transient':{k:v for k,v in transient(frames,after).items() if k!='firstRow'} if frames else None,
                'scroll_changes':sc_ch[:20],'nframes':len(fr),'cls':await pg.evaluate("window.__cls"),'shifts':(await pg.evaluate("window.__shifts"))[-6:],
                'err':log['pageerr']+[x for x in log['console'] if x.startswith('error')],'reqfail':log['reqfail'][:5]}
        print(key,json.dumps({k:R[key][k] for k in ['st','dc','diff_before_after','transient','scroll_changes','err']})[:2500],flush=True)
      except Exception as e: R[key]={'EXC':str(e)[:300]}; print('EXC',key,e,flush=True)
      await c.close()
    await b.close()
  json.dump(R,open(f"b{R.get('build','0000')[-4:]}p29-addr-{eng}-{'_'.join(sizes)}{'-'+sys.argv[4] if len(sys.argv)>4 else ''}.json",'w'),indent=1)
asyncio.run(main())
