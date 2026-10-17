# Build 1546: list charts (bar/pie/line/change bars) use the left-edge candidate column (no per-row photos), ranked for the
# current selection, tap toggles a candidate (segment/slice/line hidden when off); a candidate without a photo shows a rank badge;
# sort: % mode = share of the selected candidate(s) (leader's share when all on), # mode = raw votes, change mode = |net change| as displayed.
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
    lead=[max(x['w']['rep'],x['w']['dem']) for x in r]; ck(mono(lead),"% mode, all candidates on: rows sorted by the leader's share",lead[:8])
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); r=await pg.evaluate(ROWS)
    bw=[x['bw'] for x in r]; ck(mono(bw,tol=1.01) and r[0]['n']=='CA',"# mode: rows sorted by raw votes (bar lengths on one scale, CA first)",[x['n'] for x in r[:4]]+bw[:4])
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
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
