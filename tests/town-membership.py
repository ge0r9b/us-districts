# QA-119/121/124/126: a town's precinct list holds only its own precincts; a precinct named for another town of the same county is listed (and counted) under that town. Chromium + WebKit.
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
J="""async([st,co,tn,bad,own])=>{ await loadState(st); await loadPrecincts(st); await __loadParts(st); const T=__townsIn(st,co)||[]; const t=T.find(d=>d[2]===tn), o=T.find(d=>d[2]===own);
 const nm=d=>d?__pri(d,PREC[st],co).map(r=>r[1]):null; return {host:nm(t), own:nm(o), towns:T.length}; }"""
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
      ck(not er,f"{eng}: no page errors",er); await b.close()
  print("FAILED:",F) if F else print("ALL OK"); sys.exit(1 if F else 0)
asyncio.run(main())
