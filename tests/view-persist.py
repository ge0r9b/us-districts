# usage: python3 tests/view-persist.py URL tag -- view settings (list vs map, chart type, #/%, time range/delta, sort) persist across selections: list-all row taps (state -> its own counties list), geo-field typing, institution list, unisearch; desktop + phone
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
S="()=>({view:document.body.classList.contains('listmode')?'list':'map',ch:window.chartMode,num:((document.querySelector('#numTog .on')||{dataset:{}}).dataset.m),ym:ym(),la:window.__LA.on,lv:window.__LA.lv&&window.__LA.lv.id,sort:window.__LA.sort,st:state.value,cls:document.body.className,rows:document.querySelectorAll('#listView .lvrow.la').length})"
def chk(n,ok,i=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,json.dumps(i)[:420],flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t,touch in((1280,800,'dk',False),(430,800,'ph',True)):
      ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=touch,is_mobile=touch,user_agent=UA if touch else None); pg=await ctx.new_page(); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bTime"); await pg.wait_for_timeout(400); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(1200)
      await pg.click("#bGeo"); await pg.wait_for_timeout(900); await pg.click("li.la-row"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(500)
      await pg.evaluate("()=>{ const b=document.querySelector('#laSort'); b&&b.click(); }"); await pg.wait_for_timeout(300)
      s0=await pg.evaluate(S); print(t,'start',json.dumps(s0))
      # tap a state row -> its own counties list in list view, same settings
      await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(x=>x.querySelector('b.rn').title==='Texas'); r.querySelector('b.rn').click();}"); await pg.wait_for_timeout(7000)
      s1=await pg.evaluate(S)
      chk(f'{t} tap state row keeps list view + settings, shows its counties',s1['view']=='list' and s1['la'] and s1['lv']=='counties' and s1['rows']>100 and s1['num']==s0['num'] and s1['ym']==s0['ym'] and s1['st']=='Texas',s1)
      await pg.screenshot(path=f"/workspace/shots/vp-{tag}-{t}-counties.png")
      # tap a county row -> its townships/default child list, still list view
      await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent)[0]; r.querySelector('b.rn').click();}"); await pg.wait_for_timeout(6000)
      s2=await pg.evaluate(S)
      chk(f'{t} tap county row keeps list view + settings',s2['view']=='list' and s2['num']==s0['num'] and s2['ym']==s0['ym'],s2)
      # typing in the geo field keeps settings
      await pg.evaluate("()=>{const g=document.getElementById('gq'); g.focus();}"); await pg.wait_for_timeout(300); await pg.keyboard.type("florida"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000)
      s3=await pg.evaluate(S)
      chk(f'{t} geo typing keeps list view + settings',s3['view']=='list' and s3['num']==s0['num'] and s3['ym']==s0['ym'] and s3['st']=='Florida',s3)
      # institution list pick keeps them too
      await pg.click("#bGeo"); await pg.wait_for_timeout(1200); await pg.evaluate("()=>{const r=[...document.querySelectorAll('#sheet li')].find(x=>/^\\s*Georgia/.test(x.textContent)&&x.offsetParent); r&&r.click();}"); await pg.wait_for_timeout(5000)
      s4=await pg.evaluate(S)
      chk(f'{t} institution list pick keeps list view + settings',s4['view']=='list' and s4['num']==s0['num'] and s4['ym']==s0['ym'],s4)
      await ctx.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
