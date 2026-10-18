/* perf F: build-time precinct->district table. data/pxd/<State>.js (emitted by the build script) calls
   __pxd(state, {"2024":{ushouse:{n:[district names in GEOM order], a:"<per-precinct index into n, base36, '.'=none, comma-joined>", cov:[coverage per n]}, senate:{...}, statehouse:{...}}, "2020":{...}})
   aggFor then sums votes by lookup (no point-in-polygon in the tap). Missing table -> the original geometric path. */
window.__PXD={}; window.__pxd=(st,t)=>{ window.__PXD[st]=t; };
const PXDL={}; function loadPXD(st){ if(!st) return Promise.resolve(); return PXDL[st]||(PXDL[st]=new Promise(r=>{ const s=document.createElement("script"); s.src="data/pxd/"+st.replace(/ /g,"_")+".js?v="+window.BUILD; s.onload=r; s.onerror=r; document.head.append(s); })); }
function aggFromTable(k,yr,st,P){ const T=window.__PXD[st]&&window.__PXD[st][yr]&&window.__PXD[st][yr][k]; if(!T||!P) return null;
  const dists=(GEOM[k]||[]).filter(d=>d[0]===st); const by=new Map(dists.map(d=>[String(d[1]),d])); const res=new Map(); dists.forEach(d=>res.set(d,{dem:0,rep:0,tot:0,n:0}));
  const ND=T.n.map(n=>by.get(String(n))); if(ND.some(d=>!d)) return null; const a=T.a.split(","); if(a.length!==P.length) return null;
  for(let i=0;i<P.length;i++){ const v=a[i]; if(v==="."||v==="") continue; const d=ND[parseInt(v,36)], r=P[i], q=res.get(d); q.dem+=r[2]; q.rep+=r[3]; q.tot+=r[4]; q.n++; }
  ND.forEach((d,i)=>res.get(d).cov=T.cov[i]); return res; }
{ const _af=aggFor; aggFor=function(k,yr){ const y=yr||(ym()==="2020"?"2020":"2024"), st=state.value, key=st+"|"+k+"|"+y; if(AGG[key]) return AGG[key];
    const P=y==="2020"?(window.PREC20||{})[st]:PREC[st]; const r=aggFromTable(k,y,st,P); if(r) return AGG[key]=r; return _af(k,yr); }; }
{ const _lpf=loadPrecincts; loadPrecincts=function(st){ return Promise.all([_lpf(st),loadPXD(st)]).then(()=>undefined); }; }
