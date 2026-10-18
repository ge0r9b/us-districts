# SUPERSEDED in build 1588 (user): with every answer shown the sort is by TOTAL votes; see tests/list-sort-total.py. Kept for its alignment/crumb checks.
# Build 1551: every results list (% and # mode) sorts high→low by the TOP-RANKED TOGGLED-ON answer of the left thumbnail
# column (its share in %, its votes in #); toggles / re-ranking re-sort and reset the direction to high→low; 3+ answers;
# chart-row alignment: names start at the top fields' text x, normal weight, no ' County'; bars end 12px from the edge;
# the org crumb names the listed level ('Pennsylvania' + mid-gray 'counties', not part of its textContent);
# name column 84px: a cut-off name ends in an ellipsis and a tap on it shows the full name in a bubble (the row tap still works).
# Build 1560: bubbles show only on tap (no hover / long-press); the tap also drills in, so the bubble goes after 2 s.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
ROWS="""()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>{const w={};r.querySelectorAll('.sbw .sg').forEach(s=>{const k=s.className.replace('sg ','').trim(); w[k]=parseFloat(s.style.width)||0}); const b=r.querySelector('.sbw'); return {n:r.querySelector('.nmx').textContent,t:r.querySelector('b.rn').title,w,bw:b?b.getBoundingClientRect().width:0}})"""
def mono(xs,desc=True,tol=0.051): return all((a>=b-tol) if desc else (a<=b+tol) for a,b in zip(xs,xs[1:]))
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page()
    er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    async def info(): return await pg.evaluate("()=>window.__laInfo()")
    async def settle(ms=1500): await pg.wait_for_timeout(ms)
    # ---- state list ----
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await settle()
    await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await settle(5000)
    await pg.evaluate("()=>window.__setNum('pct')"); await settle()
    i=await info(); r=await pg.evaluate(ROWS)
    ck(i['lv']=='states' and i['sort']=='desc' and i['sc']=='t24',"state list: default high→low, key = top thumbnail (Trump)",{k:i[k] for k in ('lv','sort','sc')})
    rs=[x['w'].get('rep',0) for x in r]; ck(mono(rs) and r[0]['n']=='WY',"state list %: sorted by Trump's share, WY first",[x['n'] for x in r[:3]]+rs[:3])
    await pg.evaluate("()=>window.__setNum('num')"); await settle(); r=await pg.evaluate(ROWS)
    rv=[x['bw']*x['w'].get('rep',0)/100 for x in r]; ck(mono(rv,tol=1.5) and r[0]['n']=='TX',"state list #: sorted by Trump's votes, TX first (not CA = most votes cast)",[x['n'] for x in r[:3]])
    # 3+ answers: a third answer that ranks first (value key = all votes) leads the sort, then off -> back to Trump
    await pg.evaluate("()=>{ __CANDS['2024'].push({id:'x24',k:'tot',yr:'2024',answerId:'x',candidateId:'x',color:'#16a34a',col:'#16a34a',short:'All',full:'All votes test',ini:'AV',p:'x'}); __candOn.add('x24'); }"); await settle(2000)
    i=await info(); r=await pg.evaluate(ROWS); th=await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.dataset.cid)")
    ck(th[:1]==['x24'] and i['sc']=='x24' and r[0]['n']=='CA',"3 answers: top-ranked third answer leads the sort (# = its votes, CA first)",[th,i['sc'],[x['n'] for x in r[:3]]])
    await pg.evaluate("()=>document.querySelector('#laCands .lact[data-cid=x24]').click()"); await settle(2000)
    i=await info(); r=await pg.evaluate(ROWS)
    ck(i['sc']=='t24' and r[0]['n']=='TX',"3 answers: top one toggled off -> next toggled-on (Trump) is the key",[i['sc'],[x['n'] for x in r[:3]]])
    await pg.evaluate("()=>{ __CANDS['2024'].pop(); __candOn.delete('x24'); }"); await settle(1500)
    # ---- PA county list ----
    await pg.evaluate("()=>window.__setNum('pct')"); await settle()
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await settle(7000)
    i=await info(); r=await pg.evaluate(ROWS)
    ck(i['lv']=='counties' and len(r)==67,"PA: 67 county rows",[i['lv'],len(r)])
    rs=[x['w'].get('rep',0) for x in r]; names=[x['n'] for x in r]
    ck(i['sort']=='desc' and i['sc']=='t24' and mono(rs) and names[0]=='Fulton' and names[-1]=='Philadelphia',"PA %: high→low by Trump's share (Fulton first, Philadelphia last)",[i['sort'],i['sc'],names[:3],names[-3:]])
    ck(all(not x['n'].endswith(' County') for x in r) and r[0]['t'].startswith('Fulton County'),"chart rows drop ' County'; the title keeps the full name",[r[0]['n'],r[0]['t']])
    al=await pg.evaluate("""()=>{const rg=e=>{const x=document.createRange(); x.selectNodeContents(e); return x.getBoundingClientRect();}; const r=document.querySelector('#listView .lvrow.la.cmp'); const nm=r.querySelector('.nmx'); const sb=r.querySelector('.sbw').getBoundingClientRect(); const th=[...document.querySelectorAll('#laCands .lact')].map(b=>b.getBoundingClientRect().right); const cr=[...document.querySelectorAll('#crumbs .crumb.cur')].pop(); return {name:rg(nm).left,title:rg(document.getElementById('vtitle')).left,crumb:rg(cr.firstChild).left,bar:sb.right,iw:innerWidth,thR:Math.max(...th),fw:getComputedStyle(nm).fontWeight,oic:getComputedStyle(r.querySelector('.oic')).display,noun:cr.getAttribute('data-noun'),ctext:cr.textContent,after:getComputedStyle(cr,'::after').content,acol:getComputedStyle(cr,'::after').color}}""")
    ck(abs(al['name']-al['title'])<=1 and abs(al['name']-al['crumb'])<=1 and al['name']>al['thR'],"row names start at the top fields' text x and clear the thumbnail column",al)
    ck(abs(al['bar']-(al['iw']-12))<=1,"bars end 12px short of the screen edge",al)
    ck(al['fw']=='400' and al['oic']=='none',"chart-row names in normal weight, no per-row icon",al)
    ck(al['noun']=='counties' and al['ctext']=='Pennsylvania' and 'counties' in al['after'] and al['acol']=='rgb(142, 142, 147)',"org crumb: 'Pennsylvania' + mid-gray 'counties' (not in textContent)",al)
    await pg.screenshot(path='/workspace/pa-counties-pct-1551.png')
    await pg.evaluate("()=>window.__setNum('num')"); await settle(); r=await pg.evaluate(ROWS); i=await info()
    rv=[x['bw']*x['w'].get('rep',0)/100 for x in r]; ck(i['sort']=='desc' and mono(rv,tol=1.5),"PA #: high→low by Trump's votes",[x['n'] for x in r[:4]])
    # flip, then a toggle change re-sorts and resets to high->low
    await pg.evaluate("()=>window.__setNum('pct')"); await settle()
    await pg.evaluate("()=>document.getElementById('laSort').click()"); await settle(); i=await info(); r=await pg.evaluate(ROWS)
    ck(i['sort']=='asc' and r[0]['n']=='Philadelphia',"sort arrow flips to low→high (Philadelphia first)",[i['sort'],r[0]['n']])
    await pg.evaluate("()=>document.querySelector('#laCands .lact[data-cid=t24]').click()"); await settle(2000); i=await info(); r=await pg.evaluate(ROWS)
    hs=[x['w'].get('dem',0) for x in r]
    ck(i['sort']=='desc' and i['sc']=='h24' and r[0]['n']=='Philadelphia' and mono(hs),"Trump off: key = Harris, reset to high→low (Philadelphia first)",[i['sort'],i['sc'],[x['n'] for x in r[:3]]])
    await pg.evaluate("()=>document.querySelector('#laCands .lact[data-cid=t24]').click()"); await settle(2000); i=await info(); r=await pg.evaluate(ROWS)
    ck(i['sc']=='t24' and r[0]['n']=='Fulton',"Trump back on: key = Trump again (Fulton first)",[i['sc'],r[0]['n']])
    # no topic: plain place list keeps full names
    await pg.evaluate("()=>{ window.__topic0=document.getElementById('vtitle').textContent; }"); await pg.evaluate("()=>window.__setTopic&&window.__setTopic(null)"); await settle(3000); r=await pg.evaluate(ROWS)
    ck(r and any(x['n'].endswith(' County') for x in r),"no topic: plain list keeps the full names",[x['n'] for x in r[:3]])
    # name column 84px, ellipsis + bubble (back to a topic, PA counties)
    await pg.evaluate("()=>window.__setTopic&&window.__setTopic(window.__topic0)"); await settle(3000)
    tr=await pg.evaluate("""()=>{const rs=[...document.querySelectorAll('#listView .lvrow.la.cmp')]; const o=rs.map(r=>{const n=r.querySelector('.nmx'); return {n:n.textContent,t:r.querySelector('b.rn').title,cut:n.scrollWidth>n.clientWidth+1,w:r.querySelector('b.rn').getBoundingClientRect().width,to:getComputedStyle(n).textOverflow}}); return {rows:o.length,w:o[0]&&o[0].w,cut:o.filter(x=>x.cut).map(x=>x.n),to:o[0]&&o[0].to,uncut:!window.__nameBub(rs.find(r=>{const n=r.querySelector('.nmx'); return n.scrollWidth<=n.clientWidth}).querySelector('.nmx')), bubHidden:document.querySelector('.bub').hidden}}""")
    ck(tr['rows']>=60 and abs(tr['w']-84)<=0.5 and tr['to']=='ellipsis',"name column 84px wide, overflow shows an ellipsis",tr)
    ck(len(tr['cut'])>=1,"at least one PA county name is cut off at 84px (e.g. Northumberland)",tr['cut'])
    ck(tr['uncut'] and tr['bubHidden'],"a name that fits: no bubble",tr)
    if tr['cut']:
      lv0=await info(); nm=tr['cut'][0]
      box=await pg.evaluate("(nm)=>{const n=[...document.querySelectorAll('#listView .lvrow.la.cmp .nmx')].find(e=>e.textContent===nm); n.scrollIntoView({block:'center'}); const r=n.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}",nm)
      await pg.wait_for_timeout(500); box=await pg.evaluate("(nm)=>{const n=[...document.querySelectorAll('#listView .lvrow.la.cmp .nmx')].find(e=>e.textContent===nm); const r=n.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}",nm)
      await pg.touchscreen.tap(box[0],box[1]); await pg.wait_for_timeout(250)
      bb=await pg.evaluate("()=>{const b=document.querySelector('.bub'); const r=b.getBoundingClientRect(); return {hidden:b.hidden,text:b.textContent,top:r.top,bottom:r.bottom}}")
      ck(not bb['hidden'] and bb['text']==nm+' County' and bb['bottom']<=box[1],"tap on a cut-off name: bubble with the full name above it",[nm,bb])
      await pg.screenshot(path='/workspace/pa-counties-namebubble-1551.png')
      await pg.wait_for_timeout(1300); bv=await pg.evaluate("()=>{const b=document.querySelector('.bub'); return !b.hidden&&!b.classList.contains('fade')}")
      ck(bv,"name bubble still up ~1.5s after the tap (build 1560)",bv)
      await pg.wait_for_timeout(1000); bv=await pg.evaluate("()=>{const b=document.querySelector('.bub'); return b.hidden}")
      ck(bv,"name bubble gone ~2.5s after the tap: the tap also drilled in, so it goes after 2 s (build 1560)",bv)
      # build 1560: bubbles only on tap -- no hover / long-press bubble
      await settle(1500); lv1=await info()
      ck((lv1['lv'],lv1['order'][:1])!=(lv0['lv'],lv0['order'][:1]),"the tap still reaches the row (opens that county as before)",[lv0['lv'],lv1['lv']])
    ck(not er,"no page errors",er[:2])
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
