import openstates_metadata as M, subprocess, os, time, json
ST50 = sorted(a.upper() for a in M.STATES_BY_ABBR if a.upper() not in ("DC","PR","GU","VI","AS","MP","US","ZA"))
pages = {}
for st in ST50:
    s = M.lookup(abbr=st); n = s.name
    if s.unicameral: pages[(st,'legislature')] = "Nebraska State Senate"; continue
    pages[(st,'upper')] = f"{n} State Senate"
    lower = {"CA":"California State Assembly","NV":"Nevada State Assembly","NY":"New York State Assembly","WI":"Wisconsin State Assembly",
             "NJ":"New Jersey General Assembly","MD":"Maryland House of Delegates","VA":"Virginia House of Delegates","WV":"West Virginia House of Delegates"}
    pages[(st,'lower')] = lower.get(st, f"{n} House of Representatives")
os.makedirs('bp/chambers', exist_ok=True)
for (st,ch),title in pages.items():
    fn = f"bp/chambers/{st}_{ch}.html"
    if os.path.exists(fn) and os.path.getsize(fn) > 50000: continue
    subprocess.run(["curl","-sL","-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                    "https://ballotpedia.org/"+title.replace(' ','_'),"-o",fn])
    time.sleep(0.7)
json.dump({f"{k[0]}_{k[1]}":v for k,v in pages.items()}, open('bp/chambers/pages.json','w'), indent=1)
