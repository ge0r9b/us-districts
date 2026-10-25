# Oct 25 10AM (1618): % vs # and sort on county + place lists; time slider 16/20/24 on counties; reload restore after drill-in and after year change.
# Args: engine WxH "State|County|Place,..."
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value||document.getElementById('gq').placeholder,list:document.body.classList.contains('listmode'),ysl:window.__ysl&&window.__ysl.get(),ylab:[...document.querySelectorAll('#ysl .tk.a,#ysl .kn.a,.ylab,#bTime')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()).join('/'),loading:[...document.querySelectorAll('.loading,.spinner,[aria-busy=true]')].filter(e=>e.offsetParent).length})"
NM="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&(e.textContent.trim()===t||e.textContent.trim().startsWith(t+' ')||e.textContent.trim()===t.replace(/ County$/,'')));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
def kv(s):
  s=s.strip().replace(',','')
  m=re.match(r'^([\d.]+)([KM]?)$',s)
  if not m: return None
  return float(m.group(1))*{'':1,'K':1e3,'M':1e6}[m.group(2)]
def check(pct,num):
  o={'n':[len(pct),len(num)],'names_same':[r.split(' | ')[0] for r in pct]==[r.split(' | ')[0] for r in num],'order':[],'mismatch':[]}
  tots=[]
  for rp,rn in zip(pct,num):
    p=rp.split(' | ')[1:]; n=[kv(x) for x in rn.split(' | ')[1:]]
    if None in n or not n: continue
    tots.append(sum(n))
    try: pv=[float(x.rstrip('%')) for x in p]
    except: continue
    # only check rows where both numbers are exact (<1000) or large; compare shares
    if all(x<1000 for x in n) and sum(n)>0 and len(pv)>=2:
      sh=[100*x/sum(n) for x in n]
      if any(abs(a-b)>0.6 for a,b in zip(sh,pv)): o['mismatch'].append([rp,rn])
  o['order']=[i for i in range(1,len(tots)) if tots[i]>tots[i-1]*1.15+50]
  return o
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for spec in sys.argv[3].split(','):
      st,cn,pl=spec.split('|'); R=out[spec]={}
      c,pg,log=await ctx(b,W,H,W<600,eng); tag=f"shotsh1000/b1618h10-{eng[:2]}-{W}x{H}-md-{re.sub(r'[^A-Za-z]','',cn)}"
      async def tap(sel,w=1500):
        xy=await center(pg,sel)
        if not xy: return 'nosel'
        v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
      async def tapn(t):
        await pg.evaluate(NM,t); await pg.wait_for_timeout(400); xy=await pg.evaluate(NM,t)
        if xy: v=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); return v
        return None
      async def lvl(name):
        await pg.evaluate("()=>{const l=document.getElementById('listView');if(l)l.scrollTop=0}"); await pg.wait_for_timeout(300)
        L={}; await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
        L['hdr']=await pg.evaluate(HDR); L['th_pct']=await pg.evaluate(TH); pct=await pg.evaluate(ROWS)
        await safeshot(pg,f'{tag}-{name}-pct.png')
        await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1200)
        L['th_num']=await pg.evaluate(TH); num=await pg.evaluate(ROWS); await safeshot(pg,f'{tag}-{name}-num.png')
        L['rows_pct']=pct[:8]; L['rows_num']=num[:8]; L['check']=check(pct,num)
        L['sort_lat']=await tap('#laSort'); fl=await pg.evaluate(ROWS); L['rows_flip']=fl[:4]
        L['flip_is_reverse']=[r.split(' | ')[0] for r in fl[:3]]==[r.split(' | ')[0] for r in num[::-1][:3]]
        L['sort2_lat']=await tap('#laSort'); L['back_same']=(await pg.evaluate(ROWS))[:5]==num[:5]
        await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000)
        return L
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      R['state_list']=await lvl('counties')
      R['tapC_lat']=await tapn(cn); R['county_list']=await lvl('places')
      # slider
      R['bTime_lat']=await tap('#bTime',1200); R['years']={}
      for i,y in [(0,'2016'),(1,'2020'),(2,'2024')]:
        xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
        lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(3500)
        R['years'][y]={'lat':lat,'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3]}
        await safeshot(pg,f'{tag}-year{y}.png')
      # reload after year change (now 2024 -> set 2020 then reload)
      xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",1)
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3000)
      R['pre_reload']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3],'url':pg.url}
      await pg.reload(wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(7000)
      R['post_reload']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3],'url':pg.url}
      await safeshot(pg,f'{tag}-reload-y2020.png')
      # drill into place then reload
      if pl:
        R['tapP_lat']=await tapn(pl); R['place_list']=await lvl('placeprec')
        R['pre_reload2']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3]}
        await pg.reload(wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(7000)
        R['post_reload2']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3]}
        await safeshot(pg,f'{tag}-reload-place.png')
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(json.dumps({spec:R})[:6000],flush=True); await c.close()
    json.dump(out,open(f"b1618h1000-modes-{eng}-{W}x{H}.json",'w'),indent=1); await b.close()
asyncio.run(main())
