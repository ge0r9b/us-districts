# Build 1569: the time slider has three points (2016, 2020, 2024). 2016 has a Hillary Clinton thumbnail in the Democratic slot
# (same answerId / colour / side as Biden and Harris; Trump the Republican answer every year). Until the 2016 data lands, 2016
# shows no data: gray map (no fills), list names without values, thumbnails without figures, a short note. Back to 2024 restores
# the values. The 2016 tap paints within 150 ms (4x CPU).
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
TAPX="""async(i)=>{const w=document.getElementById('ysl'),t=w.querySelector('.tk[data-i="'+i+'"]').getBoundingClientRect(),x=t.left+t.width/2,y=t.top+t.height/2;
 const lv=document.getElementById('listView');let t0,res;const done=new Promise(r=>res=r);
 const mo=new MutationObserver(()=>{mo.disconnect();requestAnimationFrame(()=>{const c=new MessageChannel();c.port1.onmessage=()=>res(performance.now()-t0);c.port2.postMessage(0)})});
 mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
 t0=performance.now();const o={bubbles:true,clientX:x,clientY:y,pointerId:7,pointerType:'touch',isPrimary:true};w.dispatchEvent(new PointerEvent('pointerdown',o));w.dispatchEvent(new PointerEvent('pointerup',o));
 setTimeout(()=>res(-1),3000);return Math.round(await done)}"""
ST="""()=>{const lv=document.getElementById('listView');const rows=[...lv.querySelectorAll('.lvrow.la')].slice(0,6);
 const vis=rows.map(r=>{const s=r.querySelector('.sbw');return s?getComputedStyle(s).visibility:'none'});
 const th=[...document.querySelectorAll('#laCands .lact')].map(b=>[b.dataset.cid,b.className,(b.querySelector('img')||{}).src||'',getComputedStyle(b.querySelector('.cpt')).visibility]);
 return {y16:document.body.classList.contains('y16'),vis,th,ticks:[...document.querySelectorAll('#ysl .tk span')].map(s=>s.textContent),lb:[...document.querySelectorAll('#ysl .ylb')].map(s=>s.textContent),
  note:getComputedStyle(lv.querySelector('.lvgrid'),'::before').content,C:['2016','2020','2024'].map(y=>window.__CANDS[y].map(c=>[c.short,c.ix,c.answerId,c.color,c.p]))}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in ((390,844),(1024,768)):
      c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=W<500,has_touch=True); pg=await c.new_page()
      er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
      s=await pg.evaluate(ST); t=f"{W}x{H}"
      ck(s['ticks']==['2016','2020','2024'] and s['lb']==["'16","'24"],f"{t}: slider has three points 2016 / 2020 / 2024",s)
      C=s['C']; ck(all(C[i][0][1:]==[0,'dem_nominee','#2563eb','d'] and C[i][1][1:]==[1,'rep_nominee','#dc2626','r'] and C[i][1][0]=='Trump' for i in range(3)) and C[0][0][0]=='Clinton',f"{t}: Clinton / Biden / Harris share the Democratic slot + colour, Trump Republican in every year",C)
      ck(not s['y16'] and all(v=='visible' for v in s['vis']),f"{t}: 2024 shows values",s['vis'])
      cdp=await c.new_cdp_session(pg); await cdp.send("Emulation.setCPUThrottlingRate",{"rate":4})
      ms=await pg.evaluate(TAPX,0); await cdp.send("Emulation.setCPUThrottlingRate",{"rate":1}); await pg.wait_for_timeout(1500)
      ck(0<ms<150,f"{t}: tap on 2016 answers in {ms}ms (<150, 4x CPU)",ms)
      s=await pg.evaluate(ST)
      ck(s['y16'] and all(v=='hidden' for v in s['vis']) and 'No 2016' in s['note'],f"{t}: 2016 = no data yet: names without values + note",s)
      th=s['th']; ck(len(th)==2 and th[0][0]=='c16' and 'clinton.jpg' in th[0][2] and ' d' in ' '+th[0][1] and th[1][0]=='t16' and 'trump.jpg' in th[1][2] and all(x[3]=='hidden' for x in th),f"{t}: Clinton (D, blue) + Trump (R) thumbnails, no figures",th)
      ok=await pg.evaluate("()=>new Promise(r=>{const i=new Image();i.onload=()=>r([i.naturalWidth,i.naturalHeight]);i.onerror=()=>r(null);i.src='img/clinton.jpg'})")
      ck(ok==[96,96],f"{t}: clinton.jpg loads (96x96, like the others)",ok)
      if W==390: await pg.screenshot(path='/workspace/y2016-list.png')
      await pg.evaluate(TAPX,2); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST)
      ck(not s['y16'] and all(v=='visible' for v in s['vis']) and s['th'][0][0] in ('h24','t24'),f"{t}: back to 2024 restores values + Harris/Trump",s)
      await pg.evaluate(TAPX,1); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST)
      ck(not s['y16'] and any(x[0]=='b20' for x in s['th']) and await pg.evaluate("()=>document.getElementById('yslider').value")=='0',f"{t}: middle point = 2020 (Biden)",s['th'])
      ck(not er,f"{t}: no page errors",er[:2]); await c.close()
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
