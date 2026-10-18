# Build 1546: list charts (bar/pie/line/change bars) use the left-edge candidate column (no per-row photos), ranked for the
# current selection, tap toggles a candidate (segment/slice/line hidden when off); a candidate without a photo shows a rank badge;
# sort (since 1551): % mode = share of the top-ranked selected answer, # mode = its votes (see list-sort-default.py), change mode = |net change| as displayed.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8765/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
ROWS="""()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>{const w={};r.querySelectorAll('.sbw .sg').forEach(s=>{const k=s.className.replace('sg ','').trim(); w[k]=parseFloat(s.style.width)||0}); const b=r.querySelector('.sbw'); return {n:r.querySelector('.nmx').textContent,w,bw:b?b.getBoundingClientRect().width:0,photos:r.querySelectorAll('img.sth,img.pth,img.lth').length,net:(r.querySelector('.net')||{}).textContent||''}})"""
TH="""()=>[...document.querySelectorAll('#laCands .lact')].map(b=>{const r=(b.querySelector('img,.lacn')).getBoundingClientRect(); return {id:b.dataset.cid,on:b.classList.contains('on'),cpt:b.querySelector('.cpt').textContent,badge:(b.querySelector('.lacn')||{}).textContent||'',x:r.left,cx:r.left+r.width/2,top:r.top,vis:getComputedStyle(document.getElementById('laCands')).display!=='none'}})"""
def mono(xs,desc=True,tol=0.051): return all((a>=b-tol) if desc else (a<=b+tol) for a,b in zip(xs,xs[1:]))
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=await c.new_page()
    er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    if (await pg.evaluate("()=>window.__laInfo().sort"))=='asc': await pg.evaluate("()=>document.getElementById('laSort').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500)
    t=await pg.evaluate(TH); r=await pg.evaluate(ROWS)
    ck(len(t)==2 and all(x['vis'] and x['on'] for x in t) and abs(t[0]['cx']-27)<=1.5 and t[0]['top']<t[1]['top'],"thumbnail column: 2 candidates, all on, stacked in the left-edge column (centre x 27)",t)
    ck(t[0]['id']=='t24' and t[0]['cpt']=='50%' and t[1]['cpt']=='48%',"ranked by the national totals (Trump 50%, Harris 48%)",t)
    ck(all(x['photos']==0 for x in r) and len(r)>=51,"no per-row candidate photos (51 rows)",r[:2])
    ck(all(x['w'].get('rep',0)>0 and x['w'].get('dem',0)>0 for x in r),"every row has candidate-coloured rep and dem segments",r[:3])
    lead=[x['w']['rep'] for x in r]; ck(mono(lead) and r[0]['n']=='WY',"% mode, all candidates on: rows sorted by the top thumbnail's (Trump) share",lead[:8])
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); r=await pg.evaluate(ROWS)
    bw=[x['bw'] for x in r]; tv=[x['bw']*x['w'].get('rep',0)/100 for x in r]; ck(mono(tv,tol=1.5) and r[0]['n']=='TX',"# mode: rows sorted by the top thumbnail's (Trump) votes (bar lengths on one scale, TX first)",[x['n'] for x in r[:4]]+bw[:4])
    ck(all(x['bw']>=2.5 for x in r),"# mode: every row shows its bar (small states too)",min(bw))
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('#laCands .lact[data-cid=h24]').click()"); await pg.wait_for_timeout(1500)
    t=await pg.evaluate(TH); r=await pg.evaluate(ROWS)
    ck([x['on'] for x in t if x['id']=='h24']==[False],"tap Harris thumbnail: deselected",t)
    ck(all('dem' not in x['w'] for x in r),"deselected candidate's segment hidden from every bar",r[:2])
    rs=[x['w'].get('rep',0) for x in r]; ck(mono(rs) and r[0]['n']=='WY',"% mode, Trump only: rows sorted by Trump's share (WY first)",[x['n'] for x in r[:3]]+rs[:3])
    await pg.evaluate("()=>document.querySelector('#laCands .lact[data-cid=h24]').click()"); await pg.wait_for_timeout(1200)
    ck(all(x['on'] for x in await pg.evaluate(TH)),"tap again: reselected")
    await pg.evaluate("()=>{ window.__phSave=__PHOTO.h24; delete __PHOTO.h24; window.__laThumbs(); }"); await pg.wait_for_timeout(300)
    t=await pg.evaluate(TH); ck(any(x['id']=='h24' and x['badge']=='2' for x in t),"candidate without a photo: rank-number badge",t)
    await pg.evaluate("()=>{ __PHOTO.h24=window.__phSave; window.__laThumbs(); }")
    # selection re-ranks: open Vermont (Harris leads)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='VT').click()"); await pg.wait_for_timeout(7000)
    t=await pg.evaluate(TH); ck(t and t[0]['id']=='h24',"after tapping VT the thumbnails re-rank to Vermont's results (Harris first)",t)
    # change mode: sort by |net change| as displayed
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); }"); await pg.wait_for_timeout(700)
    await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000); r=await pg.evaluate(ROWS)
    nets=[float(re.sub(r'[^\d.]','',x['net']) or 0) for x in r if x['net']]
    ck(len(nets)>=10 and mono(nets),"change mode: rows sorted by the displayed net change",nets[:6])
    ck(all(x['photos']==0 for x in r),"change bars: no per-row photos")
    ck(not er,"no page errors",er[:2])
    await b.close()
# build 1564: thumbnails fully visible with their full 2px ring; badges entirely visible, below the photo (not on the face), clear of the
# next thumbnail and of the row names -- PA US House districts, % and # mode, at 390 / 375 / 320 px phones and iPad.
FIT="""()=>{const C=document.getElementById('laCands'),cr=C.getBoundingClientRect(),cl={l:cr.left+C.clientLeft,t:cr.top+C.clientTop,r:cr.left+C.clientLeft+C.clientWidth,b:cr.top+C.clientTop+C.clientHeight};
 const nm=[...document.querySelectorAll('#listView .lvrow.la b.rn .nmx')].filter(n=>n.offsetParent).map(n=>{const g=document.createRange();g.selectNodeContents(n);return g.getBoundingClientRect().left}); const nameL=Math.min(...nm);
 const th=[...C.querySelectorAll('.lact')].filter(e=>e.offsetParent).map(e=>{const i=e.querySelector('img,.lacn').getBoundingClientRect(),b=e.querySelector('.cpt'),q=b.getBoundingClientRect();
   const hit=(x,y)=>{const h=document.elementFromPoint(x,y);return !!h&&e.contains(h)}; /* badge is pointer-events:none: the topmost hit must be its own thumbnail */
   return {t:b.textContent,ring:[i.left-2,i.top-2,i.right+2,i.bottom+2],bd:[q.left,q.top,q.right,q.bottom],vis:b.textContent?[hit(q.left+1,q.top+1),hit(q.right-1,q.top+1),hit(q.left+1,q.bottom-1),hit(q.right-1,q.bottom-1)].every(Boolean):true}});
 return {cl,nameL,th,W:innerWidth}}"""
async def fit(b):
  for W,H,mob in ((390,844,True),(375,667,True),(320,568,True),(1024,768,False)):
    c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=3 if mob else 2,is_mobile=mob,has_touch=True); pg=await c.new_page()
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{ if(document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(700)
    await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=ushouse]'); if(!b.classList.contains('on')) b.click()}"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('#sheet li.la-row').click()"); await pg.wait_for_timeout(5000)
    for m in ('pct','num'):
      await pg.evaluate("m=>window.__setNum(m)",m); await pg.wait_for_timeout(1800)
      f=await pg.evaluate(FIT); th=f['th']; cl=f['cl']; tag=f"thumbs {W}px {m}"
      ck(len(th)>=2 and all(x['t'] for x in th),f"{tag}: {len(th)} thumbnails with badges {[x['t'] for x in th]}",f)
      ck(all(x['ring'][0]>=max(0,cl['l'])-0.01 and x['ring'][1]>=cl['t']-0.01 and x['ring'][2]<=cl['r']+0.01 and x['ring'][3]<=cl['b']+0.01 for x in th),f"{tag}: every photo + its 2px ring inside the visible column (nothing clipped at the screen/list edge)",f)
      ck(all(x['bd'][0]>=max(0,cl['l'])-0.01 and x['bd'][2]<=cl['r']+0.01 and x['bd'][3]<=cl['b']+0.01 and x['vis'] for x in th),f"{tag}: every badge entirely visible (on top, unclipped)",f)
      ck(all(x['bd'][1]>=x['ring'][3]-0.5 for x in th),f"{tag}: badges sit below the photo (not over the face)",f)
      ck(all(a['bd'][3]<=b2['ring'][1]-1 for a,b2 in zip(th,th[1:])),f"{tag}: a badge ends before the next thumbnail",f)
      ck(all(x['bd'][2]<=f['nameL']-2 and x['ring'][2]<=f['nameL']-2 for x in th),f"{tag}: thumbnails and badges clear of the row names (x<{f['nameL']:.0f})",f)
      if W==390 and m=='num': await pg.screenshot(path='/workspace/thumbs-fixed-num.png',clip={'x':0,'y':100,'width':390,'height':230})
    await c.close()
async def fitmain():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await fit(b); await b.close()
asyncio.run(main()); asyncio.run(fitmain()); print("FAILS",len(F)); sys.exit(1 if F else 0)
