import asyncio,sys,json,time
from playwright.async_api import async_playwright
B="""()=>{ const T=(f,n)=>{ const a=[]; for(let i=0;i<n;i++){ document.body.offsetHeight; const t=performance.now(); f(); document.body.offsetHeight; a.push(performance.now()-t); } a.sort((x,y)=>x-y); return +a[a.length>>1].toFixed(2); };
 const o={}; try{ o.renderCands=T(()=>renderCands(),15); }catch(e){ o.rcErr=String(e).slice(0,80); } try{ o.crumbs=T(()=>crumbs(),15); }catch(e){ o.crErr=String(e).slice(0,80); } try{ o.layoutSide=T(()=>layoutSide(),15); }catch(e){} try{ o.renderList=T(()=>renderList(),5); }catch(e){ o.rlErr=String(e).slice(0,80);} return o; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for v in sys.argv[1].split(','):
      c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page()
      await pg.goto(f"http://127.0.0.1:8857/{v}/v2/?v=%d"%(time.time()*1000),wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3000)
      r1=await pg.evaluate(B)
      await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'}).click()"); await pg.wait_for_timeout(6000)
      r2=await pg.evaluate(B)
      print(v,'AllStates',r1,'PA',r2,flush=True); await c.close()
    await b.close()
asyncio.run(main())
