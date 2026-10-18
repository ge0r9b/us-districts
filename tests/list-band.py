# Build 1553: results lists start half the empty band higher (first row ~6px under the chevron/sort-glyph row, nothing overlapping);
# with no back chevron the left thumbnails mirror the clock (time row closed) / chart button (open): first thumbnail centre on its
# centre; with the chevron shown they keep their place under it; the org crumb never repeats the level noun ('All States' alone,
# 'Pennsylvania counties', 'Susquehanna County townships'); white label bubbles; the cut-off-name bubble works on township lists.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
M="""()=>{const q=s=>{const e=document.querySelector(s); if(!e) return null; const r=e.getBoundingClientRect(); return r.height>0&&getComputedStyle(e).display!=='none'?{t:r.top,b:r.bottom,l:r.left,r:r.right,c:r.top+r.height/2}:null};
 const cr=[...document.querySelectorAll('#crumbs .crumb.cur')].pop();
 return {row:q('#listView .lvrow.la'),sort:q('#laSort svg'),back:q('#bBack svg'),backBtn:q('#bBack'),time:q('#bTime'),chart:q('button.rbtn.cmain'),th:q('#laCands .lact img, #laCands .lact .lacn'),bar:q('#barTime'),open:!document.getElementById('barTime').hidden,crumb:cr&&cr.textContent,noun:cr&&cr.getAttribute('data-noun')}}"""
def sgl(w): w=''.join(ch for ch in (w or '').lower() if ch.isalpha()); w=w[:-3]+'y' if w.endswith('ies') else w; return w[:-1] if w.endswith('s') else w
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page()
    er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500)
    async def timeRow(on):
      if (await pg.evaluate("()=>!document.getElementById('barTime').hidden"))!=on: await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
    for on in (False,True):
      await timeRow(on); m=await pg.evaluate(M); tag='time row '+('open' if on else 'closed')
      gap=m['row']['t']-m['sort']['b']
      ck(4.5<=gap<=8.5,f"All States, {tag}: first row ~6px under the sort glyph (half the old 13-15px band)",[gap,m])
      ck(m['backBtn'] is None,f"All States, {tag}: no back chevron",m['backBtn'])
      ref=m['chart'] if on else m['time']
      ck(m['th'] and abs(m['th']['c']-ref['c'])<=1,f"All States, {tag}: first thumbnail centred on the {'chart' if on else 'clock'} button's centre (mirrored)",[m['th'],ref])
      ck(m['th']['t']>=(m['bar']['b'] if on else 114)-0.5,f"All States, {tag}: thumbnail clear of the bar above",[m['th'],m['bar']])
      if not on: await pg.screenshot(path='/workspace/states-pct-1553.png')
    await timeRow(False)
    m=await pg.evaluate(M); ck(m['crumb']=='All States' and not m['noun'],"All States: no duplicate gray noun",m)
    # PA counties: chevron shown, thumbnails keep their place under it
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(7000)
    for on in (False,True):
      await timeRow(on); m=await pg.evaluate(M); tag='time row '+('open' if on else 'closed')
      ck(m['back'] is not None,f"PA, {tag}: back chevron shown",m)
      ref=m['chart'] if on else m['time']; ck(m['th'] and abs(m['th']['t']-round(ref['c']+14.5))<=1.5,f"PA, {tag}: thumbnails keep their pre-1553 place (top = {'chart' if on else 'clock'} centre + 14.5)",[m['th'],ref])
      ck(m['th']['t']>m['back']['b'] and m['row']['t']>m['sort']['b']+3 and m['row']['t']>m['back']['b']+3,f"PA, {tag}: nothing overlaps (chevron, sort glyph, first row, thumbnails)",m)
    await timeRow(False)
    m=await pg.evaluate(M); ck(m['crumb']=='Pennsylvania' and m['noun']=='counties',"PA: 'Pennsylvania' + gray 'counties'",m)
    bub=await pg.evaluate("()=>{const b=document.querySelector('.bub'); const s=getComputedStyle(b); return [s.backgroundColor,s.color,s.borderTopWidth,s.boxShadow!=='none',s.fontWeight]}")
    ck(bub[0]=='rgb(255, 255, 255)' and bub[1]=='rgb(28, 28, 30)' and bub[3] and bub[4]=='500',"label bubbles are white with dark text, border and shadow",bub)
    # Susquehanna County townships
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/^Susquehanna/.test(r.querySelector('b.rn').title)).click()"); await pg.wait_for_timeout(8000)
    m=await pg.evaluate(M); ck(m['crumb'] and m['crumb'].startswith('Susquehanna') and m['noun']=='townships',"Susquehanna: crumb + gray 'townships'",m)
    ck(not (m['noun'] and m['crumb'] and sgl(m['crumb'].split()[-1])==sgl(m['noun'].split()[-1])),"no repeated level word",m)
    box=await pg.evaluate("()=>{const n=[...document.querySelectorAll('#listView .lvrow.la.cmp .nmx')].find(e=>e.scrollWidth>e.clientWidth+1&&e.getBoundingClientRect().top>200&&e.getBoundingClientRect().bottom<700); if(!n) return null; const r=n.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2,n.closest('b.rn').title]}")
    ck(box is not None,"a township name is cut off",box)
    if box:
      await pg.touchscreen.tap(box[0],box[1]); await pg.wait_for_timeout(300)
      bb=await pg.evaluate("()=>{const b=document.querySelector('.bub'); return {h:b.hidden,t:b.textContent}}")
      ck(not bb['h'] and bb['t']==box[2].replace(' (≈ estimate)',''),"township list: tap on a cut-off name shows its full name",[bb,box[2]])
      await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(5000)
      ok=await pg.evaluate("()=>{const n=[...document.querySelectorAll('#listView .lvrow.la.cmp .nmx')].find(e=>e.scrollWidth>e.clientWidth+1&&e.getBoundingClientRect().top>250&&e.getBoundingClientRect().bottom<700); return n?window.__nameBub(n,20000)&&n.closest('b.rn').title:null}")
      await pg.wait_for_timeout(300); await pg.screenshot(path='/workspace/susquehanna-township-bubble-1553.png'); print('screenshot bubble:',ok)
    ck(not er,"no page errors",er[:2])
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
