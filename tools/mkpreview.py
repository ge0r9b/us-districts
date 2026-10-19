#!/usr/bin/env python3
# Build a self-contained preview page at previews/<name>/index.html from a preview branch's v2/index.html.
# It loads v2's data and images by relative path (<base href="../../v2/">), is noindex, and never touches /v2/.
# usage: tools/mkpreview.py <git-ref> <name>   (run from the repo root)
import subprocess,sys,os,re
ref,name=sys.argv[1],sys.argv[2]
s=subprocess.check_output(["git","show",f"{ref}:v2/index.html"]).decode()
head='<meta charset="utf-8">'
assert head in s
s=s.replace(head,head+'\n<base href="../../v2/">\n<meta name="robots" content="noindex, nofollow">',1)
s=re.sub(r'<title>(.*?)</title>',lambda m:f'<title>PREVIEW {name}: {m.group(1)}</title>',s,count=1)
os.makedirs(f"previews/{name}",exist_ok=True)
open(f"previews/{name}/index.html","w").write(s)
print("wrote",f"previews/{name}/index.html",len(s))
