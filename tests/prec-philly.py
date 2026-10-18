# QA-048/QA-065/QA-050: Philadelphia precinct list in '16>'24: has rows with colours/values, names without the county/city prefix, reload restores the list
import asyncio,sys,re
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>{const n=r.querySelector('.nmx'); return [n?n.textContent:'', n?n.scrollWidth>n.clientWidth+1:false, r.innerText.slice(0,160)]})"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:200]))
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Philadelphia County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{ if(!document.body.classList.contains('listmode')) document.getElementById('bGlobe').click() }"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>{const b=document.querySelector('.lbtn[data-k=precinct],.lbtn[data-k=precincts]'); b&&b.click()}"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); l&&l.click()}"); await pg.wait_for_timeout(8000)
    await pg.evaluate("()=>{ const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/Philadelphia city/.test(r.textContent)); r&&r.click() }"); await pg.wait_for_timeout(9000)
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(9000)
    r=await pg.evaluate(ROWS)
    print(await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.offsetParent); const n=r.querySelector('.nmx'); const o=e=>{const b=e.getBoundingClientRect(); return [e.className,Math.round(b.left),Math.round(b.width),e.scrollWidth,e.clientWidth,getComputedStyle(e).font]}; return [o(r),o(n),...[...r.children].map(o), r.outerHTML.slice(0,700)]}"))
    await pg.screenshot(path='/workspace/w/probe/pp.png')
    ck(len(r)>=20,f"QA-048: Philadelphia precinct list in '16>'24 has rows ({len(r)})")
    ck(r and not any(re.match(r'(?i)philadelphia',x[0]) for x in r[:30]),f"QA-065: names without county/city prefix {[x[0] for x in r[:3]]}")
    ck(r and not any(x[1] for x in r[:30]),f"QA-065: no truncated precinct names {[x[0] for x in r[:30] if x[1]][:3]}")
    ck(r and sum(1 for x in r[:30] if re.search(r'[+\u2212-]\s?\d',x[2]))>=20,f"QA-048: rows carry change values {r[0][2][:80] if r else ''!r}")
    med=await pg.evaluate("""()=>{ const P=window.precItems().filter(r=>/Philadelphia/.test(r[0])&&r[4]); const sw=[]; P.forEach(r=>{ const o=window.__match16(r); if(o&&o[4]) sw.push(((r[3]-r[2])/r[4]-(o[3]-o[2])/o[4])*100); }); sw.sort((a,b)=>a-b); return [sw.length,P.length,sw[sw.length>>1]] }""")
    ck(med[0]>=med[1]*0.98 and 2<=med[2]<=14,f"QA-048: 2016 twins sane (matched {med[0]}/{med[1]}, median swing R+{med[2]:.1f}; real Philly ~R+8)")
    await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(14000)
    r2=await pg.evaluate(ROWS); y=await pg.evaluate("()=>[!!window.__y16, window.__y16hi]")
    ck(len(r2)>=20 and y==[True,2],f"QA-050: reload restores the '16>'24 precinct list ({len(r2)} rows, {y})")
    ck(not er,f"no page errors {er[:2]}")
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
