# pass 19 (build 1587): 1586 '16 charts blank after returning to '16; menus never dim and never move the pie; 1587 sort chip at right end of bar area
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
src=open('p21-layout.py').read()
VISTXT=re.search(r'^VISTXT="(.*)"$',src,re.M).group(1).encode().decode('unicode_escape')
CH="""()=>{const vr=e=>{if(!e)return null;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'?[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]:null};
 const bars=[...document.querySelectorAll('#cands .sebr')].map(b=>({k:b.dataset.k,bar:vr(b.querySelector('.sebt i'))}));
 const pie=vr(document.querySelector('#cands .cpie1 svg'));
 const dim=document.getElementById('chartDim');const dcs=dim&&getComputedStyle(dim);
 const fixedDim=[...document.querySelectorAll('body *')].filter(e=>{const cs=getComputedStyle(e);if(cs.position!=='fixed')return false;const r=e.getBoundingClientRect();if(r.width<innerWidth*0.9||r.height<innerHeight*0.9)return false;const m=cs.backgroundColor.match(/rgba?\\(([^)]*)\\)/);if(!m)return false;const p=m[1].split(',').map(Number);const a=p.length>3?p[3]:1;return a>0.02&&a<1&&+cs.opacity>0.02&&cs.visibility!=='hidden'&&!(p[0]>250&&p[1]>250&&p[2]>250)}).map(e=>(e.id||e.className).toString().slice(0,30)+' '+getComputedStyle(e).backgroundColor+' op'+getComputedStyle(e).opacity);
 return {mode:window.chartMode,y:window.__ymode&&window.__ymode(),bars,pie,y16d:document.body.classList.contains('y16d'),cls:document.body.className.slice(0,200),crumbs:(document.getElementById('crumbs')||{}).innerText,dim:dcs&&[dcs.backgroundColor,dcs.opacity],fixedDim}}"""
SORT="""()=>{const vr=e=>{if(!e)return null;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&+cs.opacity>0?[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]:null};
 const s=vr(document.getElementById('laSort'));const btn=[...document.querySelectorAll('button.rbtn, #chartBox .cmain')].map(vr).filter(r=>r&&r[0]>innerWidth*0.6);
 const rows=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,3).map(r=>{const leaf=[...r.querySelectorAll('*')].filter(e=>e.childElementCount===0&&(e.textContent.trim()||/^(I|B|SPAN)$/.test(e.tagName))).map(e=>({t:e.textContent.trim().slice(0,12),c:(e.className||e.tagName).toString().slice(0,20),r:vr(e)})).filter(x=>x.r);return {row:vr(r),leaf}});
 return {sort:s,btn,rows,mode:window.chartMode}}"""
def ov(a,b,m=1): return bool(a and b and min(a[2],b[2])-max(a[0],b[0])>m and min(a[3],b[3])-max(a[1],b[1])>m)
async def main():
  eng=sys.argv[1]; which=[a for a in sys.argv[2:] if a not in('sortonly','aonly')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      s=tag.replace('iphone','').replace('ipad',''); R=out[tag]={'iss':[],'lat':{}}
      c,pg,log=await ctx(b,W,H,mob,eng)
      async def shot(n): await safeshot(pg,f"../shots/b1592p21-{eng[:2]}-{s}-new-{n}.png")
      async def tap(sel,name=None,w=1200):
        xy=await center(pg,sel)
        if not xy: R['iss'].append(f'{name or sel}: not visible'); return False
        l=await tap_latency(pg,*xy)
        if name: R['lat'][name]=l
        await pg.wait_for_timeout(w); return True
      async def taptxt(t,name=None,w=4000):
        xy=await pg.evaluate(VISTXT,t)
        if not xy: R['iss'].append(f'text {t} not found'); return False
        await pg.wait_for_timeout(250); l=await tap_latency(pg,xy[0],xy[1])
        if name: R['lat'][name]=l
        await pg.wait_for_timeout(w); return True
      async def tick(i):
        xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3500)
      async def pick(ch):
        await tap('#chartBox .cmain',None,800)
        cur=await pg.evaluate("()=>document.querySelector('#chartBox .cmain').dataset.ch")
        if cur==ch and await pg.evaluate("()=>window.chartMode")==ch: await tap('#chartBox .cmain',None,600); return
        await tap('#chartBox .cmain' if cur==ch else f'#chartBox .copts button[data-ch={ch}]',None,2200)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      # ---- A: '16 chart after returning to '16 (PA and AL), bar and pie
      for st in ([] if 'sortonly' in sys.argv else ['Pennsylvania','Alabama']):
        await pg.goto(URL,wait_until='networkidle',timeout=120000); await pg.wait_for_timeout(5000)
        await typegq(pg,st); await pg.wait_for_timeout(800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
        for ch in ['bar','pie']:
          await pick(ch)
          seqv=[]
          for i,yl in [(0,'16a'),(2,'24'),(0,'16b'),(1,'20'),(0,'16c')]:
            await tick(i); g=await pg.evaluate(CH); seqv.append((yl,g['y'],g['mode'],g['pie'],[x['bar'] for x in g['bars']],g['y16d']))
            vis=g['pie'] if ch=='pie' else any(x['bar'] for x in g['bars'])
            if not vis: R['iss'].append(f"{st} {ch} at {yl} (ymode {g['y']}, chartMode {g['mode']}): chart blank"); await shot(f"{st}-{ch}-{yl}-blank")
          R[f'y16_{st}_{ch}']=seqv
        await tick(2)
      R['menus']={}
      print(tag,'A',json.dumps({'iss':R['iss'],**{k:v for k,v in R.items() if k.startswith('y16_')}})[:3000],flush=True)
      if 'aonly' in sys.argv: await c.close(); continue
      # ---- C: sort chip in list views
      errs=log['pageerr'][:]; await c.close(); c,pg,log=await ctx(b,W,H,mob,eng); log['pageerr']+=errs
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      await tap('#bGeo',None,1200); await taptxt('All States','all_states',5000)
      seen=[]
      async def chk(n):
        g=await pg.evaluate(SORT); seen.append((n,g['sort']))
        if not g['sort']: R['iss'].append(f'sort chip not visible in {n}'); return
        for q in g['btn']:
          if ov(g['sort'],q,0): R['iss'].append(f"{n}: sort chip {g['sort']} under button {q}")
        for ri,r in enumerate(g['rows']):
          for l in r['leaf']:
            if ov(g['sort'],l['r'],1): R['iss'].append(f"{n}: sort chip {g['sort']} covers row{ri} '{l['t']}' ({l['c']}) {l['r']}")
        await shot('sort-'+n)
      await pick('bar'); await chk('bar-pct')
      await tap('#bNum',None,1500); await chk('bar-num'); await tap('#bNum',None,1500)
      await pg.evaluate("()=>{window.__ySelectAll();return true}"); await pg.wait_for_timeout(3000); await chk('range-bar')
      await pick('gbar'); await chk('range-gbar')
      await pick('line'); await chk('range-line')
      await tap('#bNum',None,1500); await chk('range-line-num'); await pick('gbar'); await chk('range-gbar-num'); await tap('#bNum',None,1500)
      await tick(2); await chk('back-2024')
      xs=set(tuple(x[1]) for x in seen if x[1])
      R['sort_seen']=seen
      if len(xs)>1: R['iss'].append(f'sort chip position changes across modes: {seen}')
      R['build']=await pg.evaluate('window.BUILD'); R['err']=log['pageerr'][:5]+[x for x in log['console'] if x.startswith('error')][:5]
      print(tag,json.dumps({'iss':R['iss'],'lat':R['lat'],'menus':R['menus'],'sort':seen,'err':R['err']})[:3000],flush=True)
      await c.close()
    await b.close()
  json.dump(out,open(f'b1592p21-new-{eng}-'+'_'.join(which)+'.json','w'),indent=1)
asyncio.run(main())
