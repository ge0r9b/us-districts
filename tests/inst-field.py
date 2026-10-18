# build 1577: the institution field always searches institutions (any level, synonyms, never blank); Enter takes the top match (Canada lists its 13 provinces/territories, gray); the unisearch button is top-right on every screen
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
VIS="()=>[...document.querySelectorAll('#sheet li')].filter(l=>l.getBoundingClientRect().height>0&&!l.classList.contains('orggh')).map(l=>l.textContent.replace('›','').trim())"
EXP={'united states':'United States','us':'United States','pennsylvania':'Pennsylvania','allegheny':'Allegheny County','canada':'Canada','mexico':'Mexico'}
async def openF(pg):
    await pg.evaluate("()=>{ (document.querySelector('#barGeo .fsq input')||document.getElementById('bGeo')).click() }"); await pg.wait_for_timeout(1500)
    if not await pg.evaluate("()=>!!document.querySelector('#barGeo .fsq input')"):
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
async def SB(pg,W,tag):
    r=await pg.evaluate("()=>{const b=document.getElementById('bSearch'); const r=b.getBoundingClientRect(); const cs=getComputedStyle(b); const e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return [r.left,r.top,r.width,cs.visibility,cs.display,!!(e&&(e===b||b.contains(e)))]}")
    ck(r[2]>20 and r[0]+r[2]>W-80 and r[1]<90 and r[3]=='visible' and r[5],f"{W}: unisearch button top-right and tappable ({tag})",r)
    return r
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    pg=await b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e.stack)[:300]))
    for ctx in ['US','Alabama','Pennsylvania']:
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      if ctx!='US': await pg.evaluate("(v)=>{const s=document.getElementById('state');s.value=v;s.onchange&&s.onchange()}",ctx); await pg.wait_for_timeout(4000)
      await openF(pg)
      for q,e in EXP.items():
        await pg.fill('#barGeo .fsq input',''); await pg.type('#barGeo .fsq input',q,delay=20); await pg.wait_for_timeout(700)
        v=await pg.evaluate(VIS)
        ck(any(e in x for x in v),f"{ctx}: '{q}' lists {e} ({len(v)} rows)",v[:6])
      await pg.fill('#barGeo .fsq input',''); await pg.type('#barGeo .fsq input','zzqxv',delay=20); await pg.wait_for_timeout(700)
      v=await pg.evaluate(VIS); ck(v==['No institutions match'] or 'No institutions match' in v,f"{ctx}: nonsense says 'No institutions match'",v[:4])
    # Enter on canada -> provinces
    await pg.fill('#barGeo .fsq input',''); await pg.type('#barGeo .fsq input','canada',delay=20); await pg.wait_for_timeout(700); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
    v=await pg.evaluate("()=>[...document.querySelectorAll('#orgCountry li')].filter(l=>l.offsetParent).map(l=>l.textContent.trim())")
    ph=await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input'); const l=document.querySelector('#barGeo .fsqlbl span'); return [i&&i.placeholder,l&&l.textContent]}")
    ck('Canada' in ph and len([x for x in v if x and 'v3' not in x and 'provinces and' not in x])==13 and any('v3' in x for x in v),"Enter on 'canada' sets Canada and lists 13 provinces/territories with the v3 note",[ph,v])
    # Enter on allegheny from AL -> PA / Allegheny
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000); await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Alabama';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000)
    await openF(pg); await pg.type('#barGeo .fsq input','allegheny',delay=20); await pg.wait_for_timeout(800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
    st=await pg.evaluate("()=>[state.value,document.getElementById('county').value]")
    ck(st==['Pennsylvania','Allegheny County'],"Enter on 'allegheny' from AL opens Allegheny County, PA",st)
    ck(not er,"no page errors",er[:3]); await pg.close()
    for W,H in [(390,844),(375,667),(320,568),(1024,768)]:
      pg=await b.new_page(viewport={'width':W,'height':H},is_mobile=W<800,has_touch=True); await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await SB(pg,W,'main')
      await openF(pg); await SB(pg,W,'institution filter'); await pg.keyboard.press('Escape'); await pg.evaluate("()=>{try{closeSheet()}catch(e){}}"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>window.__geoOpen&&window.__geoOpen()"); await pg.wait_for_timeout(1000); await SB(pg,W,'geo filter'); await pg.evaluate("()=>window.__geoClose&&window.__geoClose()"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(800); await SB(pg,W,'time row')
      await pg.evaluate("()=>{const m=document.querySelector('button.rbtn.cmain'); m&&m.click()}"); await pg.wait_for_timeout(600); await SB(pg,W,'chart menu')
      await pg.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
