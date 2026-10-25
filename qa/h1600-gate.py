# 1620 audit: app's gated precRowsIn vs the old centroid membership precRowsIn0, per town: lost/gained rows, emptied towns, double-assigned rows
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
JS="""async (st)=>{ await loadState(st); await loadPrecincts(st); await window.__loadParts(st); const rows=PREC[st]||[];
 const inRing=(x,y,R)=>{let c=false;for(let i=0,j=R.length-1;i<R.length;j=i++){const [xi,yi]=R[i],[xj,yj]=R[j];if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))c=!c;}return c;};
 const inPolys=(P,x,y)=>{ if(!P) return false; for(const rings of P){ if(!rings||!rings[0]) continue; if(inRing(x,y,rings[0])){ let h=false; for(let k=1;k<rings.length;k++) if(inRing(x,y,rings[k])) h=true; if(!h) return true; } } return false; };
 const cen=r=>{ if(r.__qc) return r.__qc; let A=0,cx=0,cy=0; for(const rings of r[5]){ const R=rings[0]; for(let i=0,j=R.length-1;i<R.length;j=i++){const f=R[j][0]*R[i][1]-R[i][0]*R[j][1];A+=f;cx+=(R[j][0]+R[i][0])*f;cy+=(R[j][1]+R[i][1])*f;} } let c=A?[cx/(3*A),cy/(3*A)]:[(r[6][0]+r[6][2])/2,(r[6][1]+r[6][3])/2]; if(!inPolys(r[5],c[0],c[1])) c=[(r[6][0]+r[6][2])/2,(r[6][1]+r[6][3])/2]; return r.__qc=c; };
 const geo0=(d,cn)=>rows.filter(r=>r[0]===cn&&(()=>{const [x,y]=cen(r);return inPolys(d[3],x,y)})());
 const tv=r=>{const t=r[4]; if(typeof t==='number') return t; if(Array.isArray(t)) return t.reduce((a,b)=>a+(+b||0),0); if(t&&typeof t==='object') return Object.values(t).reduce((a,b)=>a+(+b||0),0); return 0;};
 const out={st,nprec:rows.length,towns:0,changed:[],emptied:[],dups:[]};
 const cs=[...new Set(rows.map(r=>r[0]))];
 for(const cn of cs){ let T=[]; try{T=window.__townsIn(st,cn)||[];}catch(e){continue;} if(!T.length) continue; out.towns+=T.length; const seen=new Map();
  for(const d of T){ const a=window.__pri(d,rows,cn), o=geo0(d,cn); a.forEach(r=>{ if(!seen.has(r)) seen.set(r,[]); seen.get(r).push(d[2]); });
   const sa=new Set(a), so=new Set(o); const lost=o.filter(r=>!sa.has(r)), gain=a.filter(r=>!so.has(r));
   if(lost.length||gain.length) out.changed.push({c:cn,t:d[2],old:o.length,now:a.length,oldv:o.reduce((s,r)=>s+tv(r),0),nowv:a.reduce((s,r)=>s+tv(r),0),lost:lost.map(r=>String(r[1])).slice(0,8),gain:gain.map(r=>String(r[1])).slice(0,8)});
   if(o.length&&!a.length) out.emptied.push(cn+' / '+d[2]); }
  for(const [r,ts] of seen) if(ts.length>1) out.dups.push({c:cn,p:String(r[1]),towns:ts}); }
 return out; }"""
async def main():
  res=[]
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(3000)
    for st in sys.argv[1].split(','):
      try: r=await pg.evaluate(JS,st)
      except Exception as e: r={'st':st,'err':str(e)[:300]}
      print(st,r.get('nprec'),r.get('towns'),'changed',len(r.get('changed',[])),'emptied',len(r.get('emptied',[])),'dups',len(r.get('dups',[])),r.get('err',''),flush=True); res.append(r)
    json.dump(res,open('b1620h1600-gate-%s.json'%sys.argv[2],'w'),indent=0); await b.close()
asyncio.run(main())
