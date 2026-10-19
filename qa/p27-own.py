# pass 20 (build 1588): own touch checks: '16 colours vs official, PA '16 numbers, thumbnail axis in every view, list-all exits to map, district-number labels incl DC
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
from PIL import Image
AX="""()=>{const c=r=>r.left+r.width/2;const im=[...document.querySelectorAll('#cands .cand img, #cands img.dmt, #laCands img')].filter(i=>i.offsetParent&&i.getBoundingClientRect().width>0&&i.getBoundingClientRect().left<innerWidth/2).map(i=>Math.round(c(i.getBoundingClientRect())*10)/10);const ic=document.querySelector('#crumbs .cic');const r=ic&&ic.getBoundingClientRect();return {th:im,ic:r&&r.width?Math.round(c(r)*10)/10:null,listall:document.body.classList.contains('listall'),crumbs:(document.getElementById('crumbs')||{}).innerText,view:window.view||null}}"""
LBL="()=>[...document.querySelectorAll('#cands .cand')].filter(e=>e.offsetParent).map(e=>[e.getAttribute('aria-label')||'',(e.querySelector('.cpt')||e).innerText.replace(/\\n/g,' ').trim()])"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,12).map(r=>{const n=r.querySelector('.nmx');return [n?n.textContent:'',(r.querySelector('b.rn')||{}).title||'',r.innerText.replace(/\\n/g,' ').slice(0,60)]})"
S16={'CA':[36.8,-119.6,'D'],'NY':[42.9,-75.5,'D'],'IL':[40.0,-89.2,'D'],'CO':[39.0,-105.5,'D'],'VA':[37.5,-78.8,'D'],'WA':[47.4,-120.5,'D'],'TX':[31.3,-99.3,'R'],'FL':[28.3,-81.7,'R'],'PA':[40.9,-77.6,'R'],'MI':[43.6,-84.7,'R'],'WI':[44.6,-89.9,'R'],'OH':[40.3,-82.8,'R'],'KS':[38.5,-98.4,'R']}
PA16={'Philadelphia':[39.99,-75.13,'D'],'Allegheny':[40.47,-79.98,'D'],'Lancaster':[40.04,-76.25,'R'],'Westmoreland':[40.31,-79.47,'R'],'Erie':[41.99,-80.04,'R'],'Lackawanna':[41.44,-75.61,'D'],'Clearfield':[41.0,-78.47,'R']}
def side(p): r,g,b=p[:3]; return 'D' if b>r+15 else ('R' if r>b+15 else '?')
async def main():
  eng=sys.argv[1]; which=sys.argv[2:]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      s=tag.replace('iphone','').replace('ipad',''); R=out[tag]={'iss':[],'lat':{},'ax':{}}
      c,pg,log=await ctx(b,W,H,mob,eng); pre=f"../shots/b1604p27-{eng[:2]}-{s}"
      async def tap(sel,name=None,w=1500):
        xy=await center(pg,sel)
        if not xy: R['iss'].append(f'{sel}: not visible'); return False
        l=await tap_latency(pg,*xy)
        if name: R['lat'][name]=l
        await pg.wait_for_timeout(w); return True
      async def ax(n):
        g=await pg.evaluate(AX); R['ax'][n]=g
        if not g['th']: R['iss'].append(f'{n}: no thumbnails visible (listall={g["listall"]})'); await safeshot(pg,f'{pre}-own-{n}-nothumbs.png'); return g
        if g['ic'] is None: R['iss'].append(f'{n}: no row icon'); return g
        off=[round(x-g['ic'],1) for x in g['th']]
        if any(abs(o)>1 for o in off): R['iss'].append(f"{n}: thumbnails off the icon axis by {off} (icon x {g['ic']})"); await safeshot(pg,f'{pre}-own-{n}-axis.png')
        return g
      async def tick(i):
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',None,1000)
        xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(6000)
      async def pix(P,f):
        xy=await pg.evaluate("P=>{const o={};for(const[k,v] of Object.entries(P)){const q=window.__map.latLngToContainerPoint([v[0],v[1]]);o[k]=[Math.round(q.x),Math.round(q.y)]}return o}",P)
        await safeshot(pg,f); im=Image.open(f).convert('RGB'); IW,IH=im.size; o={}
        for k,v in xy.items():
          if 0<=v[0]*2<IW and 0<=v[1]*2<IH: px=im.getpixel((v[0]*2,v[1]*2)); o[k]=[px,side(px),P[k][2]]
        return o
      async def geo(q):
        await typegq(pg,q); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      async def layer(k):
        await tap('#bLyr',None,900); await tap(f'.lbtn[data-k={k}]',f'layer_{k}',4500)
        if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',None,700)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      await ax('US-map-24')
      # A: '16 colours, US and PA
      if tag in ('iphone390','ipad1024x768','ipad1024x576'):
        await tick(0); await pg.evaluate("z=>{window.__map.setView([38.5,-96],z,{animate:false});return 1}",4 if W>600 else 3); await pg.wait_for_timeout(4000)
        R['us16']=await pix(S16,f'{pre}-own-US-2016.png'); R['us16_lbl']=await pg.evaluate(LBL); await ax('US-map-16')
        bad=[k for k,v in R['us16'].items() if v[1]!=v[2]]
        if bad: R['iss'].append(f"US '16 colours wrong in {bad}: {[(k,R['us16'][k]) for k in bad]}")
        await geo('Pennsylvania'); await pg.wait_for_timeout(3000)
        R['pa16']=await pix(PA16,f'{pre}-own-PA-2016.png'); R['pa16_lbl']=await pg.evaluate(LBL); await ax('PA-map-16')
        bad=[k for k,v in R['pa16'].items() if v[1]!=v[2]]
        if bad: R['iss'].append(f"PA '16 colours wrong in {bad}: {[(k,R['pa16'][k]) for k in bad]}")
        await tick(2)
      else:
        await geo('Pennsylvania')
      # B: list-all exit to map at state level (PA US House list > map), plus axis in each view
      await ax('PA-map-24')
      await layer('ushouse'); await ax('PA-ushouse-map')
      await tap('#bGlobe','globe_to_list',4500); await ax('PA-ushouse-list'); R['pa_rows']=await pg.evaluate(ROWS); await safeshot(pg,f'{pre}-own-PA-ushouse-list.png')
      await tap('#bGlobe','globe_to_map',3500); g=await ax('PA-ushouse-map-back')
      if g['listall']: R['iss'].append('PA US House list > map: body.listall still on'); await safeshot(pg,f'{pre}-own-PA-ushouse-backmap-listall.png')
      await safeshot(pg,f'{pre}-own-PA-ushouse-backmap.png')
      await layer('senate'); await tap('#bGlobe','globe_to_list_sen',4500); await ax('PA-senate-list'); R['pa_sen_rows']=await pg.evaluate(ROWS)
      await tap('#bGlobe','globe_to_map_sen',3500); g=await ax('PA-senate-map-back')
      if g['listall']: R['iss'].append('PA state senate list > map: body.listall still on')
      # C: DC US House list label
      await layer('ushouse'); await geo('District of Columbia'); await tap('#bGlobe','dc_list',4500); R['dc_rows']=await pg.evaluate(ROWS); await ax('DC-ushouse-list'); await safeshot(pg,f'{pre}-own-DC-ushouse-list.png')
      if not any(r[0]=='At-large' for r in R['dc_rows']): R['iss'].append(f"DC US House list row not 'At-large': {R['dc_rows'][:3]}")
      await tap('#bGlobe','dc_map',3000); g=await ax('DC-ushouse-map-back')
      if g['listall']: R['iss'].append('DC US House list > map: body.listall still on')
      # D: US list and chart views axis
      await geo('United States'); await tap('#bGlobe','us_list',4000); await ax('US-ushouse-list'); R['us_rows']=await pg.evaluate(ROWS)
      R['build']=await pg.evaluate('window.BUILD'); R['err']=log['pageerr'][:5]+[x for x in log['console'] if x.startswith('error')][:5]
      print(tag,json.dumps({k:R[k] for k in R if k!='ax'})[:3500],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1604p27-own-{eng}-'+'_'.join(which)+'.json','w'),indent=1)
asyncio.run(main())
