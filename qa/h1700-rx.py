import re,sys
for f in sys.argv[1:]:
  for l in open(f):
    k=l.split(' ')[0]
    if not re.match(r'^[A-Za-z0-9]+-[a-z]+$',k): continue
    cr=re.findall(r'"crumbs": "([^"]*)"',l); th=[re.findall(r'/ ([0-9.]+%)',t) for t in re.findall(r'"th": \[([^\]]*)\]',l)]; gq=re.findall(r'"gq": "([^"]*)"',l); pp=re.findall(r'"(?:pop|popc)": \[([^\]]*)\]',l)
    print(f.split('-')[-1][:-4],k,'| crumbs',cr,'| th',th,'| fld',gq[::2] if len(gq)>3 else gq,'| pop',[p[:60] for p in pp])
