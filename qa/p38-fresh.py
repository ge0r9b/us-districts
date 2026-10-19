# pass 38 (build 1616): institution search + filters, % vs # charts (pie/bar/line) vs list and __stTot, reload restore (list/map/chart/range)
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p35-states.py').read().split('async def main')[0].split('from gaps import typegq')[1])
CH="()=>{const b=document.getElementById('chartBox');return b?b.innerText.replace(/\\n/g,' | ').slice(0,400):null}"
SHEET="()=>[...document.querySelectorAll('#sheet li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').trim().slice(0,50)).slice(0,10)"
INP="()=>{const i=[...document.querySelectorAll('input')].filter(e=>e.offsetParent&&e.id!=='gq'&&e.id!=='yslider');return i.map(e=>{const r=e.getBoundingClientRect();return [e.id||e.className,e.placeholder,Math.round(r.left+r.width/2),Math.round(r.top+r.height/2)]})}"
MP="()=>{const m=window.__map;return m?[m.getZoom(),+m.getCenter().lat.toFixed(3),+m.getCenter().lng.toFixed(3)]:null}"
VISTXT="(t)=>{const L=[...document.querySelectorAll('li,.lvrow,button')].filter(e=>e.offsetParent&&e.innerText);const nm=e=>e.innerText.trim().split('\\n').map(x=>x.replace('›','').trim()).filter(x=>x.length>1)[0]||'';let e=L.filter(e=>nm(e)===t);if(!e.length)e=L.filter(e=>nm(e).startsWith(t));if(!e.length)return null;const r=e[e.length-1];r.scrollIntoView({block:'nearest'});const n=r.querySelector('.nmx')||r;const b=n.getBoundingClientRect();return [b.left+b.width/2,b.top+b.height/2]}"
SNAP="()=>JSON.stringify(window.__stateSnapshot())"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; parts=sys.argv[3].split(','); out={'parts':parts}
  pre=f"shots38/b1616p38-{eng[:2]}-{W}x{H}"
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    async def newpage():
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD"); return c,pg,log
    def mk(pg):
      async def tap(sel,wait=0):
        xy=await center(pg,sel)
        if not xy: return None
        v=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return v
      return tap
    async def setnum(pg,tap,want):
      if (await pg.evaluate("()=>window.__numMode()"))==want: return 'already'
      l=await tap('#bNum',1200)
      opt=await pg.evaluate("w=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()===(w==='num'?'#':'%')&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",want)
      if opt: await tap_latency(pg,*opt); await pg.wait_for_timeout(1800)
      if (await pg.evaluate("()=>window.__numMode()"))!=want: await pg.evaluate("w=>window.__setNum(w)",want); await pg.wait_for_timeout(1500)
      return [l,await pg.evaluate("()=>window.__numMode()")]
    async def state(pg,tap,st):
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5500)
    async def grab(pg):
      return {'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'ch':await pg.evaluate(CH),'rows':(await pg.evaluate(ROWS))[:4],'n':await pg.evaluate(NROWS),'mp':await pg.evaluate(MP),'layout':await pg.evaluate(LAYOUT)}
    if 'inst' in parts:
      I=out['inst']={}
      c,pg,log=await newpage(); tap=mk(pg)
      await tap('#bGeo',1300); I['inputs0']=await pg.evaluate(INP); I['sheet0']=await pg.evaluate(SHEET)
      # filters at US level: each institution type
      for nm in ['US House districts','State senate districts','State house districts','School districts']:
        if not await pg.evaluate("()=>!document.getElementById('sheet').hidden"): await tap('#bGeo',1300)
        xy=await pg.evaluate(VISTXT,nm)
        if not xy: I[nm]='no row'; continue
        l=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
        G=I[nm]=await grab(pg); G['lat']=l
        G['num']=await setnum(pg,tap,'num'); G['th_num']=await pg.evaluate(TH); G['hdr_num']=await pg.evaluate(HDR); G['rows_num']=(await pg.evaluate(ROWS))[:3]
        await safeshot(pg,f"{pre}-inst-{nm.split()[0]}{nm.split()[1]}.png"); await setnum(pg,tap,'pct')
        print('inst',nm,json.dumps({k:v for k,v in G.items() if k!='layout'})[:1200],'LAYOUT',G['layout'],flush=True)
      await c.close()
      # institution search field
      for q,enter in [('Georgia',True),('Fulton',False),('Mecklenburg',True),('Franklin County, OH',True),('Wayne',False),('ohio',True),('zzqx',False)]:
        c,pg,log=await newpage(); tap=mk(pg); S=I['q:'+q]={}
        await tap('#bGeo',1300); inp=await pg.evaluate(INP); S['inputs']=inp
        if not inp:
          await tap('#crumbs .crumb.cur',1000); inp=await pg.evaluate(INP); S['inputs2']=inp
        if inp: await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500)
        else:
          loc=pg.locator('#barGeo input').first
          try: await loc.focus()
          except Exception as e: S['focuserr']=str(e)[:80]
        await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1500)
        S['rows']=await pg.evaluate(SHEET); await safeshot(pg,f"{pre}-inst-q-{q.replace(' ','').replace(',','')}.png")
        if enter:
          await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5500); S['after']=await grab(pg)
          S['tot']=await pg.evaluate("n=>{try{return window.__stTot(n,'2024')}catch(e){return null}}",q.title() if len(q)>3 else q)
          S['num']=await setnum(pg,tap,'num'); S['th_num']=await pg.evaluate(TH)
          await safeshot(pg,f"{pre}-inst-q-{q.replace(' ','').replace(',','')}-enter.png")
        S['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
        print('instq',q,json.dumps({k:(v if k!='after' else {kk:vv for kk,vv in v.items() if kk!='layout'}) for k,v in S.items()})[:1500],flush=True); await c.close()
    if 'charts' in parts:
      C=out['charts']={}
      for st in sys.argv[4].split(',') if len(sys.argv)>4 else ['Georgia','North Carolina']:
        c,pg,log=await newpage(); tap=mk(pg); await state(pg,tap,st); R=C[st]={}
        R['tot']=await pg.evaluate("n=>{const o={};for(const y of ['2016','2020','2024'])o[y]=window.__stTot(n,y);return o}",st)
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
        for yl,js in [('24','window.__ySetYr(2)'),('20','window.__ySetYr(1)'),('16','window.__ySetYr(0)'),('16-24','window.__ySet16(2)'),('20-24','window.__ySelectAll()'),('16-20','window.__ySet16(1)')]:
          await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(2500)
          await tap('#chartBox .cmain',900); opts=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)")
          for ch in opts:
            for mode in ['pct','num']:
              await setnum(pg,tap,mode)
              if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',900)
              l=await tap(f'#chartBox .copts button[data-ch={ch}]',2200)
              k=f'{yl}-{ch}-{mode}'; R[k]={'lat':l,'mode':await pg.evaluate("()=>window.chartMode"),'ch':await pg.evaluate(CH),'th':await pg.evaluate(TH),'ysl':await pg.evaluate("()=>window.__ysl.get()"),'layout':await pg.evaluate(LAYOUT)}
              await safeshot(pg,f'{pre}-chart-{st.replace(" ","")}-{k}.png')
              print('chart',st,k,json.dumps({x:y for x,y in R[k].items() if x!='layout'})[:900],R[k]['layout'],flush=True)
        # list: All States row for this state at '24, % and #
        await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(1500)
        if await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',600)
        await tap('#bGeo',1300); await tap('li.la-row',5000)
        for mode in ['pct','num']:
          await setnum(pg,tap,mode); rr=await pg.evaluate(ROWS); ab={'Georgia':'GA','North Carolina':'NC','Ohio':'OH','Michigan':'MI','Arizona':'AZ'}.get(st,st)
          R['listrow-'+mode]=[r for r in rr if r.startswith(ab+' ') or r.startswith(ab+' |') or r.startswith(st)][:2]
          if not R['listrow-'+mode]:
            await pg.evaluate("a=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.textContent.trim()===a);if(e)e.scrollIntoView({block:'center'})}",ab); await pg.wait_for_timeout(800)
            rr=await pg.evaluate(ROWS); R['listrow-'+mode]=[r for r in rr if r.split(' |')[0].strip() in (ab,st)][:2]
        print('chart',st,'list',R['listrow-pct'],R['listrow-num'],'tot',R['tot'],flush=True)
        R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]; await c.close()
    if 'reload' in parts:
      RL=out['reload']={}
      async def rel(pg,k):
        await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); a=await grab(pg); s1=await pg.evaluate(SNAP); await safeshot(pg,f'{pre}-reload-{k}-before.png')
        await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7500)
        z=await grab(pg); s2=await pg.evaluate(SNAP); await safeshot(pg,f'{pre}-reload-{k}-after.png')
        same={x:a[x]==z[x] for x in ['hdr','th','ch','rows','n']}
        RL[k]={'before':{x:a[x] for x in a if x!='layout'},'after':{x:z[x] for x in z if x!='layout'},'snap':[s1,s2],'same':same,'layout_after':z['layout']}
        print('reload',k,same,json.dumps(RL[k]['before'])[:600],'||',json.dumps(RL[k]['after'])[:600],flush=True)
      # list: Georgia counties list
      c,pg,log=await newpage(); tap=mk(pg); await state(pg,tap,'Georgia'); await tap('#bGeo',1300); await tap('li.la-row',5000)
      await rel(pg,'list-GAcounties'); await c.close()
      # map: Fulton County map (drill then globe)
      c,pg,log=await newpage(); tap=mk(pg); await state(pg,tap,'Georgia'); await tap('#bGeo',1300); await tap('li.la-row',5000)
      xy=await pg.evaluate(NMXY,'Fulton'); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,'Fulton')
      if xy: await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
      await tap('#bGlobe',5000); await rel(pg,'map-Fulton'); await c.close()
      # chart: Ohio pie in # mode at 2020
      c,pg,log=await newpage(); tap=mk(pg); await state(pg,tap,'Ohio')
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
      await pg.evaluate("()=>window.__ySetYr(1)"); await pg.wait_for_timeout(2000); await setnum(pg,tap,'num')
      await tap('#chartBox .cmain',900); await tap('#chartBox .copts button[data-ch=pie]',2500); await rel(pg,'chart-OHpie20num'); await c.close()
      # range: NC counties list '16>'24 line
      c,pg,log=await newpage(); tap=mk(pg); await state(pg,tap,'North Carolina'); await tap('#bGeo',1300); await tap('li.la-row',5000)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
      await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(2500); await tap('#chartBox .cmain',900); await tap('#chartBox .copts button[data-ch=line]',2500)
      await rel(pg,'range-NC1624line'); RL['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]; await c.close()
    await b.close()
  json.dump(out,open(f"b1616p38-fresh-{eng}-{W}x{H}-{'_'.join(parts)}.json",'w'),indent=1)
asyncio.run(main())
