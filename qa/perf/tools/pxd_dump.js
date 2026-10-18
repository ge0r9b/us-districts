// run in the page after the state's precincts + state file are loaded: emits the build-time table for state.value, 2024 (what the build script would compute)
(()=>{ const {AGG,aggFor,grid,gq,pointInItem}=window.__aggDbg(); const st=state.value, yr="2024", out={}; out[yr]={};
 for(const k of ["ushouse","senate","statehouse"]){ AGG[st+"|"+k+"|"+yr]=undefined; delete AGG[st+"|"+k+"|"+yr];
  const res=aggFor(k,yr); if(!res) continue; const dists=[...res.keys()]; const P=PREC[st];
  const DG=grid(dists,d=>d.__bb,0.1);
  const a=P.map(r=>{ const [x,y]=r.__c; const i=gq(DG,x,y).find(d=>x>=d.__bb[0]&&x<=d.__bb[2]&&y>=d.__bb[1]&&y<=d.__bb[3]&&pointInItem(d,x,y)); return i?dists.indexOf(i).toString(36):"."; });
  out[yr][k]={n:dists.map(d=>d[1]),a:a.join(","),cov:dists.map(d=>+res.get(d).cov.toFixed(4))}; }
 return '__pxd('+JSON.stringify(st)+','+JSON.stringify(out)+');'; })()
