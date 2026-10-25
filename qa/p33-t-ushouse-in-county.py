# QA-005 (build 1596) + touch-adjust fix: a tap on a row name next to the thumbnail column drills in (Chromium touch adjustment used to retarget it to the thumbnail, toggling the candidate); a tap on the thumbnail itself still toggles it.
# QA-005 (build 1596): list view inside a county (townships list) > district type US House lists the county's US House districts (like school / state house / state senate do), never an empty list with the county's total under the state's name. Deselecting the type returns to the county's townships list.
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
FIND="""n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn,.nmx');return b&&(b.textContent.trim()===n||(b.title||'').startsWith(n)||b.textContent.trim().startsWith(n))});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.querySelector('b.rn,.nmx').getBoundingClientRect();return [q.left+5,q.top+q.height/2]}"""
S="""()=>{const i=window.__laInfo(); return {on:i.on,lv:i.lv,order:i.order.map(o=>o[0]),st:state.value,cn:county.value,lt:(document.querySelector('#lyrRow .lbtn.on')||{dataset:{}}).dataset.k,rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).length}}"""
async def run(b,eng,cty,exp):
  c=await b.new_context(viewport={'width':390,'height':844},is_mobile=eng=='chromium',has_touch=True); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until='networkidle'); await pg.wait_for_timeout(3000)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
  for n in ('PA',cty):
    if n==cty:
      A="()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.getAttribute('aria-pressed')).join(',')"
      a0=await pg.evaluate(A); xy=await pg.evaluate("()=>{const r=document.querySelector('#laCands .lact').getBoundingClientRect();return [r.left+r.width/2,r.top+18]}")
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(800); a1=await pg.evaluate(A)
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(800); a2=await pg.evaluate(A)
      ck(eng+" thumbnail tap still toggles the candidate (and back)",a1!=a0 and a2==a0,(a0,a1,a2))
    xy=await pg.evaluate(FIND,n)
    if not xy: ck(eng+" find row "+n,False); await c.close(); return
    await pg.wait_for_timeout(700); xy=await pg.evaluate(FIND,n); await pg.wait_for_timeout(200); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(4500)
  s0=await pg.evaluate(S); ck(eng+" "+cty+": townships list",s0['on'] and s0['lv']=='townships' and s0['rows']>=1,s0)
  await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(900)
  await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(4500)
  s=await pg.evaluate(S)
  ck(eng+" "+cty+" > US House: list of the county's US House districts %s"%exp,s['on'] and s['lv']=='districts' and s['lt']=='ushouse' and s['cn']==cty+' County' and s['st']=='Pennsylvania' and sorted(s['order'])==sorted(exp) and s['rows']==len(exp),s)
  await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(4500)
  s=await pg.evaluate(S); ck(eng+" "+cty+": deselect US House -> townships list again",s['on'] and s['lv']=='townships' and s['cn']==cty+' County' and s['rows']==s0['rows'],s)
  ck(eng+" no page errors",not errs,errs[:2]); await c.close()
async def main():
  async with async_playwright() as p:
    for eng in ('chromium','webkit'):
      b=await getattr(p,eng).launch()
      await run(b,eng,'Philadelphia',['District 02','District 03','District 05'])
      await run(b,eng,'Allegheny',['District 12','District 17'])
      await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
