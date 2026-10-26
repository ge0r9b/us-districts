# Build 1572: geo merge. towns + places read from v2/data/parts/ + places/ (states/ for counties, schools, districts), no ../data/ request,
# suffix-aware town dedupe (identical full names or TOWN_PAIRS "same" only), Ohio Union County's two Washington townships,
# county school lists from the v2 school layer (Oklahoma's 509), PACK.lists sync (schools 13,304; Nebraska 49 state house rows), at-large label.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':768}); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    req=[]; pg.on('request',lambda r:req.append(r.url))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    r=await pg.evaluate("""async()=>{ await Promise.all(['Iowa','Ohio','Illinois','Connecticut','Oklahoma','Pennsylvania'].map(s=>loadState(s))); await window.__loadDS('schools');
      const G=window.__GEOM, nT=s=>G.towns.filter(d=>d[0]===s).length, nP=s=>G.places.filter(d=>d[0]===s).length;
      const ia=[...new Set(G.counties.filter(d=>d[0]==='Iowa').map(d=>d[1]))]; let shown=0, raw=0, pairs=0;
      ia.forEach(c=>{ const t=window.__townsIn('Iowa',c); shown+=t.length; const n=new Map(); t.forEach(x=>{ const k=window.__normT(x[2]); n.set(k,(n.get(k)||0)+1); }); n.forEach(v=>{ if(v>1) pairs++; }); });
      raw=G.towns.filter(d=>d[0]==='Iowa').length;
      const oh=window.__townsIn('Ohio','Union County').filter(t=>/^Washington township/.test(t[2])).map(t=>t[2]);
      const chi=window.__townsIn('Illinois','Cook County').filter(t=>/^Chicago( city)?$/.test(t[2])).map(t=>t[2]);
      const ans=window.__townsIn('Connecticut','New Haven County').filter(t=>/^Ansonia/.test(t[2])).map(t=>t[2]);
      const okc=[...new Set(G.counties.filter(d=>d[0]==='Oklahoma').map(d=>d[1]))]; let ok0=0, ok1=new Set();
      okc.forEach(c=>{ ok0+=window.__sic0('Oklahoma',c).length; window.__sic('Oklahoma',c).forEach(d=>ok1.add(d[1])); });
      const pa=window.__sic('Pennsylvania','Philadelphia County').map(d=>d[1]);
      return {iaT:nT('Iowa'),iaP:nP('Iowa'),shown,raw,pairs,oh,chi,ans,ok0,ok1:ok1.size,pa,
        sch:DATA.schools?DATA.schools.length:null,ne:(DATA.statehouse||[]).filter(x=>x[0]==='Nebraska').length,
        al:['Wyoming','Alaska','Vermont'].map(s=>window.__aname({kind:'natcd',tk:'ushouse',d:[s,'00']})), d5:window.__aname({kind:'natcd',tk:'ushouse',d:['Pennsylvania','05']})}}""")
    print(json.dumps(r)[:900])
    bad=[u for u in req if '/data/' in u and '/v2/data/' not in u]; ck(not bad,"no request outside v2/data (zero ../data/)",bad[:3])
    ck(any('/v2/data/parts/Iowa.js' in u for u in req) and any('/v2/data/places/Iowa.js' in u for u in req) and any('/v2/data/states/Iowa.js' in u for u in req),"Iowa reads states/ + parts/ + places/")
    ck(r['iaT']>=2600 and r['iaP']>=900,"Iowa towns from parts/ (2,609 rows) and places from places/",[r['iaT'],r['iaP']])
    ck(r['shown']>=r['raw']-5 and r['pairs']>=150,f"Iowa: same-name city/township pairs both show ({r['pairs']} pairs, {r['shown']}/{r['raw']} rows)",r)
    ck(len(r['oh'])==2,"Ohio Union County: both Washington townships",r['oh'])
    ck(len(r['chi'])==1,"Cook County: Chicago once (identical full names collapse)",r['chi'])
    ck(len(r['ans'])==1,"Connecticut: Ansonia city / town = one row (TOWN_PAIRS same)",r['ans'])
    ck(r['ok1']>=480 and r['ok1']>r['ok0'],f"Oklahoma county school lists cover the v2 districts ({r['ok1']} distinct, was {r['ok0']} rows)",[r['ok0'],r['ok1']])
    ck(len(r['pa'])>=1 and any('Philadelphia' in x for x in r['pa']),"Philadelphia County schools",r['pa'])
    ck(r['al']==['At large']*3 and r['d5']=='District 5',"at-large US House label",[r['al'],r['d5']])
    ck(r['ne']==49,"PACK statehouse: 49 Nebraska rows",r['ne'])
    ck(not er,"no page errors",er[:3]); await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
