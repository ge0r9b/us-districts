# usage: python3 tests/glass.py URL -- build 1563 (Liquid Glass, approved preview v3):
# every floating/round button: clear glass + dark 1.5px outline + dark glyph when unselected; darker smoky glass + white outline + white glyph when selected;
# sizes unchanged (48x48); sort chip 31x26 r9 and back-chevron 26px circle centred on their glyphs; shorter sort arrows (~10.2px tall);
# bar lists: name column = longest name + 6px (All States bars start at x=82), 84px cap; in-bar labels fit-or-hide (never partial, % and #);
# thumbnail value badges on top and unclipped; one shared label-bubble style.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:600]); fails+=0 if ok else 1
BT="""()=>[...document.querySelectorAll('.rbtn,#bGeo,#bTime,.xrow .lbtn,#bLyr')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&getComputedStyle(e).visibility!=='hidden'}).map(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect(),s=e.querySelector('svg');return {id:e.id||e.dataset.k||e.dataset.ch||e.className,on:/\\b(on|typed)\\b/.test(e.className),w:Math.round(r.width),h:Math.round(r.height),bg:c.backgroundImage,bw:parseFloat(c.borderTopWidth),bc:c.borderTopColor,st:s?getComputedStyle(s).stroke:'',col:c.color,bf:c.backdropFilter||c.webkitBackdropFilter||'',sh:c.boxShadow}})"""
SORT="""()=>{const b=document.getElementById('laSort'),c=getComputedStyle(b,'::before'),s=b.querySelector('svg');let L=1e9,T=1e9,R=-1e9,B=-1e9;s.querySelectorAll('path').forEach(e=>{const r=e.getBoundingClientRect();L=Math.min(L,r.left);T=Math.min(T,r.top);R=Math.max(R,r.right);B=Math.max(B,r.bottom)});const br=b.getBoundingClientRect();return {chip:[parseFloat(c.width),parseFloat(c.height),c.borderRadius],cx:br.left+parseFloat(c.left)+parseFloat(c.width)/2,cy:br.top+parseFloat(c.top)+parseFloat(c.height)/2,gx:(L+R)/2,gy:(T+B)/2,gh:B-T,gw:R-L,btn:[Math.round(br.width),Math.round(br.height)]}}"""
BACK="""()=>{const b=document.getElementById('bBack'),c=getComputedStyle(b,'::before'),s=b.querySelector('svg').getBoundingClientRect(),br=b.getBoundingClientRect();return {w:parseFloat(c.width),h:parseFloat(c.height),r:c.borderRadius,cx:br.left+parseFloat(c.left)+parseFloat(c.width)/2,cy:br.top+parseFloat(c.top)+parseFloat(c.height)/2,gx:s.left+s.width/2,gy:s.top+s.height/2}}"""
ROWS="""()=>{const rg=document.createRange();const rows=[...document.querySelectorAll('#listView .lvrow.la.cmp')].filter(r=>r.offsetParent);let m=0;const o=rows.slice(0,12).map(r=>{const n=r.querySelector('b.rn .nmx');rg.selectNodeContents(n);const t=rg.getBoundingClientRect();const s=r.querySelector('.sbw').getBoundingClientRect();return {n:n.textContent,nl:t.left,nr:t.right,bar:s.left}});rows.forEach(r=>{const n=r.querySelector('b.rn .nmx');rg.selectNodeContents(n);m=Math.max(m,rg.getBoundingClientRect().width)});return {rows:o,longest:m,rnw:getComputedStyle(document.querySelector('#listView .lvgrid')).getPropertyValue('--rnw')}}"""
PARTIAL="""()=>{let bad=[],shown=0;document.querySelectorAll('#listView .sbw:not(.dl) .sg b').forEach(b=>{if(b.style.visibility==='hidden'||!b.textContent)return;const s=b.parentElement.getBoundingClientRect(),r=b.getBoundingClientRect();if(r.bottom<0||r.top>innerHeight||!s.width)return;shown++;if(r.right>s.right+0.5||r.left<s.left-0.5)bad.push(b.textContent+' '+Math.round(r.right-s.right))});return {bad:bad.slice(0,8),shown}}"""
BADGE="""()=>[...document.querySelectorAll('#laCands .lact .cpt')].filter(e=>e.textContent).map(e=>{const r=e.getBoundingClientRect(),cy=r.top+r.height/2,a=document.elementFromPoint(r.right-1.5,cy),z=document.elementFromPoint(r.left+1.5,cy);return {t:e.textContent,l:r.left,r:r.right,top:[a,z].every(x=>x===e||e.contains(x)||x===e.parentElement) /* the badge (pointer-events:none) is hit-tested as its own thumbnail button: nothing else covers it */,in:r.left>=0&&r.right<=innerWidth}})"""
BUB="""()=>[...document.querySelectorAll('.tlab')].filter(e=>e.getBoundingClientRect().height>0&&getComputedStyle(e).display!=='none').map(e=>{const c=getComputedStyle(e);return [e.textContent,c.fontSize,c.whiteSpace,c.backgroundColor,Math.round(e.getBoundingClientRect().height)]})"""
def glassok(x):
  if x['w']!=48 and x['w']!=44 and x['w']<40: return False
  if x['on']: return '0, 0, 0, 0.88' in x['bg'] and '0, 0, 0, 0.92' in x['bg'] and x['bc'].startswith('rgba(255, 255, 255') and x['st'] in ('rgb(255, 255, 255)','') and x['col']=='rgb(255, 255, 255)' and 1<=x['bw']<=1.5
  return '255, 255, 255, 0.22' in x['bg'] and '255, 255, 255, 0.14' in x['bg'] and 'brightness(1.12)' in x['bf'] and '0px -1px 1px 0px inset' not in x.get('sh','') and x['bc']=='rgba(0, 0, 0, 0.75)' and x['st'] in ('rgb(17, 17, 17)','') and x['col']=='rgb(17, 17, 17)' and 1<=x['bw']<=1.5
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(1200)
    bt=await pg.evaluate(BT); ids={x['id'] for x in bt}
    ck("map: search, filter, time, layers, type buttons, #/%, globe, chart all present",{'bSearch','bGeo','bTime','bLyr','bNum','bGlobe','ushouse','senate'}<=ids,sorted(ids))
    ck("map: every round button has the glass look (clear/dark outline or smoky/white outline), 48px",all(glassok(x) for x in bt),[x for x in bt if not glassok(x)])
    ck("map: selected ones (time, layers, %, globe) are smoky",all(x['on'] for x in bt if x['id'] in ('bTime','bLyr','bNum','bGlobe')),[(x['id'],x['on']) for x in bt])
    ck("map: unselected ones (search, filter, type buttons) are clear",not any(x['on'] for x in bt if x['id'] in ('bSearch','bGeo','ushouse','senate','statehouse','schools')),[(x['id'],x['on']) for x in bt])
    ck("map: glass blurs what is behind it (backdrop-filter)",all('blur' in x['bf'] for x in bt) or all(x['bf'] in ('','none') for x in bt),[x['bf'] for x in bt][:4])
    await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(2500)
    if await pg.evaluate("()=>document.getElementById('lyrRow').hidden"): await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(1200)
    bub=await pg.evaluate(BUB); ck(f"type label: one, shared bubble size (10px, single line), near-black fill (build 1564) {bub}",len(bub)==1 and bub[0][0]=='US House' and bub[0][1]=='10px' and bub[0][2]=='nowrap' and bub[0][3]=='rgba(0, 0, 0, 0.9)',bub)
    await c.close()
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    for nm in ('pct','num'):
      await pg.evaluate("m=>window.__setNum(m)",nm); await pg.wait_for_timeout(2200)
      s=await pg.evaluate(SORT)
      ck(f"All States {nm}: sort chip 31x26 r9, centred on the glyph",abs(s['chip'][0]-31)<=1 and s['chip'][1]==26 and s['chip'][2]=='9px' and abs(s['cx']-s['gx'])<=1 and abs(s['cy']-s['gy'])<=1,s)
      ck(f"All States {nm}: shorter sort arrows (glyph {s['gh']:.1f}px tall, {s['gw']:.1f}px wide), 34x22 tap target",9.5<=s['gh']<=10.8 and abs(s['gw']-16.5)<=0.6 and s['btn']==[34,22],s)
      r=await pg.evaluate(ROWS); xs={round(x['bar']) for x in r['rows']}
      ck(f"All States {nm}: name column = longest name ({r['longest']:.1f}px -> {r['rnw']}), bars start 6px after it (x={sorted(xs)})",len(xs)==1 and abs(min(xs)-(52+r['longest']+6))<=1.5 and min(xs)<=84,r)
      pa=await pg.evaluate(PARTIAL); ck(f"All States {nm}: in-bar labels fit-or-hide, none partial ({pa['shown']} shown)",not pa['bad'] and pa['shown']>5,pa)
      bd=await pg.evaluate(BADGE); ck(f"All States {nm}: thumbnail badges on top and unclipped ({[x['t'] for x in bd]})",bd and all(x['top'] and x['in'] for x in bd),bd)
      bars=min(xs); ck(f"All States {nm}: bars clear of the badges",all(x['r']<bars for x in bd),[bars,bd])
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
    chip=await pg.evaluate("()=>['laSort','bBack'].map(id=>{const e=document.getElementById(id); if(!e) return null; const c=getComputedStyle(e,'::before'); return [id,c.backgroundImage,c.backdropFilter||c.webkitBackdropFilter,c.boxShadow]}).filter(Boolean)")
    ck("sort chip (and back chevron if shown): whiter, more transparent glass .22->.14 + brightness(1.12), no dark bottom inner shadow",chip and all('255, 255, 255, 0.22' in x[1] and '255, 255, 255, 0.14' in x[1] and 'brightness(1.12)' in x[2] and 'rgba(0, 0, 0, 0.07) 0px -1px' not in x[3] for x in chip),chip)
    # build 1564: selected = near-black in the right column and in the menus that open from it (time row, chart options)
    if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
    await pg.evaluate("()=>{const m=document.querySelector('button.rbtn.cmain'); if(m) m.click()}"); await pg.wait_for_timeout(900)
    bt=await pg.evaluate(BT); on=[x for x in bt if x['on']]
    ck(f"list + chart menu open: {len(on)} selected buttons near-black rgba(0,0,0,.88->.92), white outline + glyph; unselected clear",len(on)>=2 and {'bTime','bNum'}<=set(x['id'] for x in on) and all(glassok(x) for x in bt) and await pg.evaluate("()=>[...document.querySelectorAll('.rbtn[data-ch]')].some(b=>!b.classList.contains('cmain')&&b.getBoundingClientRect().width>40)"),[x for x in bt if not glassok(x)] or [x['id'] for x in on])
    if len(sys.argv)>2:
      await pg.screenshot(path=sys.argv[2],clip={'x':390-150,'y':0,'width':150,'height':844})
    await pg.evaluate("()=>{const m=document.querySelector('button.rbtn.cmain'); const w=m&&m.closest('.open'); if(w) document.body.click()}"); await pg.wait_for_timeout(600)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(7000)
    k=await pg.evaluate(BACK); ck("PA counties: back chevron glass is a 26px circle centred on the chevron",k['w']==26 and k['h']==26 and k['r']=='50%' and abs(k['cx']-k['gx'])<=1.5 and abs(k['cy']-k['gy'])<=1.5,k)
    s=await pg.evaluate(SORT); ck("PA counties: sort chip on the chevron's centre line",abs(s['cy']-k['cy'])<=1,[s['cy'],k['cy']])
    r=await pg.evaluate(ROWS); xs={round(x['bar']) for x in r['rows']}; ck(f"PA counties: long names cap the column at 84px (bars at x={sorted(xs)})",r['rnw'].strip()=='84px' and len(xs)==1 and abs(min(xs)-142)<=1.5,r)
    pa=await pg.evaluate(PARTIAL); ck("PA counties: no partial labels",not pa['bad'],pa)
    ck("no page errors",not errs,errs); await c.close(); await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
