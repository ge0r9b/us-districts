# t241/t242/t244/t245: list view + a district type selected lists districts, never the consolidated total. US House nationwide (435), other types: states list then drill into the state's districts. Map mode unchanged.
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
S="""()=>{const lv=document.getElementById('listView'); const c=document.getElementById('cands'); const vis=e=>e&&e.getBoundingClientRect().width>0&&getComputedStyle(e).display!=='none'; return {la:document.body.classList.contains('listall'),view:window.__v2.view,rows:[...lv.querySelectorAll('.lvrow.la')].filter(r=>r.offsetParent).length,head:(lv.querySelector('.lvhead')||{}).textContent,first:(lv.querySelector('.lvrow.la b.rn')||{}).textContent,lt:(document.querySelector('#lyrRow .lbtn.on')||{dataset:{}}).dataset.k,st:state.value,cons:!!(vis(c)&&/Trump|Harris/.test(c.textContent)&&!document.body.classList.contains('listall')),lay:document.querySelector('#map')&&getComputedStyle(document.getElementById('map')).visibility}}"""
async def run(b,tag,vp,mobile):
  for k,exp,head in (("ushouse",430,"US House"),("senate",50,"states"),("statehouse",50,"states"),("schools",50,"states")):
    c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__v2.setView('list')"); await pg.wait_for_timeout(1500)
    await pg.evaluate("k=>document.querySelector('.lbtn[data-k='+k+']').click()",k); await pg.wait_for_timeout(5000)
    s=await pg.evaluate(S); ck(tag+" %s at US scope in list view: list of %s (not the consolidated total)"%(k,head),s['la'] and s['view']=='list' and s['rows']>=exp and head in (s['head'] or '') and not s['cons'],s)
    if k=="ushouse":
      ck(tag+" ushouse rows are districts (e.g. 'AL-01')",bool(s['first']) and '-' in s['first'],s['first'])
      await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/AL-01/.test(r.textContent)).click()"); await pg.wait_for_timeout(6000)
      s=await pg.evaluate(S); ck(tag+" tap AL-01 -> Alabama's US House list (7 districts)",s['st']=='Alabama' and s['la'] and s['rows']==7,s)
    else:
      await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&/Alabama/.test(b.title||b.textContent)}).click()"); await pg.wait_for_timeout(7000)
      s=await pg.evaluate(S); ck(tag+" tap Alabama -> Alabama's counties (state -> counties -> districts), type %s kept"%k,s['st']=='Alabama' and s['la'] and s['rows']==67 and s['lt']==k,s)
      await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&/Mobile/.test(b.title||b.textContent)}).click()"); await pg.wait_for_timeout(7000)
      s=await pg.evaluate(S); n={"senate":1,"statehouse":1,"schools":3}[k]
      ck(tag+" tap Mobile County -> its %s (>=%d rows), same list view"%(k,n),s['la'] and s['rows']>=n and s['lt']==k and s['view']=='list',s)
    # map mode unchanged: switching to the map leaves no list-all and the map visible
    await pg.evaluate("()=>window.__v2.setView('map')"); await pg.wait_for_timeout(1500); s=await pg.evaluate(S)
    ck(tag+" %s: map mode shows the map (no list overlay)"%k,s['view']=='map' and s['lay']!='hidden',s)
    ck(tag+" %s: no page errors"%k,not errs,errs[:2]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"desktop",{"width":1280,"height":800},False); await run(b,"phone",{"width":390,"height":780},True)
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
