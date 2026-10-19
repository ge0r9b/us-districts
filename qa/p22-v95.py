# pass 21 (build 1592): verify 1590-1592 by touch: QA-044 sort chip header row (all rows, scrolled), QA-078 shared split-bar scale, QA-081 split bar start,
# QA-077 range bars with time row closed, QA-079 chart off -> map + reload, top-flush + overlaps, QA-076 bubble
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
HIT="""()=>{const s=document.getElementById('laSort');if(!s||getComputedStyle(s).display==='none')return {shown:false};const c=s.getBoundingClientRect();const lv=document.getElementById('listView');const clip=lv.getBoundingClientRect().top+(parseFloat(getComputedStyle(lv).paddingTop)||0)-2;
 const els=[...lv.querySelectorAll('.lvrow.la *')].filter(e=>e.offsetParent&&e.childElementCount===0&&(e.textContent||'').trim());
 const bad=[];for(const e of els){const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||+cs.opacity===0)continue;const top=Math.max(r.top,clip);if(top>=r.bottom)continue;if(r.left<c.right-1&&r.right>c.left+1&&top<c.bottom-1&&r.bottom>c.top+1)bad.push([(e.className||e.tagName).toString().slice(0,14),(e.textContent||'').trim().slice(0,12),Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)])}
 const rows=[...lv.querySelectorAll('.lvrow.la')].filter(r=>r.offsetParent);const fr=rows[0]&&rows[0].getBoundingClientRect();
 return {shown:true,chip:[c.left,c.top,c.right,c.bottom].map(Math.round),clip:Math.round(clip),firstRowTop:fr?Math.round(fr.top):null,st:lv.scrollTop,bad:bad.slice(0,6),n:els.length}}"""
BARS="""()=>[...document.querySelectorAll('#listView .lvrow.la .gbt')].filter(e=>e.offsetParent).map(e=>[parseFloat(e.querySelector('i').style.width),e.querySelector('b').textContent])"""
START="""()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,3);return r.map(x=>{const vr=e=>{if(!e)return null;const q=e.getBoundingClientRect();return q.width?[Math.round(q.left),Math.round(q.right)]:null};const th=[...document.querySelectorAll('#laCands img, #cands .cand img')].filter(i=>i.offsetParent).map(i=>Math.round(i.getBoundingClientRect().right));return {nm:vr(x.querySelector('.nmx')),bar:vr(x.querySelector('.sbw,.gbw,.gbt i,.sg,.cbt')),thR:Math.max(0,...th),txt:x.innerText.replace(/\\n/g,' ').slice(0,40)}})}"""
RNG="""()=>{const vis=e=>e&&e.offsetParent&&e.getBoundingClientRect().width>0;const vr=e=>{const q=e.getBoundingClientRect();return [Math.round(q.left),Math.round(q.top),Math.round(q.right),Math.round(q.bottom)]};
 const x=document.querySelector('.dmx');const rows=x?[...x.querySelectorAll('.dmr')].filter(vis).map(r=>({k:r.dataset.k,r:vr(r),bar:r.querySelector('.dmb')&&vis(r.querySelector('.dmb'))?vr(r.querySelector('.dmb')):null,t:r.innerText.replace(/\\n/g,' ')})):[];
 const ims=[...document.querySelectorAll('#cands .cand img, #cands img.dmt')].filter(vis).map(i=>({c:i.closest('.cand')?i.closest('.cand').className:i.className,r:vr(i)}));
 const col=Math.min(...[...document.querySelectorAll('.rbtn')].filter(vis).map(b=>b.getBoundingClientRect()).filter(r=>r.left>innerWidth*0.6).map(r=>r.left));
 const old=[...document.querySelectorAll('.cfoot,.lsh,.cpanel')].filter(vis).map(e=>e.textContent.slice(0,40));const txt=document.getElementById('cands').innerText;
 return {dm:document.body.classList.contains('dmerge'),rows,ims,col:Math.round(col),old,oldtxt:/pts|shift/.test(txt),timeHidden:document.getElementById('barTime').hidden,mode:window.chartMode}}"""
ST="()=>({lm:document.body.classList.contains('listmode'),la:document.body.classList.contains('listall'),ch:window.chartMode||null,rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).length,lvvis:getComputedStyle(document.getElementById('listView')).visibility,map:(()=>{const m=document.getElementById('map');const r=m.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})(),tiles:[...document.querySelectorAll('.leaflet-tile-loaded, .leaflet-overlay-pane path')].length})"
TOP="""()=>{const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return e.offsetParent!==null&&r.width>0&&r.height>0&&cs.visibility!=='hidden'&&+cs.opacity>0};const vr=e=>{const q=e.getBoundingClientRect();return [Math.round(q.left),Math.round(q.top),Math.round(q.right),Math.round(q.bottom)]};
 const bs=document.getElementById('barSearch');const els=[...document.querySelectorAll('.v2bar, .rbtn, #cands .cand, #crumbs, #chartBox .cmain, #laSort, #bBack')].filter(vis);
 const ov=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],b=els[j];if(a.contains(b)||b.contains(a))continue;const p=a.getBoundingClientRect(),q=b.getBoundingClientRect();const ix=Math.min(p.right,q.right)-Math.max(p.left,q.left),iy=Math.min(p.bottom,q.bottom)-Math.max(p.top,q.top);if(ix>2&&iy>2)ov.push([(a.id||a.className).toString().slice(0,20),vr(a),(b.id||b.className).toString().slice(0,20),vr(b)])}
 const minTop=Math.min(...els.map(e=>e.getBoundingClientRect().top));const off=els.filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+1||r.bottom>innerHeight+1||r.left<-1}).map(e=>[(e.id||e.className).toString().slice(0,20),vr(e)]);
 return {bar:bs?Math.round(bs.getBoundingClientRect().top*10)/10:null,map:Math.round(document.getElementById('map').getBoundingClientRect().top),minTop:Math.round(minTop),ov:ov.slice(0,10),off,rows:[...document.querySelectorAll('.v2bar')].filter(vis).map(e=>[e.id,...vr(e)])}}"""
def num(t):
  t=t.replace('\u2212','-').replace('%','').replace('+','').replace(',','').strip(); m=1
  if t.endswith('M'): m=1e6; t=t[:-1]
  elif t.endswith('K'): m=1e3; t=t[:-1]
  try: return abs(float(t)*m)
  except: return None
async def main():
  eng=sys.argv[1]; which=sys.argv[2:]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      s=tag.replace('iphone','').replace('ipad',''); R=out[tag]={'iss':[],'lat':{},'chip':[],'scale':{},'start':{},'rng':{},'off':{},'top':{}}
      pre=f"../shots/b1595p22-{eng[:2]}-{s}-v"
      c,pg,log=await ctx(b,W,H,mob,eng)
      async def tap(sel,name=None,w=1200):
        xy=await center(pg,sel)
        if not xy: R['iss'].append(f'{name or sel}: not visible'); return False
        l=await tap_latency(pg,*xy)
        if name: R['lat'][name]=l
        await pg.wait_for_timeout(w); return True
      async def tick(i,w=3500):
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',None,900)
        xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(w)
      async def pick(ch):
        await tap('#chartBox .cmain',None,800)
        cur=await pg.evaluate("()=>document.querySelector('#chartBox .cmain').dataset.ch")
        if cur==ch and await pg.evaluate("()=>window.chartMode")==ch: await tap('#chartBox .cmain',None,600); return
        await tap('#chartBox .cmain' if cur==ch else f'#chartBox .copts button[data-ch={ch}]',None,2200)
      async def setnum(want):
        cur=await pg.evaluate("()=>window.__numMode&&window.__numMode()")
        if (cur=='num')==(want=='num'): return
        await tap('#bNum',None,900); sym='#' if want=='num' else '%'
        opt=await pg.evaluate("s=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()===s&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",sym)
        if opt: await pg.touchscreen.tap(*opt); await pg.wait_for_timeout(1800)
        if (await pg.evaluate("()=>window.__numMode()")=='num')!=(want=='num'): R['iss'].append(f'could not set {want} mode')
      async def touchscroll(dy):
        # touch-drag the list (CDP in chromium; fallback scrollTop)
        await pg.evaluate(f"()=>{{const l=document.getElementById('listView');l.scrollTop={dy}}}"); await pg.wait_for_timeout(400)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      R['build']=await pg.evaluate('window.BUILD')
      # ---- F: top flush on map
      t=await pg.evaluate(TOP); R['top']['map']=t
      if abs(t['bar'])>0.5 or t['map']>0.5 or t['minTop']<0: R['iss'].append(f"top-flush map: bar {t['bar']} map {t['map']} minTop {t['minTop']}")
      if t['ov']: R['iss'].append(f"map overlaps {t['ov']}")
      if t['off']: R['iss'].append(f"map off-screen {t['off']}")
      await safeshot(pg,pre+'-top-map.png')
      # ---- E: QA-079 chart from map then off (bar, pie)
      for ch in ['bar','pie']:
        s0=await pg.evaluate(ST); await pick(ch); s1=await pg.evaluate(ST)
        t=await pg.evaluate(TOP); R['top']['chart_'+ch]=t
        if t['ov']: R['iss'].append(f"chart {ch} overlaps {t['ov']}")
        await tap('#chartBox .cmain',None,800); R['lat']['chartoff_'+ch]=await tap_latency(pg,*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2500)
        s2=await pg.evaluate(ST); R['off'][ch]=[s0,s1,s2]
        if s2['lm'] or s2['ch']: R['iss'].append(f"QA-079 chart {ch} off from map: not back on map {s2}"); await safeshot(pg,pre+f'-chartoff-{ch}.png')
      await pg.wait_for_timeout(1500); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(8000); s3=await pg.evaluate(ST); R['off']['reload']=s3
      if s3['lm'] or s3['ch']: R['iss'].append(f"QA-079 reload after chart off: not map {s3}")
      await safeshot(pg,pre+'-chartoff-reload.png')
      # ---- D: QA-077 US map > time row 2020>2024 > Bar, time row closed (two orders)
      await tick(1,3000); await pg.evaluate("()=>{window.__ySelectAll();return 1}"); await pg.wait_for_timeout(3000)
      await tap('#bTime','time_close',1500); await pick('bar'); g=await pg.evaluate(RNG); R['rng']['A_closed_then_bar']=g; await safeshot(pg,pre+'-range-closed-bar.png')
      await tap('#bTime',None,1500); g2=await pg.evaluate(RNG); R['rng']['A_reopened']=g2
      await tap('#bTime',None,1500); g3=await pg.evaluate(RNG); R['rng']['A_closed_again']=g3
      for k,g in [('closed-then-bar',R['rng']['A_closed_then_bar']),('reopened',g2),('closed-again',g3)]:
        if g['old'] or g['oldtxt']: R['iss'].append(f"QA-077 {k}: old block {g['old']} pts/shift text")
        if len(g['rows'])!=3: R['iss'].append(f"QA-077 {k}: {len(g['rows'])} range rows (dm {g['dm']})")
        for r in g['rows']:
          if r['r'][2]>g['col']-2: R['iss'].append(f"QA-077 {k}: row {r['k']} right {r['r'][2]} under button column {g['col']}")
        ims=sorted([i['r'] for i in g['ims'] if i['r'][0]<W/2],key=lambda q:q[1])
        for i,r in enumerate(sorted(g['rows'],key=lambda r:r['r'][1])):
          if i<len(ims):
            cy=(ims[i][1]+ims[i][3])/2; ry=((r['bar'] or r['r'])[1]+(r['bar'] or r['r'])[3])/2
            if abs(cy-ry)>4: R['iss'].append(f"QA-077 {k}: row {r['k']} centre y {ry} vs icon {cy}")
      # ---- G: QA-076 bubble (single-year bar)
      await tick(2,3000); await tap('#bTime',None,1200)
      if await pg.evaluate("()=>window.chartMode")!='bar': await pick('bar')
      xy=await center(pg,'#cands .cand img')
      if xy:
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(500)
        R['bubble']=await pg.evaluate("()=>{const e=document.getElementById('iconBub');const i=document.querySelector('#cands .cand img');const v=e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};return e?{t:e.textContent,b:v(e),img:v(i)}:null}")
        await safeshot(pg,pre+'-bubble.png')
      await pg.wait_for_timeout(3500)
      # ---- A/B/C: All States list modes
      await pick('bar') if await pg.evaluate("()=>window.chartMode")!='bar' else None
      await tap('#chartBox .cmain',None,800); await tap('#chartBox .cmain',None,2000)  # chart off -> map
      await tap('#bGeo',None,1200); xy=await center(pg,'li.la-row'); R['lat']['all_states_row']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
      t=await pg.evaluate(TOP); R['top']['list']=t
      if abs(t['bar'])>0.5 or t['minTop']<0: R['iss'].append(f"top-flush list: bar {t['bar']} minTop {t['minTop']}")
      if t['ov']: R['iss'].append(f"list overlaps {t['ov']}")
      async def chip(n):
        for sc in [0,13,47,200]:
          await touchscroll(sc); h=await pg.evaluate(HIT); R['chip'].append((n,sc,h))
          if not h['shown']: R['iss'].append(f'QA-044 {n}: chip not shown'); return
          if h['bad']: R['iss'].append(f"QA-044 {n} scroll {sc}: chip {h['chip']} covers {h['bad'][:3]}"); await safeshot(pg,pre+f'-chip-{n}-{sc}.png')
          if False and h['firstRowTop'] is not None and h['firstRowTop']<h['chip'][3]-1: R['iss'].append(f"QA-044 {n}: first row top {h['firstRowTop']} above chip bottom {h['chip'][3]}")
        await touchscroll(0)
      async def scale(n):
        bars=await pg.evaluate(BARS); pct=n.endswith('pct')
        r=[(w/num(t_)) for w,t_ in bars if num(t_) and w>4 and (not pct or num(t_)>=2)]
        sp=max(r)/min(r) if r else 0; R['scale'][n]=[len(r),round(sp,3),bars[:6]]
        if len(r)<10 or sp>=1.12: R['iss'].append(f"QA-078 {n}: split bars not on one scale ({len(r)} bars, spread {sp:.3f}) {bars[:5]}"); await safeshot(pg,pre+f'-scale-{n}.png')
      async def start(n): R['start'][n]=await pg.evaluate(START)
      await pick('bar'); await setnum('pct'); await chip('bar-pct'); await start('bar-pct'); await safeshot(pg,pre+'-list-bar-pct.png')
      await setnum('num'); await chip('bar-num')
      await pick('gbar'); await chip('gbar-num'); await scale('gbar-24-num'); await start('gbar-num')
      await setnum('pct'); await chip('gbar-pct'); await scale('gbar-24-pct'); await start('gbar-pct'); await safeshot(pg,pre+'-list-gbar-pct.png')
      await pick('line'); await chip('line-pct'); await setnum('num'); await chip('line-num'); await setnum('pct')
      await pg.evaluate("()=>{window.__ySelectAll();return 1}"); await pg.wait_for_timeout(3500)
      await pick('bar'); await chip('range-bar-pct'); await setnum('num'); await chip('range-bar-num'); await setnum('pct')
      await pick('gbar'); await chip('range-gbar-pct'); await scale('range-gbar-pct'); await start('range-gbar-pct'); await safeshot(pg,pre+'-list-range-gbar-pct.png')
      await setnum('num'); await chip('range-gbar-num'); await scale('range-gbar-num'); await safeshot(pg,pre+'-list-range-gbar-num.png'); await setnum('pct')
      await pick('line'); await chip('range-line-pct'); await setnum('num'); await chip('range-line-num'); await setnum('pct')
      await pg.evaluate("()=>{window.__ySet16(2);return 1}"); await pg.wait_for_timeout(5000)
      await pick('gbar'); await chip('range16-gbar-pct'); await scale('range16-gbar-pct')
      await setnum('num'); await scale('range16-gbar-num'); await setnum('pct')
      await tick(0,5000); await chip('16-gbar-pct'); await scale('16-gbar-pct'); await tick(2,3500); await chip('back24-gbar-pct')
      R['err']=log['pageerr'][:5]+[x for x in log['console'] if x.startswith('error')][:5]; R['reqfail']=log['reqfail'][:5]; R['http']=log['http'][:5]
      R['cls']=await pg.evaluate("()=>window.__cls")
      print(tag,json.dumps({'iss':R['iss'],'lat':R['lat'],'start':R['start'],'scale':{k:v[:2] for k,v in R['scale'].items()},'bubble':R.get('bubble'),'err':R['err'],'build':R['build']})[:4000],flush=True)
      await c.close()
    await b.close()
  json.dump(out,open(f'b1595p22-v-{eng}-'+'_'.join(which)+'.json','w'),indent=1)
asyncio.run(main())
