# usage: python3 tests/chart-menu.py URL -- build 1563: the chart button on the intro screen (single entity 'United States') works with touch and click:
# its options are distinct and never repeat the main button's chart (1562 showed a 2nd pie and no bar, or nothing at all while the pie was on);
# a single entity offers pie + bar (one year) or line + bar (two years); each option switches the view; tapping the open main button turns the chart off.
# Single-entity bar = one bar per answer, sorted high -> low (% in % mode, votes in # mode), names at x=52, bars end 12px short of the right edge.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:600]); fails+=0 if ok else 1
ST="""()=>{const w=document.getElementById('chartBox'),m=w.querySelector('.cmain'),r=m.getBoundingClientRect();
 const ob=[...w.querySelectorAll('.copts button')].map(b=>{const q=b.getBoundingClientRect();return {k:b.dataset.ch,x:q.left+q.width/2,y:q.top+q.height/2,w:q.width}});
 const rows=[...document.querySelectorAll('.cpanel .sebr')].map(e=>{const n=e.querySelector('.sebn').getBoundingClientRect(),t=e.querySelector('.sebt').getBoundingClientRect(),i=e.querySelector('.sebt i').getBoundingClientRect(),b=e.querySelector('.sebt b'),br=b.getBoundingClientRect();return {k:e.dataset.k,v:+e.dataset.v,n:e.querySelector('.sebn').textContent,nl:n.left,tr:t.right,il:i.left,ir:i.right,lab:b.textContent,bl:br.left,brr:br.right,vis:br.width>0}});
 return {mode:window.chartMode,main:m.dataset.ch,open:w.classList.contains('open'),opts:ob,mx:r.left+r.width/2,my:r.top+r.height/2,lm:document.body.classList.contains('listmode'),pie:!!document.querySelector('.cpanel .cpie1 svg, .cpanel .cpieL svg'),line:!!document.querySelector('.cpanel .clinechart svg'),rows,vw:innerWidth}}"""
async def tap(pg,x,y,touch):
  if touch: await pg.touchscreen.tap(x,y)
  else: await pg.mouse.click(x,y)
  await pg.wait_for_timeout(900)
async def run(b,tag,vp,touch):
  c=await b.new_context(viewport=vp,is_mobile=vp['width']<600,has_touch=True); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(4000)
  s=await pg.evaluate(ST); await tap(pg,s['mx'],s['my'],touch); s=await pg.evaluate(ST); ks=[o['k'] for o in s['opts']]
  ck(f"{tag} tap opens the chart menu",s['open'],s)
  ck(f"{tag} one year, single entity: options distinct, never the main chart, pie+bar offered ({s['main']} + {ks})",len(ks)==len(set(ks)) and s['main'] not in ks and set(ks+[s['main']])=={'pie','bar'},s)
  seen=set()
  for step in range(3):
    s=await pg.evaluate(ST)
    if not s['open']: await tap(pg,s['mx'],s['my'],touch); s=await pg.evaluate(ST)
    o=[x for x in s['opts'] if x['k'] not in seen] or s['opts']; o=o[0]; seen.add(o['k'])
    await tap(pg,o['x'],o['y'],touch); await pg.wait_for_timeout(800); s=await pg.evaluate(ST)
    shown={'pie':s['pie'],'bar':bool(s['rows'])}[o['k']]
    ck(f"{tag} option '{o['k']}' switches the view (mode {s['mode']}, menu closed, chart drawn)",s['mode']==o['k'] and not s['open'] and s['lm'] and shown and s['main']==o['k'],{k:s[k] for k in ('mode','open','lm','pie','main')})
    if o['k']=='bar':
      for nm in ('pct','num'):
        await pg.evaluate("m=>window.__setNum(m)",nm); await pg.wait_for_timeout(1600); s=await pg.evaluate(ST); r=s['rows']
        ck(f"{tag} single bar {nm}: one bar per answer (3: R, D, other)",len(r)==3 and {x['k'] for x in r}=={'rep','dem','oth'},r)
        ck(f"{tag} single bar {nm}: sorted high -> low",all(r[i]['v']>=r[i+1]['v'] for i in range(len(r)-1)),[x['v'] for x in r])
        ck(f"{tag} single bar {nm}: names at x=52, bars end 12px short of the right edge",all(abs(x['nl']-52)<=1 and abs(x['tr']-(s['vw']-12))<=1.5 for x in r),[(x['nl'],x['tr']) for x in r])
        import re
        pat=r'^\d+\.\d%$' if nm=='pct' else r'^\d+(\.\d{2}[MK]|K|M)?$|^\d+(\.\d+)?[MK]$'
        ck(f"{tag} single bar {nm}: every bar labeled with its total ({[x['lab'] for x in r]})",all(re.match(pat,x['lab']) and x['vis'] and x['bl']>=x['il']-0.5 and x['brr']<=x['tr']+0.5 for x in r),r)
        if nm=='num': ck(f"{tag} single bar num: lengths follow the vote counts",r[0]['ir']-r[0]['il']>=r[1]['ir']-r[1]['il']>=r[2]['ir']-r[2]['il'],r)
      await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000)
  # back: the open main button turns the chart off
  s=await pg.evaluate(ST); await tap(pg,s['mx'],s['my'],touch); s=await pg.evaluate(ST); ks=[o['k'] for o in s['opts']]
  ck(f"{tag} reopened menu: distinct options without the main chart ({s['main']} + {ks})",len(ks)==len(set(ks)) and s['main'] not in ks and ks,s)
  await tap(pg,s['mx'],s['my'],touch); s=await pg.evaluate(ST); ck(f"{tag} tapping the open main button turns the chart off",s['mode'] is None and not s['open'],{k:s[k] for k in ('mode','open')})
  # two years: line + bar, no pie
  await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll&&window.__ySelectAll(); }"); await pg.wait_for_timeout(2000)
  s=await pg.evaluate(ST); await tap(pg,s['mx'],s['my'],touch); s=await pg.evaluate(ST); ks=[o['k'] for o in s['opts']]
  ck(f"{tag} two years: options distinct, line+bar, no pie ({s['main']} + {ks})",len(ks)==len(set(ks)) and s['main'] not in ks and set(ks+[s['main']])=={'line','bar'},s)
  ck(f"{tag} no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp,t in (("ph-touch",{'width':390,'height':844},True),("ipad-touch",{'width':1024,'height':576},True),("ipad-click",{'width':1024,'height':576},False)):
      await run(b,tag,vp,t)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
