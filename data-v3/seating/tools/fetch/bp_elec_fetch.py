import json, subprocess, os, time
pages = json.load(open('bp/chambers/pages.json'))
for k, t in pages.items():
    fn = f"bp/elections/{k}.html"
    if os.path.exists(fn) and os.path.getsize(fn) > 30000: continue
    subprocess.run(["curl","-sL","-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36","https://ballotpedia.org/"+t.replace(' ','_')+"_elections,_2026","-o",fn]); time.sleep(0.6)
print("done")
