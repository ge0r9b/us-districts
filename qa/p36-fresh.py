# pass 36 (build 1615): 2016 state totals vs FEC, All States sort in %/#/range, # mode pie/bar/line, slider drag at 1024x768
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p35-states.py').read().split('async def main')[0].split('from gaps import typegq')[1].replace("exec(open('p33-flow.py')","exec(open('p33-flow.py')"))
AB=json.load(open('fec16.json')).keys()
NAMES=dict(AL='Alabama',AK='Alaska',AZ='Arizona',AR='Arkansas',CA='California',CO='Colorado',CT='Connecticut',DE='Delaware',DC='District of Columbia',FL='Florida',GA='Georgia',HI='Hawaii',ID='Idaho',IL='Illinois',IN='Indiana',IA='Iowa',KS='Kansas',KY='Kentucky',LA='Louisiana',ME='Maine',MD='Maryland',MA='Massachusetts',MI='Michigan',MN='Minnesota',MS='Mississippi',MO='Missouri',MT='Montana',NE='Nebraska',NV='Nevada',NH='New Hampshire',NJ='New Jersey',NM='New Mexico',NY='New York',NC='North Carolina',ND='North Dakota',OH='Ohio',OK='Oklahoma',OR='Oregon',PA='Pennsylvania',RI='Rhode Island',SC='South Carolina',SD='South Dakota',TN='Tennessee',TX='Texas',UT='Utah',VT='Vermont',VA='Virginia',WA='Washington',WV='West Virginia',WI='Wisconsin',WY='Wyoming')
CH="()=>document.getElementById('chartBox').innerText.replace(/\\n/g,' | ').slice(0,300)"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; parts=sys.argv[3].split(','); out={'parts':parts}
  pre=f"shots36/b1615p36-{eng[:2]}-{W}x{H}-fresh"
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    async def tap(sel,wait=0):
      xy=await center(pg,sel)
      if not xy: return None
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return v
    async def setnum(want):
      if (await pg.evaluate("()=>window.__numMode()"))==want: return 'already'
      l=await tap('#bNum',1200)
      opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
      if opt and want!='pct': await tap_latency(pg,*opt); await pg.wait_for_timeout(1800)
      return [l,await pg.evaluate("()=>window.__numMode()")]
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000); out['build']=await pg.evaluate("window.BUILD")
    if 'y16' in parts:
      f16=json.load(open('fec16.json')); rows=[]; S=[0,0,0]; F=[0,0,0]
      for a in AB:
        v=await pg.evaluate("n=>{try{return window.__stTot(n,'2016')}catch(e){return String(e)}}",NAMES[a])
        o=f16[a]; fo=[o['C'],o['T'],o['C']+o['T']+o['O']]
        if isinstance(v,list):
          d=[v[i]-fo[i] for i in range(3)]; pc=[round(100*d[i]/fo[i],4) for i in range(3)]
          for i in range(3): S[i]+=v[i]; F[i]+=fo[i]
          rows.append((a,v,fo,d,pc))
        else: rows.append((a,v,fo,None,None))
      out['y16']={'rows':rows,'app_sum':S,'fec_sum':F,'nat_pct':[round(100*(S[i]-F[i])/F[i],4) for i in range(3)],'over01':[r for r in rows if r[4] and max(abs(x) for x in r[4])>=0.1],'nonlist':[r for r in rows if r[3] is None]}
      await pg.evaluate("()=>window.__ySetYr(0)"); await pg.wait_for_timeout(3000); out['y16']['us_th']=await pg.evaluate(TH)
      await setnum('num'); await pg.wait_for_timeout(1500); out['y16']['us_th_num']=await pg.evaluate(TH); await safeshot(pg,pre+'-US16-num.png')
      await setnum('pct'); await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(2500)
      print('y16',json.dumps({k:v for k,v in out['y16'].items() if k!='rows'}),flush=True)
    if 'sort' in parts:
      S=out['sort']={}
      await tap('#bGeo',1200); await tap('li.la-row',5000)
      for mode in ['pct','num']:
        if mode=='num': S['setnum']=await setnum('num')
        for yl,js in [('24','window.__ySetYr(2)'),('16','window.__ySetYr(0)'),('20-24','window.__ySelectAll()')]:
          await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(3000)
          r=await pg.evaluate(ROWS); k=f'{mode}-{yl}'; G=S[k]={'n':len(r),'rows':r[:5],'last':r[-2:],'order':order(r),'th':await pg.evaluate(TH),'hdr':await pg.evaluate(HDR),'layout':await pg.evaluate(LAYOUT)}
          await safeshot(pg,f'{pre}-sort-{k}.png')
          G['lat_flip']=await tap('#laSort',1800); r2=await pg.evaluate(ROWS); G['flip_rows']=r2[:5]; G['flip_order']=order(r2); G['flip_layout']=await pg.evaluate(LAYOUT)
          await safeshot(pg,f'{pre}-sort-{k}-flip.png')
          G['lat_flip2']=await tap('#laSort',1800); r3=await pg.evaluate(ROWS); G['back_same']=r3[:5]==r[:5]
          print('sort',k,json.dumps({x:G[x] for x in G if 'layout' not in x})[:1400],G['layout'],G['flip_layout'],flush=True)
      await setnum('pct'); await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(2000)
      await tap('#bGlobe',3500)
    if 'charts' in parts:
      C=out['charts']={}
      for st in ['Colorado','Virginia']:
        await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
        C[st]={'tot':await pg.evaluate("n=>{const o={};for(const y of ['2016','2020','2024'])o[y]=window.__stTot(n,y);return o}",st)}
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
        for mode in ['num','pct']:
          await setnum(mode)
          for yl,js in [('24','window.__ySetYr(2)'),('16','window.__ySetYr(0)'),('20-24','window.__ySelectAll()'),('16-24','window.__ySet16(2)')]:
            await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(2500)
            await tap('#chartBox .cmain',900); opts=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)")
            for ch in opts:
              if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',900)
              l=await tap(f'#chartBox .copts button[data-ch={ch}]',2200)
              k=f'{mode}-{yl}-{ch}'; C[st][k]={'lat':l,'mode':await pg.evaluate("()=>window.chartMode"),'txt':await pg.evaluate(CH),'th':await pg.evaluate(TH),'layout':await pg.evaluate(LAYOUT)}
              await safeshot(pg,f'{pre}-chart-{st}-{k}.png')
            print('chart',st,mode,yl,opts,json.dumps({k:v for k,v in C[st].items() if k.startswith(f'{mode}-{yl}')})[:1600],flush=True)
        await setnum('pct'); await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(1500)
        if await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',600)
    if 'drag' in parts:
      D=out['drag']={}
      await typegq(pg,'Pennsylvania'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1200)
      D['dom']=await pg.evaluate("()=>{const k=document.querySelector('.kn.a');const w=k.parentElement;return {w:w.outerHTML.slice(0,600),N:w.querySelectorAll('.tk').length,kn:[...w.querySelectorAll('.kn')].map(e=>{const r=e.getBoundingClientRect();return [e.className,Math.round(r.left+r.width/2),Math.round(r.top+r.height/2)]})}}")
      BOXJ="()=>{const o={};for(const id of ['vtitle','gq','bGeo','bTime','bLyr','bNum','bGlobe','ysl']){const e=document.getElementById(id);if(e&&e.offsetParent){const r=e.getBoundingClientRect();o[id]=[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}};[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).forEach((e,i)=>{const r=e.getBoundingClientRect();o['th'+i]=[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]});return o}"
      def tick(i): return pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
      async def drag(x0,y0,x1,y1,steps=12):
        if eng=='chromium':
          cdp=await c.new_cdp_session(pg)
          await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x0,'y':y0}]})
          for s in range(1,steps+1):
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x0+(x1-x0)*s/steps,'y':y0+(y1-y0)*s/steps}]}); await pg.wait_for_timeout(25)
          await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        else:
          await pg.mouse.move(x0,y0); await pg.mouse.down()
          for s in range(1,steps+1): await pg.mouse.move(x0+(x1-x0)*s/steps,y0+(y1-y0)*s/steps); await pg.wait_for_timeout(25)
          await pg.mouse.up()
      for nm,(fi,ti) in [('24to16',(2,0)),('16to20',(0,1)),('20to24',(1,2))]:
        a=await pg.evaluate(BOXJ); y0=await pg.evaluate("()=>window.__ysl.get()")
        # drag the active knob
        kn=await pg.evaluate("()=>{const r=document.querySelector('.kn.a').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
        t=await tick(ti); await pg.evaluate("()=>{window.__dl=[];window.__dt0=performance.now();const f=()=>{window.__dl.push([Math.round(performance.now()-window.__dt0),JSON.stringify(window.__ysl.get()),(document.querySelector('.cand')||{}).innerText]);if(performance.now()-window.__dt0<2500)requestAnimationFrame(f)};requestAnimationFrame(f)}")
        await drag(kn[0],kn[1],t[0],t[1]); await pg.wait_for_timeout(2600)
        z=await pg.evaluate(BOXJ); y1=await pg.evaluate("()=>window.__ysl.get()")
        fr=await pg.evaluate("()=>window.__dl"); seq=[]
        for f in fr:
          if not seq or seq[-1][1:]!=f[1:]: seq.append(f)
        mv=[(k,[z[k][i]-a[k][i] for i in range(4)]) for k in a if k in z and any(abs(z[k][i]-a[k][i])>=2 for i in range(4))]
        D[nm]={'from':y0,'to':y1,'knob':kn,'target':t,'moved':mv,'gone':[k for k in a if k not in z],'new':[k for k in z if k not in a],'seq':[s[:2]+[str(s[2]).replace('\n',' ')[:40]] for s in seq][:12],'th':await pg.evaluate(TH),'ym':await pg.evaluate("()=>window.__ymode()")}
        await safeshot(pg,f'{pre}-drag-{nm}.png'); print('drag',nm,json.dumps(D[nm])[:1500],flush=True)
      # drag the slider from '16 knob across to make a range? try dragging with two-knob range if offered
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]+log['reqfail'][:4]+log['http'][:4]; print('err',out['err'],flush=True)
    await b.close()
  json.dump(out,open(f"b1615p36-fresh-{eng}-{W}x{H}-{'_'.join(parts)}.json",'w'),indent=1)
asyncio.run(main())
