# QA-119/121/124/126 (+QA-128 regression: no town that had rows on 1618 is emptied; same-stem towns never trade precincts; Ohio unchanged): a town's precinct list holds only its own precincts; a precinct named for another town of the same county is listed (and counted) under that town. Chromium + WebKit.
import asyncio,sys,os,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
# (state, county, town, must-not-contain prefix, owner town that must contain it)
CASES=[("Vermont","Chittenden County","Burlington city","SOUTH BURLINGTON","South Burlington city"),
 ("Rhode Island","Kent County","Warwick city","003-West Warwick","West Warwick town"),
 ("Massachusetts","Hampden County","Chicopee city","Holyoke","Holyoke city"),
 ("Pennsylvania","Montgomery County","Pottstown borough","West Pottsgrove","West Pottsgrove township"),
 ("Michigan","Kalamazoo County","Kalamazoo city","Oshtemo","Oshtemo charter township")]
# QA-128: same-stem pairs and layered townships keep their 1618 rows (not empty, nothing moved)
KEEP=[("New Jersey","Camden County","Gloucester City city"),("New Jersey","Camden County","Gloucester township"),("Michigan","Alpena County","Alpena city"),("Michigan","Alpena County","Alpena township"),("Michigan","Oakland County","Royal Oak city"),("Michigan","Oakland County","Royal Oak charter township"),("Pennsylvania","Bucks County","Bristol township"),("Pennsylvania","Bucks County","Bristol borough"),("Vermont","Washington County","Barre town"),("Vermont","Washington County","Barre city"),("Illinois","Cook County","Skokie village"),("Pennsylvania","Allegheny County","Baldwin township"),("Ohio","Franklin County","Franklin township")]
JK="""async([st,co,tn])=>{ await loadState(st); await loadPrecincts(st); await __loadParts(st); const t=(__townsIn(st,co)||[]).find(d=>d[2]===tn); if(!t) return null; const a=__pri0(t,PREC[st],co), b=__pri(t,PREC[st],co); return [a.length,b.length,a.filter(r=>!b.includes(r)).map(r=>r[1])]; }"""
J="""async([st,co,tn,bad,own])=>{ await loadState(st); await loadPrecincts(st); await __loadParts(st); const T=__townsIn(st,co)||[]; const t=T.find(d=>d[2]===tn), o=T.find(d=>d[2]===own);
 const nm=d=>d?__pri(d,PREC[st],co).map(r=>r[1]):null; return {host:nm(t), own:nm(o), towns:T.length}; }"""
AUD="""async(st)=>{ await loadState(st); await loadPrecincts(st); await __loadParts(st); const P=PREC[st]||[]; const o={n:0,chg:0,ne:[]}; for(const c of [...new Set(P.map(r=>r[0]))]) for(const t of (__townsIn(st,c)||[])){ o.n++; const a=__pri0(t,P,c), b=__pri(t,P,c); if(a.length&&!b.length) o.ne.push(c+'|'+t[2]); if(a.length!==b.length) o.chg++; } return o; }"""
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch(); pg=await b.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      for st,co,tn,bad,own in CASES:
        r=await pg.evaluate(J,[st,co,tn,bad,own])
        if r['host'] is None: ck(False,f"{eng} {tn}: town exists",r); continue
        ck(len(r['host'])>0,f"{eng} {tn}: has its own precincts",r)
        ck(not any(n.lower().startswith(bad.lower()) for n in r['host']),f"{eng} {tn}: no '{bad}' rows",r['host'])
        if r['own'] is not None: ck(any(n.lower().startswith(bad.lower()) for n in r['own']),f"{eng} {own}: holds its '{bad}' rows",r['own'])
      for st,co,tn in KEEP:
        r=await pg.evaluate(JK,[st,co,tn])
        if r is None: print(f"skip {eng} {tn}: not a town here"); continue
        stem=tn.split()[0].lower(); ck(r[1]>0 and not any(stem in n.lower() for n in r[2]),f"{eng} {tn}: keeps its 1618 rows (1618 {r[0]}, now {r[1]}, moved out {r[2]})",r)
      if eng=='chromium' or os.environ.get('FULL'):
        for st in (await pg.evaluate("()=>Object.keys(STATE_FILES).sort()")):
          r=await pg.evaluate(AUD,st); ck(not r['ne'],f"{eng} {st}: no town emptied vs 1618 ({r['n']} towns, {r['chg']} changed)",r['ne'][:8])
          if st=='Ohio': ck(r['chg']==0,f"{eng} Ohio: 1618 assignment unchanged",r)
      ck(not er,f"{eng}: no page errors",er); await b.close()
  print("FAILED:",F) if F else print("ALL OK"); sys.exit(1 if F else 0)
asyncio.run(main())
