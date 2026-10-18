import asyncio,sys,json,time
from playwright.async_api import async_playwright
from common import *
LAYOUT="""()=>{const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'&&r.bottom>0&&r.top<innerHeight};
 const btns=[...document.querySelectorAll('.rbtn,#laSort,#bBack')].filter(vis).map(b=>[b,b.getBoundingClientRect()]);
 const leaves=[...document.querySelectorAll('body *')].filter(e=>e.childElementCount===0&&e.textContent.trim()&&vis(e)&&!e.closest('.leaflet-tile-pane,.leaflet-control-attribution'));
 const over=[],clip=[],off=[];
 for(const e of leaves){const r=e.getBoundingClientRect();const t=e.textContent.trim().slice(0,25);
  for(const [b,q] of btns){ if(b.contains(e)||e.contains(b)) continue; const ix=Math.min(r.right,q.right)-Math.max(r.left,q.left), iy=Math.min(r.bottom,q.bottom)-Math.max(r.top,q.top); if(ix>3&&iy>3){ if(getComputedStyle(e).opacity!=='0') over.push(t+' x '+(b.id||b.getAttribute('aria-label')||b.className))} }
  if(r.right>innerWidth+1||r.left<-1) off.push(t+' '+Math.round(r.left)+'..'+Math.round(r.right));
  const cs=getComputedStyle(e); if(e.scrollWidth>e.clientWidth+1&&cs.overflow!=='visible'&&cs.textOverflow!=='ellipsis') clip.push(t+' '+e.scrollWidth+'>'+e.clientWidth);
 }
 return {over:[...new Set(over)].slice(0,12),clip:[...new Set(clip)].slice(0,12),off:[...new Set(off)].slice(0,12)}}"""
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,8).map(r=>r.innerText.replace(/\\n/g,' | '))"
async def main():
  eng=sys.argv[1]; which=sys.argv[2:] 
  res={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in VPS:
      if which and tag not in which: continue
      c,pg,log=await ctx(b,W,H,mob,eng); R={'lat':{},'layout':{},'notes':[],'t':{}}
      async def shot(n): await pg.screenshot(path=f"../shots/b1585p18-{eng[:2]}-{tag.replace("iphone","").replace("ipad","")}-{n.split("-",1)[1]}.png")
      async def tap(sel,name,wait=1500):
        xy=await center(pg,sel)
        if not xy: R['notes'].append(f'{name}: {sel} not visible'); return False
        R['t'][name]=await pg.evaluate('()=>Math.round(performance.now())'); R['lat'][name]=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return True
      async def lay(n): R['layout'][n]=await pg.evaluate(LAYOUT)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await lay('map')
      # institution filter -> All States list
      await tap('#bGeo','open_institution'); await shot('01-institution-menu'); await lay('inst_menu')
      await tap('li.la-row','list_all_states',5000); await shot('02-allstates-list'); await lay('allstates')
      R['rows_default']=await pg.evaluate(ROWS)
      R['sortinfo']=await pg.evaluate("()=>window.__laInfo&&JSON.stringify(window.__laInfo()).slice(0,300)")
      await tap('#laSort','sort_flip',1200); R['rows_flipped']=await pg.evaluate(ROWS); await shot('03-sort-flipped')
      await tap('#laSort','sort_flip_back',2200)
      await tap('#bNum','num_toggle',1500); await shot('04-num-toggle-open')
      R['num_after_tap']=await pg.evaluate("()=>window.__numMode()")
      # if it opened an option chooser, pick '#'
      opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
      if opt: R['lat']['num_pick']=await tap_latency(pg,*opt); await pg.wait_for_timeout(2000)
      R['num_mode']=await pg.evaluate("()=>window.__numMode()"); R['rows_num']=await pg.evaluate(ROWS); await shot('05-allstates-num'); await lay('allstates_num')
      # time
      await tap('#bTime','time_open',1200); await shot('06-time-row')
      R['time']=await pg.evaluate("()=>{const s=document.getElementById('yslider');return s?{min:s.min,max:s.max,v:s.value,hidden:document.getElementById('barTime').hidden}:null}")
      await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.min;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(3000); R['ymode_2020']=await pg.evaluate("()=>window.__ymode&&window.__ymode()"); R['rows_2020']=await pg.evaluate(ROWS); await shot('07-allstates-2020')
      await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(3000)
      R['ymode_range']=await pg.evaluate("()=>window.__ymode&&window.__ymode()"); R['rows_delta']=await pg.evaluate(ROWS); await shot('08-allstates-delta'); await lay('delta')
      # chart menu
      await tap('#chartBox .cmain','chart_menu',900); R['chart_opts']=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)"); await shot('09-chart-menu-range')
      for k in list(R['chart_opts']):
        if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain','chart_menu_re',900)
        if await tap(f'#chartBox .copts button[data-ch={k}]',f'chart_{k}',2500): await shot(f'10-chart-{k}-range'); await lay(f'chart_{k}_range')
        R.setdefault('chart_mode',[]).append((k,await pg.evaluate("()=>window.chartMode")))
      # back to single year 2024 -> pie
      await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(3000); R['ymode_single']=await pg.evaluate("()=>window.__ymode&&window.__ymode()")
      await tap('#chartBox .cmain','chart_menu_single',900); R['chart_opts_single']=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)")
      if 'pie' in R['chart_opts_single']:
        await tap('#chartBox .copts button[data-ch=pie]','chart_pie',2500); await shot('11-chart-pie-single'); await lay('chart_pie')
      R['chart_now']=await pg.evaluate("()=>window.chartMode")
      # drill-in PA
      xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
      await pg.wait_for_timeout(600)
      if xy: R['lat']['drill_PA']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000); await shot('12-drill-PA-counties'); await lay('PA_counties')
      R['PA_rows']=await pg.evaluate(ROWS); R['PA_info']=await pg.evaluate("()=>window.__laInfo&&JSON.stringify(window.__laInfo()).slice(0,200)")
      xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent)[0];if(!r)return null;const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
      if xy: R['lat']['drill_county']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); await shot('13-drill-county'); await lay('county_level')
      R['county_rows']=await pg.evaluate(ROWS); R['county_info']=await pg.evaluate("()=>window.__laInfo&&JSON.stringify(window.__laInfo()).slice(0,200)")
      xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent)[0];if(!r)return null;const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
      if xy: R['lat']['drill_town']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); await shot('14-drill-town'); await lay('town_level')
      R['town_rows']=await pg.evaluate(ROWS); R['town_info']=await pg.evaluate("()=>window.__laInfo&&JSON.stringify(window.__laInfo()).slice(0,200)")
      # back
      await tap('#bBack','back',3000); R['after_back']=await pg.evaluate("()=>window.__laInfo&&JSON.stringify(window.__laInfo()).slice(0,200)")
      # district type
      await tap('#bLyr','type_menu',1200); await shot('15-type-menu')
      await tap('#lyrRow .lbtn[data-k=ushouse]','type_ushouse',4000); await shot('16-type-ushouse'); await lay('ushouse')
      R['ushouse_rows']=await pg.evaluate(ROWS)
      await tap('#lyrRow .lbtn[data-k=ushouse]','type_deselect',3000)
      await pg.mouse.click(5,H//2) if False else None
      # reload + restore
      snap=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot()).slice(0,300)")
      await pg.wait_for_timeout(1500); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(8000)
      snap2=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot()).slice(0,300)"); R['restore']=(snap,snap2,snap==snap2); await shot('17-after-reload')
      # address search via geo field
      await pg.evaluate("()=>{const g=document.getElementById('gq');g.focus();}"); await pg.wait_for_timeout(500)
      await pg.keyboard.type("1600 Pennsylvania Ave NW, Washington, DC 20500",delay=20); await pg.wait_for_timeout(2500); await shot('18-addr-typing')
      R['addr_sugg']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.textContent.trim().slice(0,60)).slice(0,6)")
      await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000); await shot('19-addr-result')
      R['addr_result']=await pg.evaluate("()=>({ph:document.getElementById('gq').placeholder,val:document.getElementById('gq').value,st:window.state&&state.value,co:window.county&&county.value,pop:[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.slice(0,150))})")
      R['cls']=await pg.evaluate("()=>window.__cls"); R['shifts']=await pg.evaluate("()=>window.__shifts.slice(0,10)")
      R.update(log); res[tag]=R; await c.close()
      print(tag,'done',flush=True)
    await b.close()
  json.dump(res,open(f'b1585p18-flow-{eng}-'+'_'.join(which)+'.json','w'),indent=1)
if __name__=="__main__": asyncio.run(main())
