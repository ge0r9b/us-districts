# usage: python3 tests/state-persist.py URL tag -- state persistence: reload restores topic/geo/time range/chart/list-vs-map/#-%/layer from the URL hash (versioned snapshot v:1), localStorage fallback with no hash, invalid values fall back safely (no errors)
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
S="()=>({st:state.value,co:county.value,lt:window.__stateSnapshot().lt,yv:+document.getElementById('yslider').value,tb:!document.getElementById('barTime').hidden,ch:window.chartMode,nm:window.__numMode(),list:document.body.classList.contains('listmode'),ph:document.getElementById('gq').placeholder,snap:window.__stateSnapshot&&window.__stateSnapshot()})"
def chk(n,ok,i=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,json.dumps(i)[:380],flush=True)
async def chart(pg,k):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch===k); x&&x.click();}",k); await pg.wait_for_timeout(2000)
async def typ(pg,q):
  await pg.evaluate("()=>{const g=document.getElementById('gq'); g.focus();}"); await pg.wait_for_timeout(400); await pg.keyboard.type(q); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t,touch in((1280,800,'dk',False),(430,800,'ph',True)):
      ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=touch,is_mobile=touch,user_agent=UA if touch else None); pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)[:120]))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      # 1 Florida + list view + pie chart (build 1557: a single entity has no bar chart; it restores as pie)
      await typ(pg,"florida"); await chart(pg,"pie"); await pg.wait_for_timeout(2500)
      s0=await pg.evaluate(S); h=await pg.evaluate("()=>location.hash")
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000); s1=await pg.evaluate(S)
      chk(f'{t} reload restores Florida + list view + pie chart',s0['st']=='Florida' and h.startswith('#s=') and s1['st']=='Florida' and s1['list'] and s1['ch']=='pie' and 'Florida' in s1['ph'],[s0,s1,h[:40]])
      await pg.screenshot(path=f"/workspace/shots/sp-{tag}-{t}-florida.png")
      await pg.wait_for_timeout(4000); s1b=await pg.evaluate(S); chk(f'{t} stays Florida after restore (no stale clear)',s1b['st']=='Florida',s1b)
      # 2 localStorage fallback: no hash
      await pg.goto(base.split('#')[0],wait_until="networkidle"); await pg.wait_for_timeout(9000); s2=await pg.evaluate(S)
      chk(f'{t} localStorage fallback restores with no hash',s2['st']=='Florida' and s2['ch']=='pie',s2)
      # 2b plural list: 'Florida counties' + bar chart restores as the bar list
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1600); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
      await pg.evaluate("()=>{ if(window.chartMode!=='bar'){ const c=document.querySelector('[aria-label=Chart]'); c.click(); setTimeout(()=>{ const x=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch==='bar'); if(x) x.click(); else if(c.dataset.ch==='bar') c.click(); },500); } }"); await pg.wait_for_timeout(2500)
      s0=await pg.evaluate("()=>[window.__laInfo().on, window.__laInfo().lv, window.chartMode]")
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(10000); s1=await pg.evaluate("()=>[window.__laInfo().on, window.__laInfo().lv, window.chartMode, state.value]")
      chk(f'{t} reload restores the plural Florida counties list with the bar chart',s0==[True,'counties','bar'] and s1==[True,'counties','bar','Florida'],[s0,s1])
      await ctx.close()
      # 3 delta line chart
      ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=touch,is_mobile=touch,user_agent=UA if touch else None); pg=await ctx.new_page(); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.click("#bTime"); await pg.wait_for_timeout(500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(1500); await chart(pg,"line"); await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
      s0=await pg.evaluate(S); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000); s1=await pg.evaluate(S)
      chk(f'{t} reload restores delta line chart (# mode, time filter open)',s1['yv']==1 and s1['tb'] and s1['ch']=='line' and s1['nm']=='num' and s1['list'],[s0,s1]); await pg.screenshot(path=f"/workspace/shots/sp-{tag}-{t}-line.png")
      await ctx.close()
      # 4 district layer + Texas
      ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=touch,is_mobile=touch,user_agent=UA if touch else None); pg=await ctx.new_page(); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await typ(pg,"texas"); await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=senate]'); b&&b.click();}"); await pg.wait_for_timeout(3000)
      s0=await pg.evaluate(S); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000); s1=await pg.evaluate(S)
      chk(f'{t} reload restores Texas + state senate layer',s0['lt']=='senate' and s1['lt']=='senate' and s1['st']=='Texas',[s0['lt'],s1]); await pg.screenshot(path=f"/workspace/shots/sp-{tag}-{t}-senate.png")
      await ctx.close()
      # 5 invalid / unknown values and garbage hash
      for hsh in ("#s=garbage!!","#s="+"eyJ2Ijo5OSwic3QiOiJOYXJuaWEiLCJjaCI6Inp6eiIsInl2Ijo5LCJ6enoiOjF9"):
        ctx=await b.new_context(viewport={"width":W,"height":H}); pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)[:120]))
        await pg.goto(base.split('#')[0]+hsh,wait_until="networkidle"); await pg.wait_for_timeout(8000); s=await pg.evaluate(S)
        chk(f'{t} invalid state falls back safely ({hsh[:12]})',s['st']==''and s['ch'] in (None,'') and not errs,[s['st'],s['ch'],errs]); await ctx.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
