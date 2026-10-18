# b1576: QA-045 re-test. Every state + DC, one Chromium, 1024x768 and 390x844. Thumbnail size at the first painted frame after the switch,
# at 300 ms and settled (3 s); clipping/overlap; crumb icon; layout shifts. Transitions: DE after DC, AK after AL, US precinct list after Blount.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from cmp import AB
M="""()=>{const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&e.offsetParent};
 const ims=[...document.querySelectorAll('img')].filter(i=>/img\\/[a-z_0-9-]+\\.(jpg|png|webp)/i.test(i.getAttribute('src')||'')&&!/flags|stateflags|seal|icons?\\//.test(i.getAttribute('src'))&&vis(i)&&i.closest('.cand,.ccol,[class*=cand],[class*=thumb]'));
 const th=ims.map(i=>{const r=i.getBoundingClientRect(),p=i.parentElement.getBoundingClientRect(),bd=i.parentElement.querySelector('.cpt');const b=bd?bd.getBoundingClientRect():null;
  return {src:(i.getAttribute('src')||'').split('/').pop().split('?')[0],w:+r.width.toFixed(1),h:+r.height.toFixed(1),x:Math.round(r.left),y:Math.round(r.top),box:[Math.round(p.left),Math.round(p.top),+p.width.toFixed(1),+p.height.toFixed(1)],badge:b?[Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height),bd.textContent]:null,
   clip:(r.left<p.left-.5||r.top<p.top-.5||r.right>p.right+.5||r.bottom>p.bottom+.5||r.left<0||r.top<0||r.right>innerWidth||r.bottom>innerHeight)}});
 let ov=[];for(let a=0;a<th.length;a++)for(let b=a+1;b<th.length;b++){const A=th[a].box,B=th[b].box;if(A[0]<B[0]+B[2]-.5&&B[0]<A[0]+A[2]-.5&&A[1]<B[1]+B[3]-.5&&B[1]<A[1]+A[3]-.5)ov.push([a,b])}
 const f=document.querySelector('#crumbs .cic img'),fr=f?f.getBoundingClientRect():null;
 return {crumb:(document.getElementById('crumbs')||{}).innerText,icon:f?{src:(f.getAttribute('src')||'').split('/').slice(-2).join('/').split('?')[0],nat:[f.naturalWidth,f.naturalHeight],r:[+fr.width.toFixed(1),+fr.height.toFixed(1)],ok:f.complete&&f.naturalWidth>0}:null,
  thw:getComputedStyle(document.documentElement).getPropertyValue('--thw').trim(),th,ov}}"""
REC="""(n)=>{window.__fr=[];window.__shifts=[];const t0=performance.now();const m=%s;const go=()=>{const x=m();window.__fr.push({t:Math.round(performance.now()-t0),crumb:x.crumb,th:x.th.map(z=>[z.w,z.h,z.x,z.y]),icon:x.icon&&x.icon.r});if(performance.now()-t0<1200)requestAnimationFrame(go)};
 if(n){const s=document.getElementById('state');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}))} requestAnimationFrame(go);return 1}"""%M
async def boot(b,W,H):
  c,pg,log=await ctx(b,W,H,W<600)
  await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map&&document.getElementById('state').options.length>40",timeout=90000); await pg.wait_for_timeout(3500)
  return c,pg,log
async def sw(pg,n=None,click=None):
  if click: await pg.evaluate(REC.replace("if(n){","if(0){"),None); await pg.evaluate(click)
  else: await pg.evaluate(REC.replace('if(n){','if(n!==null){'),n)
  await pg.wait_for_timeout(300); e=await pg.evaluate(M)
  await pg.wait_for_timeout(2700); l=await pg.evaluate(M)
  fr=await pg.evaluate("window.__fr"); sh=await pg.evaluate("window.__shifts")
  # first painted frame where thumbnails are present
  first=next((f for f in fr if f['th']),None)
  sizes=sorted({(z[0],z[1]) for f in fr for z in f['th']})
  # jumps: thumbnail position change between consecutive frames after they first appear
  jumps=[]
  for a,b2 in zip(fr,fr[1:]):
    if a['th'] and b2['th'] and len(a['th'])==len(b2['th']):
      for p,q in zip(a['th'],b2['th']):
        d=[q[i]-p[i] for i in (2,3,0,1)]
        if any(abs(v)>0.5 for v in d): jumps.append({'t':b2['t'],'dx':d[0],'dy':d[1],'dw':d[2],'dh':d[3]}); break
  fz=[];prev=None
  for f in fr:
    k=json.dumps([f['crumb'][:40],f['th']])
    if k!=prev: fz.append(f); prev=k
  return {'frames':fz[:12],'first':first,'early':e,'late':l,'sizes':sizes,'jumps':jumps[:5],'shifts':sh[:6],'nframes':len(fr)}
def short(r):
  f=r['first']; return f"first@{f['t'] if f else '-'}={f['th'][0][:2] if f else None} 300ms={[ (z['w'],z['h']) for z in r['early']['th']][:1]} late={[ (z['w'],z['h']) for z in r['late']['th']][:1]} all={r['sizes']} icon={r['late']['icon']} clip={sum(z['clip'] for z in r['late']['th'])} ov={len(r['late']['ov'])} jumps={len(r['jumps'])} shifts={len(r['shifts'])}"
VISTXT="(t)=>{const L=[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent&&e.innerText);const nm=e=>e.innerText.trim().split('\\n').map(x=>x.replace('›','').trim()).filter(x=>x.length>1)[0]||'';let e=L.filter(e=>nm(e)===t);if(!e.length)return null;const r=e[e.length-1];r.scrollIntoView({block:'nearest'});r.click();return 1}"
async def main():
  out={}; tags=sys.argv[1].split(','); only=sys.argv[2].split(',') if len(sys.argv)>2 else None
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag in tags:
      W,H={'1024x768':(1024,768),'390':(390,844)}[tag]
      import os
      fn=f'b1584p16-thumbs-{tag}.json'
      R=out[tag]=json.load(open(fn))[tag] if os.path.exists(fn) and not only else {'states':{},'trans':{}}
      c,pg,log=await boot(b,W,H); R['build']=await pg.evaluate('window.BUILD'); R['US']=await pg.evaluate(M)
      lst=[kv for kv in sorted(AB.items(),key=lambda kv:kv[1]) if kv[0]!='DC' and (not only or kv[0] in only)]
      for i,(a,n) in enumerate(lst):
        if a in R['states']: continue
        if i and i%6==0: await c.close(); c,pg,log=await boot(b,W,H)
        try: r=await sw(pg,n)
        except Exception as ex:
          print(tag,a,'retry',str(ex)[:80],flush=True)
          try: await c.close()
          except Exception: pass
          c,pg,log=await boot(b,W,H); r=await sw(pg,n); r['retried']=True
        R['states'][a]=r
        if a in ('AL','DE','NH','GA','NE'): await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-{a}.png')
        print(tag,a,short(r),flush=True)
        json.dump(out,open(f'b1584p16-thumbs-{tag}.json','w'),indent=1)
      R['err']=log['pageerr'][:5]
      await c.close()
      if R['trans'].get('USlist_after_Blount'): continue
      # DC, then DE after DC
      c,pg,log=await boot(b,W,H)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
      R['trans']['DC']=await sw(pg,click="()=>{const e=[...document.querySelectorAll('.lvrow')].filter(e=>/^\\s*DC\\b/.test(e.innerText)).pop();e.scrollIntoView();e.click();return 1}")
      await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-DC.png'); print(tag,'DC',short(R['trans']['DC']),flush=True)
      R['trans']['DE_after_DC']=await sw(pg,'Delaware'); R['trans']['DE_field']=await pg.evaluate("()=>{const g=document.getElementById('gq');return [g.value,g.placeholder,document.getElementById('crumbs').innerText]}"); print('QA-061',R['trans']['DE_field'],flush=True); await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-DE-after-DC.png'); print(tag,'DE<DC',short(R['trans']['DE_after_DC']),flush=True)
      await c.close()
      # AK after AL
      c,pg,log=await boot(b,W,H)
      R['trans']['AL']=await sw(pg,'Alabama'); R['trans']['AK_after_AL']=await sw(pg,'Alaska'); print(tag,'AK<AL',short(R['trans']['AK_after_AL']),flush=True)
      await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-AK-after-AL.png'); await c.close()
      # US precinct list after Blount
      c,pg,log=await boot(b,W,H)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate(VISTXT,'Alabama'); await pg.wait_for_timeout(5000)
      ok=await pg.evaluate(VISTXT,'Blount County'); await pg.wait_for_timeout(7000)
      R['trans']['Blount']={'ok':ok,'m':await pg.evaluate(M)}; await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-Blount.png')
      R['trans']['Blount_list']=await sw(pg,click="()=>{document.getElementById('bGlobe').click();return 1}")
      await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-Blount-list.png'); print(tag,'Blount list',short(R['trans']['Blount_list']),flush=True)
      R['trans']['US_after_Blount']=await sw(pg,'')
      await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-US-after-Blount.png'); print(tag,'US<Blount',short(R['trans']['US_after_Blount']),'crumb',R['trans']['US_after_Blount']['late']['crumb'],flush=True)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      R['trans']['USlist_after_Blount']=await sw(pg,click="()=>{document.querySelector('li.la-row').click();return 1}")
      await pg.screenshot(path=f'../shots/b1584p16-thumbs-ch-{tag}-USlist-after-Blount.png')
      print(tag,'Blount',ok,R['trans']['Blount']['m']['crumb'],[(z['w'],z['h']) for z in R['trans']['Blount']['m']['th']],flush=True)
      print(tag,'USlist<Blount',short(R['trans']['USlist_after_Blount']),'crumb',R['trans']['USlist_after_Blount']['late']['crumb'],flush=True)
      R['err2']=log['pageerr'][:5]; await c.close()
      json.dump(out,open(f'b1584p16-thumbs-{tag}.json','w'),indent=1)
    await b.close()
asyncio.run(main())
