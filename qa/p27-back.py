# pass 27: QA-020 re-test on 1603+: list-view drill CA > Los Angeles > Back (x2), latency, per-frame chrome boxes + heat-layer count, heat colours vs the first CA visit, map after Back
import asyncio,json,sys,hashlib
from playwright.async_api import async_playwright
from common import *
BOX="""()=>{const o={};const add=(k,e)=>{if(!e||!e.offsetParent&&getComputedStyle(e).position!=='fixed')return;const r=e.getBoundingClientRect();if(!r.width||!r.height)return;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||+cs.opacity===0)return;o[k]=[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]};
 for(const id of ['vtitle','crumbs','ysl','gq','bSearch','bGeo','bTime','bLyr','bNum','bGlobe','bBack','laSort']) add(id,document.getElementById(id));
 add('chartBtn',document.querySelector('#chartBox .cmain'));
 [...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).forEach((e,i)=>add('thumb'+i,e));
 const fr=[...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent); add('firstRow',fr);
 return o}"""
HN="()=>{try{const f=l=>l.getLayers?l.getLayers().reduce((a,x)=>a+f(x),0):1;return heatLayer?f(heatLayer):-1}catch(e){return -2}}"
HEAT="""()=>{try{const out=[];const f=l=>{if(l.getLayers)l.getLayers().forEach(f);else out.push((l.options&&l.options.fillColor)||'?')};if(!heatLayer)return null;f(heatLayer);const h={};out.forEach(c=>h[c]=(h[c]||0)+1);const top=Object.entries(h).sort((a,b)=>b[1]-a[1]).slice(0,6);return {n:out.length,top,sig:out.join('|')}}catch(e){return {err:String(e)}}}"""
SAMPLE="""(ms)=>new Promise(res=>{const fr=[];const t0=performance.now();const f=()=>{setTimeout(()=>{const t=performance.now()-t0;fr.push([Math.round(t),(%s)(),(%s)(),document.querySelectorAll('#listView .lvrow').length,((document.querySelector('#listView .lvrow .nmx')||{}).textContent||'').trim()]);if(t<ms)requestAnimationFrame(f);else res(fr)},0)};requestAnimationFrame(f)})"""%(BOX,HN)
def transient(frames,final):
  seq={}
  for t,o,*_ in frames:
    for k,v in o.items():
      s=seq.setdefault(k,[])
      if not s or s[-1][1]!=v: s.append((t,v))
  return {k:s for k,s in seq.items() if len(s)>2 or (len(s)==2 and final.get(k)!=s[-1][1])}
def diff(a,b):
  out=[]
  for k in sorted(set(a)|set(b)):
    if k in a and k in b:
      d=[b[k][i]-a[k][i] for i in range(4)]
      if any(abs(x)>=2 for x in d): out.append([k,d])
    elif k in a: out.append([k,'gone'])
    else: out.append([k,'new'])
  return out
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
def gap(fr):
  g=[fr[i+1][0]-fr[i][0] for i in range(len(fr)-1)]; return [max(g),fr[g.index(max(g))][0]] if g else None
def tl(fr):
  hs=[]; prev=None
  for t,o,hn,nr,first in fr:
    if (hn,nr,first)!=prev: hs.append([t,hn,nr,first]); prev=(hn,nr,first)
  return hs
def sig(h): return hashlib.md5(h['sig'].encode()).hexdigest()[:10] if h and 'sig' in h else None
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2].split(','); SZ={'1024x768':(1024,768),'1024x576':(1024,576),'390':(390,844),'375':(375,667),'320':(320,568)}
  R={'eng':eng,'sizes':{}}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for size in sizes:
      W,H=SZ[size]; c,pg,log=await ctx(b,W,H,W<600,eng); S=R['sizes'][size]={'reps':[]}
      try:
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000); S['build']=R['build']=await pg.evaluate("window.BUILD")
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
        S['allstates']=await tap_latency(pg,*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        for rep in range(2):
          r={}
          xy=await pg.evaluate(NMXY,'CA'); await pg.wait_for_timeout(300); r['drillCA']=await tap_latency(pg,*xy); await pg.wait_for_timeout(4000)
          hCA=await pg.evaluate(HEAT); r['heatCA']={'n':hCA and hCA.get('n'),'top':hCA and hCA.get('top'),'sig':sig(hCA)}
          xy=await pg.evaluate(NMXY,'Los Angeles'); await pg.wait_for_timeout(300)
          samp=asyncio.ensure_future(pg.evaluate(SAMPLE,1200)); r['drillLA']=await tap_latency(pg,*xy); fr=await samp; await pg.wait_for_timeout(4000)
          z=await pg.evaluate(BOX); r['drillLA_transient']=transient(fr,z); r['drillLA_timeline']=tl(fr); r['drillLA_maxgap']=gap(fr); r['nLA']=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow').length")
          a=await pg.evaluate(BOX); xy=await center(pg,'#bBack')
          samp=asyncio.ensure_future(pg.evaluate(SAMPLE,1500)); r['back']=await tap_latency(pg,*xy); fr=await samp
          await pg.wait_for_timeout(3000); z=await pg.evaluate(BOX); hB=await pg.evaluate(HEAT)
          r['heatBack']={'n':hB and hB.get('n'),'top':hB and hB.get('top'),'sig':sig(hB)}; r['heat_same_as_CA']=sig(hB)==sig(hCA)
          r['back_moved']=diff(a,z); r['back_transient']=transient(fr,z)
          # when did the heat count change, and when did the list rows change
          hs=[]; prev=None
          for t,o,hn,nr,first in fr:
            if (hn,nr,first)!=prev: hs.append([t,hn,nr,first]); prev=(hn,nr,first)
          r['back_timeline']=hs; r['back_maxgap']=gap(fr); r['nBack']=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow').length")
          await safeshot(pg,f"../shots/b{R['build'][-4:]}p27-{eng[:2]}-{size}-back-rep{rep}.png")
          print(eng,size,rep,json.dumps({k:v for k,v in r.items() if k not in('back_transient','drillLA_transient')}),'transient',list(r['back_transient'].keys()),list(r['drillLA_transient'].keys()),flush=True)
          S['reps'].append(r)
          if rep==1:
            # see the map under the list after Back: globe > map, shot, heat, then back to list
            S['map_lat']=await tap_latency(pg,*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
            hm=await pg.evaluate(HEAT); S['map_heat']={'n':hm and hm.get('n'),'top':hm and hm.get('top'),'sig':sig(hm),'same_as_CA':sig(hm)==sig(hCA)}
            S['map_state']=await pg.evaluate("()=>({crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),z:map.getZoom(),c:[+map.getCenter().lat.toFixed(2),+map.getCenter().lng.toFixed(2)]})")
            await safeshot(pg,f"../shots/b{R['build'][-4:]}p27-{eng[:2]}-{size}-map-after-back.png"); print('map',json.dumps(S['map_heat']),S['map_state'],flush=True)
            break
          # Back to All States for the next rep
          await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3500)
      except Exception as e: S['EXC']=str(e)[:300]; print('EXC',size,str(e)[:200],flush=True)
      S['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:8]+log['reqfail'][:5]+log['http'][:5]
      await c.close()
    await b.close()
  json.dump(R,open(f"b{R.get('build','0000')[-4:]}p27-back-{eng}.json",'w'),indent=1)
asyncio.run(main())
