# Build 1549: list-view back chevron and sort glyph always sit inside the list band (below the time row, above the first row),
# time row open/closed, with a topic (chart button present) and with no topic (plain entity list, no chart button);
# with no topic the sort glyph is hidden (nothing to sort by). Phone 390x844.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; tag=sys.argv[2] if len(sys.argv)>2 else "x"
M="""()=>{const R=e=>{if(!e)return null;const r=e.getBoundingClientRect();return r.height>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'?r:null};
 const lv=document.getElementById('listView').getBoundingClientRect(); const bt=R(document.getElementById('barTime')); const so=R(document.querySelector('#laSort svg'))&&R(document.getElementById('laSort'))?document.querySelector('#laSort svg').getBoundingClientRect():null;
 const bb=R(document.getElementById('bBack')); const sv=bb?document.querySelector('#bBack svg').getBoundingClientRect():null;
 const fr=[...document.querySelectorAll('#listView .lvrow.la')].map(x=>x.getBoundingClientRect()).find(q=>q.height>0&&q.top>=lv.top-1);
 const exp=document.getElementById('bTime').classList.contains('on'); const tb=document.getElementById('barTime');
 const tbot=exp&&bt?bt.bottom:null;
 return {exp,notopic:document.body.classList.contains('notopic'),chart:!!R(document.querySelector('button.rbtn.cmain')),lvTop:lv.top,timeBottom:tbot,row1:fr?fr.top:null,chev:sv?[sv.top,sv.bottom]:null,sort:so?[so.top,so.bottom]:null,rows:document.querySelectorAll('#listView .lvrow.la').length}}"""
async def main():
  bad=[]
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=3); await c.add_init_script("try{localStorage.clear()}catch(e){}"); pg=await c.new_page()
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_function("()=>!!document.getElementById('bGeo')",timeout=60000); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=20000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&/Wisconsin/.test(b.title||b.textContent)}).click()"); await pg.wait_for_timeout(7000)
    for topic in (True,False):
      if not topic: await pg.evaluate("()=>window.__setTopic(null)"); await pg.wait_for_timeout(2500)
      for exp in (False,True):
        cur=await pg.evaluate("()=>document.getElementById('bTime').classList.contains('on')")
        if cur!=exp: await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
        d=await pg.evaluate(M); nm=f"{'topic' if topic else 'notopic'}-{'open' if exp else 'closed'}"
        await pg.screenshot(path=f"/workspace/band-{nm}.png")
        top=max(d['lvTop'],d['timeBottom'] or 0); low=d['row1'] if d['row1'] is not None else d['lvTop']+60
        ok=d['chev'] is not None and d['chev'][0]>=top+1 and d['chev'][1]<=low-1
        if topic: ok=ok and d['sort'] is not None and d['sort'][0]>=top+1 and d['sort'][1]<=low-1 and abs((d['sort'][0]+d['sort'][1])/2-(d['chev'][0]+d['chev'][1])/2)<=1.5
        else: ok=ok and d['sort'] is None and d['notopic']
        print(nm,'OK' if ok else 'FAIL',json.dumps({k:(round(v,1) if isinstance(v,float) else v) for k,v in d.items()}),flush=True)
        if not ok: bad.append(nm)
      ph=await pg.evaluate("()=>{const v=document.getElementById('vtitle'); const a=getComputedStyle(v,'::after'); return {txt:v.textContent,after:a.content,col:a.color}}")
      okp=(ph['after']=='"Topic"' and ph['txt']=='' and ph['col']!='rgb(0, 0, 0)') if not topic else (ph['after'] in ('none','normal') and ph['txt']!='')
      print('title placeholder',topic,'OK' if okp else 'FAIL',ph)
      if not okp: bad.append('placeholder '+str(topic))
      if not topic:
        await pg.screenshot(path="/workspace/band-topic-placeholder.png",clip={'x':0,'y':0,'width':390,'height':200})
        await pg.evaluate("()=>document.getElementById('vtitle').click()"); await pg.wait_for_timeout(600)
        v=await pg.evaluate("()=>{const i=document.getElementById('topin')||document.getElementById('usq'); return i&&i.offsetParent?[i.value,i.id]:null}")
        okt=v is not None and v[0]=='' ; print('tap -> blank input','OK' if okt else 'FAIL',v)
        if not okt: bad.append('tap input')
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
    await b.close()
  print('FAILS',len(bad),bad); sys.exit(1 if bad else 0)
asyncio.run(main())
