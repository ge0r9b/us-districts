import asyncio,json
from playwright.async_api import async_playwright
from common import *
AB=dict(AL='Alabama',AK='Alaska',AZ='Arizona',AR='Arkansas',CA='California',CO='Colorado',CT='Connecticut',DE='Delaware',DC='District of Columbia',FL='Florida',GA='Georgia',HI='Hawaii',ID='Idaho',IL='Illinois',IN='Indiana',IA='Iowa',KS='Kansas',KY='Kentucky',LA='Louisiana',ME='Maine',MD='Maryland',MA='Massachusetts',MI='Michigan',MN='Minnesota',MS='Mississippi',MO='Missouri',MT='Montana',NE='Nebraska',NV='Nevada',NH='New Hampshire',NJ='New Jersey',NM='New Mexico',NY='New York',NC='North Carolina',ND='North Dakota',OH='Ohio',OK='Oklahoma',OR='Oregon',PA='Pennsylvania',RI='Rhode Island',SC='South Carolina',SD='South Dakota',TN='Tennessee',TX='Texas',UT='Utah',VT='Vermont',VA='Virginia',WA='Washington',WV='West Virginia',WI='Wisconsin',WY='Wyoming')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.min;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(6000)
    print('E20 loaded', await pg.evaluate("()=>!!window.ELECTION2020"))
    app=await pg.evaluate("names=>{const o={};for(const [a,n] of Object.entries(names)){o[a]={y24:window.__stTot(n,'2024'),y20:window.__stTot(n,'2020')}};return o}",AB)
    await c.close(); await b.close()
  f24=json.load(open('fec24.json')); f20=json.load(open('fec20.json'))
  bad=[]; tot={'24':[0,0,0],'20':[0,0,0]}
  for a in AB:
    for yr,f,dk in (('24',f24,'HARRIS'),('20',f20,'BIDEN')):
      v=app[a]['y'+yr]; 
      if not v: bad.append((a,yr,'missing')); continue
      o=[f[dk].get(a),f['TRUMP'].get(a),f['TOTAL_VOTES'].get(a)]
      for i in range(3): tot[yr][i]+=v[i]
      d=[v[i]-(o[i] or 0) for i in range(3)]
      if any(abs(x)>0 for x in d[:2]) or abs(d[2])>0.005*o[2]: bad.append((a,'20'+yr,'app',v[:3],'fec',o,'diff',d))
  for x in bad: print(x)
  print('app national',tot)
  print('fec 24 D R T',sum(f24['HARRIS'].values()),sum(f24['TRUMP'].values()),sum(f24['TOTAL_VOTES'].values()))
  print('fec 20 D R T',sum(f20['BIDEN'].values()),sum(f20['TRUMP'].values()),sum(f20['TOTAL_VOTES'].values()))
if __name__=='__main__': asyncio.run(main())
