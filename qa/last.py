import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import fresh,typegq,ST,LI
async def main():
  o={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    c,pg,log=await fresh(b); o['build']=await pg.evaluate("()=>BUILD")
    o['cumb']=await pg.evaluate("()=>ELECTION2024['Pennsylvania|Cumberland County']")
    await typegq(pg,"1600 Pennsylvania Ave NW, Washington, DC 20500"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
    o['wh_enter']=await pg.evaluate(ST); await pg.screenshot(path="../shots/b1568-ch-390-addr-wh-enter.png"); await c.close()
    for k,lab in (('senate','State senate districts'),('school','School districts')):
      c,pg,log=await fresh(b)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("l=>[...document.querySelectorAll('li')].find(e=>e.offsetParent&&e.innerText.includes(l)).click()",lab); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      o[k+'_menu']=await pg.evaluate(LI)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
      R=[]
      for name in ('PA',None,None):
        info=await pg.evaluate("()=>[window.__laInfo().lv,[...document.querySelectorAll('#listView .lvrow.la')].length,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))]"); R.append(info)
        xy=await pg.evaluate("n=>{const rs=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent);const r=n?rs.find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n}):rs[0];if(!r)return null;r.scrollIntoView({block:'center'});const q=(r.querySelector('.nmx')||r).getBoundingClientRect();return [q.left+q.width/2,q.top+q.height/2]}",name)
        if not xy: break
        await pg.wait_for_timeout(300); lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000); R.append(('lat',lat))
      R.append(await pg.evaluate("()=>[window.__laInfo().lv,[...document.querySelectorAll('#listView .lvrow.la')].length,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | ')),state.value,county.value]"))
      await pg.screenshot(path=f"../shots/b1568-ch-390-{k}-list.png"); o[k]=R; o[k+'_err']=log['pageerr']; await c.close()
    await b.close()
  print(json.dumps(o,indent=0)[:4000])
asyncio.run(main())
