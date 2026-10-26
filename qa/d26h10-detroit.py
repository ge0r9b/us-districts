# Oct 26 ~10 AM (1623) copy of h0400-detroit.py
# Oct 26 ~4 AM (1622): Detroit city row vs certified (221,157 / 19,638 / 246,552, detroitmi.gov official)
import asyncio,json
from playwright.async_api import async_playwright
from common import *
JS="""async ([st,cn,town])=>{ await window.__townAudit(st,cn); const rows=(PREC[st]||[]).filter(r=>r[0]===cn); const T=window.__townsIn(st,cn); const asg=new Map(); for(const d of T){const g=window.__pri(d,PREC[st],cn); const nm=(d.n||d.name||String(d)).toString().split(',')[2]||String(d); g.forEach(r=>asg.set(r,nm));}
 const det=rows.filter(r=>/detroit/i.test(r[1])); const by={}; for(const r of det){const k=asg.get(r)||'NONE'; by[k]=by[k]||[0,0,0,0]; by[k][0]++; by[k][1]+=+r[2]||0; by[k][2]+=+r[3]||0; by[k][3]+=+r[4]||0;}
 const s=(a,i)=>a.reduce((x,r)=>x+(+r[i]||0),0);
 return {nrows:rows.length, county:[s(rows,2),s(rows,3),s(rows,4)], detroitNamed:[det.length,s(det,2),s(det,3),s(det,4)], detByTown:by, names:det.map(r=>r[1]).slice(0,80), sampleOther:rows.filter(r=>!/detroit/i.test(r[1])).slice(0,3).map(r=>r.slice(0,5))}; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    r=await pg.evaluate(JS,['Michigan','Wayne County','Detroit city'])
    try: r['e24']=await pg.evaluate("()=>{const t=window.ELECTION2024;const k=Object.keys(t||{}).filter(k=>/Wayne/.test(k)&&/Mich|MI|26/.test(k));return [k,k.map(x=>t[x])]}")
    except Exception as e: r['e24']=str(e)[:200]
    print(json.dumps(r)[:6000]); json.dump(r,open('b1623d26h10-detroit.json','w'),indent=1)
asyncio.run(main())
