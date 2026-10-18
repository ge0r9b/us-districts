import openstates_metadata as M, subprocess, os, time, json
ST50 = sorted(a.upper() for a in M.STATES_BY_ABBR if a.upper() not in ("DC","PR","GU","VI","AS","MP","US","ZA"))
special = {"MD":"Maryland Supreme Court","NY":"New York Court of Appeals","MA":"Massachusetts Supreme Judicial Court","ME":"Maine Supreme Judicial Court","WV":"West Virginia Supreme Court of Appeals"}
pages = {}
for st in ST50:
    pages[st+"_SC"] = special.get(st, M.lookup(abbr=st).name + " Supreme Court")
pages["TX_CCA"] = "Texas Court of Criminal Appeals"; pages["OK_CCA"] = "Oklahoma Court of Criminal Appeals"
for k, t in pages.items():
    fn = f"bp/courts/{k}.html"
    if os.path.exists(fn) and os.path.getsize(fn) > 30000: continue
    subprocess.run(["curl","-sL","-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36","https://ballotpedia.org/"+t.replace(' ','_'),"-o",fn]); time.sleep(0.7)
json.dump(pages, open("bp/courts/pages.json","w"), indent=1)
