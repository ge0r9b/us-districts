import asyncio,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
    x,y,w=await pg.evaluate("()=>{const t=document.querySelector('.trk').getBoundingClientRect();return [t.left,t.top+t.height/2,t.width]}")
    await pg.touchscreen.tap(x+2,y); await pg.wait_for_timeout(9000)
    print(await pg.evaluate("()=>[Object.keys(DS16),typeof DS16.states, Object.keys(DS16.states||{}).slice(0,3)]"))
    r=await pg.evaluate("()=>({st:JSON.stringify(DS16.states).slice(0,600),pa:ELECTION2016['Pennsylvania|Philadelphia County'],al:ELECTION2016['Pennsylvania|Allegheny County'],keys:Object.keys(DS16.states).length})")
    print(json.dumps(r)[:1500])
    full=await pg.evaluate("()=>DS16.states"); json.dump(full,open('ds16states.json','w'))
    # county sums per state
    cs=await pg.evaluate("()=>{const o={};for(const [k,v] of Object.entries(ELECTION2016)){const s=k.split('|')[0];o[s]=o[s]||[0,0,0,0];for(let i=0;i<Math.min(4,v.length);i++)if(typeof v[i]=='number')o[s][i]+=v[i];o[s][3]++}return o}")
    json.dump(cs,open('e16countysums.json','w')); print('sample',json.dumps(ELECTION2016_sample:=await pg.evaluate("()=>Object.entries(ELECTION2016).slice(0,2)"))[:300])
    await c.close(); await b.close()
asyncio.run(main())
