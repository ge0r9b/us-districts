import asyncio,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    out={}
    for st,cn in [('Kentucky','Jefferson County'),('New Mexico','Bernalillo County'),('Oregon','Multnomah County')]:
      r=await pg.evaluate("a=>window.__townAudit(a[0],a[1])",[st,cn])
      tot=sum((x['v24'] or {}).get('tot',0) for x in r if isinstance(x['v24'],dict))
      out[cn]={'n':len(r),'sum24':tot,'np24':r[0]['np24'] if r else None,'top':sorted([(x['n'],(x['v24'] or {}).get('tot') if isinstance(x['v24'],dict) else x['v24']) for x in r],key=lambda t:-(t[1] or 0))[:8]}
      print(cn,json.dumps(out[cn]),flush=True)
    json.dump(out,open('b1621h2000-jeff.json','w'),indent=1)
asyncio.run(main())
