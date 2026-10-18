# pass 18 (build 1585): new chart layout: bars on thumbnail rows, pie box, Other chip, name bubble, range bars on icon rows, list without pie, split bar
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
GEOM="""()=>{const vr=e=>{if(!e)return null;const r=e.getBoundingClientRect();return r.width>0&&r.height>0?[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]:null};
 const ims=[...document.querySelectorAll('#cands .cand img')].map(i=>({p:i.closest('.cand').classList.contains('r')?'rep':'dem',r:vr(i)})).filter(x=>x.r);
 const bars=[...document.querySelectorAll('#cands .sebr')].map(b=>{const i=b.querySelector('.sebt i');const t=[...b.querySelectorAll('*')].filter(e=>e.childElementCount===0&&e.textContent.trim()).map(e=>({t:e.textContent.trim(),r:vr(e)}));return {k:b.dataset.k,v:+b.dataset.v,row:vr(b),bar:vr(i),txt:t,chip:vr(b.querySelector('.sechip')),chipbg:b.querySelector('.sechip')&&getComputedStyle(b.querySelector('.sechip')).backgroundColor}});
 const rng=[...document.querySelectorAll('#cands .dmx .dmr')].map(r=>({k:r.dataset.k,row:vr(r),bar:vr(r.querySelector('.dmb')),icon:vr(r.querySelector('.dmt')),txt:r.innerText.replace(/\\n/g,' ')}));
 const btn=[...document.querySelectorAll('button.rbtn')].map(vr).filter(r=>r&&r[0]>innerWidth*0.5);
 const pie=vr(document.querySelector('#cands .cpie1 svg'));const bb=vr(document.getElementById('barBottom'));const ysl=vr(document.getElementById('ysl'));
 return {chv:document.body.classList.contains('chv'),ims,bars,rng,btn,pie,bb,ysl,mode:window.chartMode,opts:[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)}}"""
def ov(a,b,m=1): return a and b and min(a[2],b[2])-max(a[0],b[0])>m and min(a[3],b[3])-max(a[1],b[1])>m
def check(g,W,H,tag):
  iss=[]
  ims=sorted(g['ims'],key=lambda x:x['r'][1])
  for b in g['bars']:
    m=[i for i in ims if i['p']==b['k']]
    if m and b['bar']:
      cy=(m[0]['r'][1]+m[0]['r'][3])/2; by=(b['bar'][1]+b['bar'][3])/2
      if abs(cy-by)>3: iss.append(f"{tag}: {b['k']} bar centre y {by} vs thumbnail centre {cy}")
      if abs(b['bar'][0]-(m[0]['r'][2]+6))>2: iss.append(f"{tag}: {b['k']} bar starts x {b['bar'][0]}, icon right {m[0]['r'][2]} (+6 expected)")
    if b['bar'] and b['bar'][2]>W+1: iss.append(f"{tag}: {b['k']} bar runs off screen to {b['bar'][2]}")
    for t in b['txt']:
      if t['r'] and t['r'][2]>W+1: iss.append(f"{tag}: label {t['t']} off screen {t['r']}")
      for q in g['btn']:
        if ov(t['r'],q,2): iss.append(f"{tag}: label '{t['t']}' {t['r']} under button {q}")
  if g['bars']:
    o=[b for b in g['bars'] if b['k']=='oth']
    if not o: iss.append(f"{tag}: no Other bar")
    elif not o[0]['chip']: iss.append(f"{tag}: Other bar has no chip")
  if g['pie']:
    p=g['pie']; L=max([i['r'][2] for i in ims] or [0]); R=min([q[0] for q in g['btn'] if q[3]>p[1] and q[1]<p[3]] or [W])
    if p[0]<L: iss.append(f"{tag}: pie left {p[0]} overlaps thumbnails (right {L})")
    if p[2]>R: iss.append(f"{tag}: pie right {p[2]} overlaps buttons (left {R})")
    if g['bb'] and p[3]>g['bb'][1]: iss.append(f"{tag}: pie bottom {p[3]} below bottom field top {g['bb'][1]}")
    if p[3]>H: iss.append(f"{tag}: pie bottom {p[3]} off screen")
    if p[2]-p[0]<80: iss.append(f"{tag}: pie only {p[2]-p[0]} px")
  for r in g['rng']:
    if r['bar'] and r['bar'][2]>W+1: iss.append(f"{tag}: range {r['k']} bar off screen {r['bar']}")
    if r['bar'] and r['icon'] and abs((r['bar'][1]+r['bar'][3])/2-(r['icon'][1]+r['icon'][3])/2)>3: iss.append(f"{tag}: range {r['k']} bar not on icon row {r['bar']} vs {r['icon']}")
  return iss
async def main():
  eng=sys.argv[1]; which=sys.argv[2:]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      s=tag.replace('iphone','').replace('ipad','')
      c,pg,log=await ctx(b,W,H,mob,eng); R=out[tag]={'iss':[],'lat':{}}
      async def shot(n): await safeshot(pg,f"../shots/b1585p18-{eng[:2]}-{s}-chart-{n}.png")
      async def tapc(sel,name,w=1500):
        xy=await center(pg,sel)
        if not xy: R['iss'].append(f'{name}: {sel} not visible'); return False
        R['lat'][name]=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return True
      async def pick(ch,name):
        if not await tapc('#chartBox .cmain',name+'_menu',900): return False
        R.setdefault('opts',{})[name]=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)")
        cur=await pg.evaluate("()=>document.querySelector('#chartBox .cmain').dataset.ch")
        if cur==ch and await pg.evaluate("()=>window.chartMode")==ch: await tapc('#chartBox .cmain',name+'_close',600); return True
        return await tapc('#chartBox .cmain' if cur==ch else f'#chartBox .copts button[data-ch={ch}]',name,2200)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      for ch in ['bar','pie']:
        if await pick(ch,'us_'+ch):
          g=await pg.evaluate(GEOM); R['us_'+ch]=g; R['iss']+=check(g,W,H,'US '+ch); await shot('us-'+ch)
      # name bubble on a thumbnail in the bar view
      await pick('bar','us_bar2')
      cand=await pg.evaluate("()=>[...document.querySelectorAll('#cands .cand')].filter(e=>e.offsetParent).map(e=>e.className)")
      xy=await center(pg,'#cands .cand img')
      if xy:
        R['lat']['thumb_bubble']=await tap_latency(pg,*xy); await pg.wait_for_timeout(500)
        bub=await pg.evaluate("()=>{const e=document.getElementById('iconBub');if(!e)return null;const r=e.getBoundingClientRect();return [e.textContent,Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]}")
        R['bubble']=bub; await shot('bubble')
        if not bub: R['iss'].append('US bar: tapping a thumbnail shows no name bubble')
        elif bub[3]>W or bub[1]<0: R['iss'].append(f'US bar: bubble off screen {bub}')
        cand2=await pg.evaluate("()=>[...document.querySelectorAll('#cands .cand')].filter(e=>e.offsetParent).map(e=>e.className)")
        if cand2!=cand: R['iss'].append(f'US bar: thumbnail tap changed candidates {cand} -> {cand2}')
        xo=await center(pg,'#cands .sechip')
        if xo:
          await pg.touchscreen.tap(*xo); await pg.wait_for_timeout(500); R['bubble_other']=await pg.evaluate("()=>document.getElementById('iconBub')&&document.getElementById('iconBub').textContent")
          if R['bubble_other']!='Other': R['iss'].append(f"US bar: Other chip bubble = {R['bubble_other']}")
        await pg.wait_for_timeout(3500); R['bubble_after_3s']=await pg.evaluate("()=>!!document.getElementById('iconBub')")
        if R['bubble_after_3s']: R['iss'].append('US bar: bubble still open after 3.5 s')
      # range
      await pg.evaluate("()=>{window.__ySelectAll();return true}"); await pg.wait_for_timeout(3000)
      g=await pg.evaluate(GEOM); R['us_range']=g; R['iss']+=check(g,W,H,'US range '+str(g['mode'])); await shot('us-range')
      # time row open + pie
      await pg.evaluate("()=>{window.__ySet&&0}"); 
      # list view
      await tapc('#bGeo','open_geo',1200); await tapc('li.la-row','all_states',5000)
      R['list_opts']=await pg.evaluate("()=>{document.querySelector('#chartBox .cmain').click();return new Promise(r=>setTimeout(()=>{const o=[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch);document.querySelector('#chartBox .cmain').click();r(o)},700))}")
      if 'pie' in (R['list_opts'] or []): R['iss'].append(f"list range offers pie {R['list_opts']}")
      # single year 2024 in the list
      await pg.evaluate("()=>{const w=document.querySelector('.kn.a');return true}")
      for ch in ['gbar','bar']:
        if await pick(ch,'list_'+ch):
          rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,4).map(r=>({t:r.innerText.replace(/\\n/g,' | '),pie:!!r.querySelector('svg circle,.pwr'),gb:r.querySelectorAll('.gbt').length,sb:r.querySelectorAll('.sbw').length}))")
          R['list_'+ch]=rows; await shot('list-'+ch)
      R['build']=await pg.evaluate('window.BUILD'); R['err']=log['pageerr'][:5]+[x for x in log['console'] if x.startswith('error')][:5]
      print(tag,json.dumps({'iss':R['iss'],'lat':R['lat'],'opts':R.get('opts'),'list_opts':R.get('list_opts'),'bubble':R.get('bubble'),'err':R['err']})[:2500],flush=True)
      await c.close()
    await b.close()
  json.dump(out,open(f'b1585p18-chart-{eng}-'+'_'.join(which)+'.json','w'),indent=1)
asyncio.run(main())
