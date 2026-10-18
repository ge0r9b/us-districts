# usage: python3 tests/icon-subscript.py URL -- build 1555: the S / H subscripts (and US House dome) glyph text is black on light surfaces
# (institution field / crumb, filter rows) and white only on black buttons: every visible icon <text> contrasts with the surface behind it.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:700]); fails+=0 if ok else 1
J="""()=>{ const lum=c=>{const m=(c||'').match(/[\\d.]+/g); if(!m) return null; const [r,g,b,a]=m.map(Number); if(a!==undefined&&a<0.5) return null; return (0.299*r+0.587*g+0.114*b)/255;};
  const bgOf=e=>{ for(let x=e; x&&x!==document.documentElement; x=x.parentElement){ if(x instanceof SVGElement) continue; const cs=getComputedStyle(x); const l=lum(cs.backgroundColor); if(l!==null) return {l,el:(x.id||x.className||x.tagName)+''}; } return {l:1,el:'page'}; };
  return [...document.querySelectorAll('svg text')].filter(t=>{ const r=t.getBoundingClientRect(); const s=t.closest('svg'); const sr=s.getBoundingClientRect(); return r.width>0&&sr.width<=60&&/^[SH]$/.test(t.textContent.trim())&&getComputedStyle(t).visibility!=='hidden'&&t.closest('svg').getBoundingClientRect().top<innerHeight; })
    .map(t=>{ const f=getComputedStyle(t).fill; const b=bgOf(t.closest('svg').parentElement); const hostEl=t.closest('svg').parentElement; return {t:t.textContent.trim(), fill:f, fl:lum(f), bg:b.l, where:b.el.slice(0,40), host:(hostEl.id||hostEl.className||hostEl.tagName)+''}; }); }"""
FQ="()=>{const f=document.querySelector('#barGeo .fsq .fqi, #crumbs .fqi, .fsqlbl .fqi'); if(!f) return null; const t=f.querySelector('svg text'); return {k:f.dataset.k||'', txt:t?t.textContent:'', fill:t?getComputedStyle(t).fill:'', vis:f.getBoundingClientRect().width>0}}"
async def run(b,tag,vp):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3800)
  for k,sub in (("statehouse","H"),("senate","S"),("ushouse","")):
    await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1400)
    await pg.evaluate("(k)=>{const b=document.querySelector('#lyrRow .lbtn[data-k='+k+']'); if(b&&!b.classList.contains('on')) b.click()}",k); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
    fq=await pg.evaluate(FQ)
    if sub: ck(f"{tag} {k}: the field icon's '{sub}' subscript is black",fq and fq['txt']==sub and fq['fill'] in ('rgb(0, 0, 0)','rgb(17, 17, 17)','rgb(28, 28, 30)'),fq)
    else: ck(f"{tag} {k}: field shows the US House icon (no subscript)",fq is not None and fq['txt']=='',fq)
    r=await pg.evaluate(J); bad=[x for x in r if x['fl'] is None or abs(x['fl']-x['bg'])<0.5]
    ck(f"{tag} {k}: every visible S/H subscript contrasts with its surface ({len(r)} checked)",(r or not sub) and not bad,bad or r)
    dark=[x for x in r if x['bg']<0.3]; ck(f"{tag} {k}: subscripts on black buttons are white",all(x['fl']>0.7 for x in dark),dark)
    await pg.screenshot(path=f"/workspace/pv/t1555/sub-{tag}-{k}.png")
    await pg.evaluate("()=>{ if(document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(800)
  # type row open: the active (black) button's subscript is white, the others black
  await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=senate]'); b&&b.click()}"); await pg.wait_for_timeout(2500)
  await pg.evaluate("()=>{const r=document.getElementById('lyrRow'); if(r&&r.hidden) document.getElementById('bLyr').click()}"); await pg.wait_for_timeout(1200)
  r=await pg.evaluate(J); bad=[x for x in r if x['fl'] is None or abs(x['fl']-x['bg'])<0.5]
  ck(tag+f" type row open: S and H subscripts contrast with their buttons ({len(r)} checked; white on the black active one)",len(r)>=2 and not bad and any(x['bg']<0.3 and x['fl']>0.7 for x in r),bad or r)
  await pg.screenshot(path=f"/workspace/pv/t1555/sub-{tag}-typerow.png")
  ck(tag+" no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp in (("ph",{"width":390,"height":780}),("dk",{"width":1280,"height":800})): await run(b,tag,vp)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
