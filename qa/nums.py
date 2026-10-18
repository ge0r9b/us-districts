import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    r=await pg.evaluate("""()=>{const E=window.ELECTION2024;const s={};for(const k in E){const st=k.split('|')[0];s[st]=s[st]||[0,0,0];for(let i=0;i<3;i++)s[st][i]+=E[k][i]};return {n:Object.keys(E).length,sample:Object.keys(E).slice(0,3),PA:s.Pennsylvania,GA:s.Georgia,MI:s.Michigan,WI:s.Wisconsin,AZ:s.Arizona,NV:s.Nevada,NC:s['North Carolina'],tot:Object.values(s).reduce((a,v)=>[a[0]+v[0],a[1]+v[1],a[2]+v[2]],[0,0,0]),stTot:typeof __stTot=='function'?__stTot.toString().slice(0,300):String(__stTot).slice(0,300)}}""")
    print(json.dumps(r))
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    for yr in ('2024','2020'):
      for nm in ('num','pct'):
        await pg.evaluate("m=>window.__setNum(m)",nm); await pg.wait_for_timeout(2500)
        rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>r.innerText.replace(/\\n/g,' | ')).filter(t=>/^(PA|GA|MI|WI|AZ|NV|NC|TX|CA|FL|NY|AK)\\b/.test(t))")
        print(yr,nm,json.dumps(rows))
        await pg.screenshot(path=f"../shots/chromium-ipad1024x768-allstates-{yr}-{nm}.png")
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.min;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(3000)
      print('ymode',await pg.evaluate("()=>window.__ymode&&(typeof __ymode=='function'?__ymode():__ymode)"))
    print(log); await c.close(); await b.close()
asyncio.run(main())
