# usage: python3 tests/list-all-clean.py URL tag -- 'List all states': field says 'All States' (flag kept), no total block / Republican-Democratic-Other text labels, 51 rows visible and scrollable in every mode, party bubble on press; phone + desktop
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
M="""()=>{const lv=document.getElementById('listView'); const lr=lv.getBoundingClientRect(); const rows=[...lv.querySelectorAll('.lvrow.la')]; const vis=rows.filter(r=>{const b=r.getBoundingClientRect(); return b.height>0&&b.bottom>lr.top&&b.top<lr.bottom&&b.left>=0&&b.right<=innerWidth+1});
 const cur=document.querySelector('#crumbs .crumb.cur'); const cb=document.getElementById('cands');
 return {n:rows.length,vis:vis.length,lvH:Math.round(lr.height),lvTop:Math.round(lr.top),field:cur&&cur.textContent,flag:!!document.querySelector('#crumbs .cic img'),cands:getComputedStyle(cb).display,labels:/Republican|Democratic|Other/.test(lv.innerText)||/Republican|Democratic/.test(document.body.innerText.replace(/[\\s\\S]*?(?=\\n)/,'')) && !!lv.querySelector('.cbl'),scrollH:lv.scrollHeight,first:rows[0]&&rows[0].querySelector('b.rn').textContent}}"""
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((430,640,'ph'),(1280,800,'dk')):
      for mode in ['map','bar','line','pie']:
        pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
        if mode!='map':
          await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
          await pg.evaluate("(m)=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch===m); x&&x.click();}",mode); await pg.wait_for_timeout(800)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
        r=await pg.evaluate(M)
        ok=r['n']==51 and r['vis']>=(8 if mode!='line' else 5) and r['field']=='All States' and r['flag'] and r['cands']=='none' and not r['labels'] and r['lvH']>150 and r['scrollH']>r['lvH']
        fails+=0 if ok else 1; print(t,mode,'OK' if ok else 'FAIL',json.dumps(r),flush=True)
        await pg.screenshot(path=f"/workspace/shots/lac-{tag}-{t}-{mode}.png")
        if mode=='bar':
          await pg.evaluate("()=>document.querySelector('#listView .sg.rep').click()"); await pg.wait_for_timeout(300)
          bt=await pg.evaluate("()=>{const e=document.getElementById('partyBub');return e&&e.textContent}"); ok=bool(bt) and bt.startswith('Republican') and ('%' in bt or any(ch.isdigit() for ch in bt)); fails+=0 if ok else 1; print(t,'party bubble','OK' if ok else 'FAIL',bt)
          await pg.screenshot(path=f"/workspace/shots/lac-{tag}-{t}-bubble.png")
          await pg.evaluate("()=>{document.getElementById('listView').scrollTop=1500}"); await pg.wait_for_timeout(500); await pg.screenshot(path=f"/workspace/shots/lac-{tag}-{t}-scroll1.png")
          await pg.evaluate("()=>{document.getElementById('listView').scrollTop=99999}"); await pg.wait_for_timeout(500); await pg.screenshot(path=f"/workspace/shots/lac-{tag}-{t}-scrollend.png")
        await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
