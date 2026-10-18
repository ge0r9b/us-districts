# Build local prototype roots from the clean origin/main tree (/workspace/w/perf):
#  A = unchanged v2 (baseline)
#  B = A + PACK/XREF moved out of index.html into v2/pack.js (JSON.parse, content-hash URL)
#  C = B + data/script URLs versioned by a data version (window.DATAV) instead of window.BUILD
import os,re,json,hashlib,shutil
SRC='/workspace/w/perf'; OUT='/workspace/perf/proto'
s=open(f'{SRC}/v2/index.html').read()
def root(name):
  r=f'{OUT}/{name}'; shutil.rmtree(r,ignore_errors=True); os.makedirs(f'{r}/v2')
  for d in ('data','lib'): os.symlink(f'{SRC}/{d}',f'{r}/{d}')
  for d in ('data','img'): os.symlink(f'{SRC}/v2/{d}',f'{r}/v2/{d}')
  return r
def esc(t): return t.replace('\\','\\\\').replace("'","\\'")
open(root('A')+'/v2/index.html','w').write(s)
st=s.index('<script>\nconst PACK = '); en=s.index('</script>',st)
blk=s[st+len('<script>\n'):en]; lines=blk.split('\n')
assert lines[0].startswith('const PACK = { lists: ') and lines[5].startswith('const XREF = ')
p=lines[0]; j0=len('const PACK = { lists: '); g=p.rindex(', geom: {')
lists=p[j0:g]; json.loads(lists); geom=p[g+2:]
xr=lines[5][len('const XREF = '):].rstrip(';'); json.loads(xr)
pack="const PACK = { lists: JSON.parse('"+esc(lists)+"'), "+geom+"\nconst XREF = JSON.parse('"+esc(xr)+"');\n"
h=hashlib.sha1(pack.encode()).hexdigest()[:10]
rest='\n'.join([l for i,l in enumerate(lines) if i not in (0,5)])
sB=s[:st]+f'<script src="pack.js?v={h}"></script>\n<script>\n'+rest+s[en:]
rB=root('B'); open(rB+'/v2/index.html','w').write(sB); open(rB+'/v2/pack.js','w').write(pack)
dv='d'+h[:6]
sC=sB.replace('window.BUILD="202610181575"','window.BUILD="202610181575";window.DATAV="%s"'%dv,1)
sC,n0=re.subn(r'(\?v=["\']\s*\+\s*\(?)window\.BUILD',r'\1window.DATAV',sC)
rC=root('C'); open(rC+'/v2/index.html','w').write(sC); os.symlink(rB+'/v2/pack.js',rC+'/v2/pack.js')
print('pack.js',len(pack),'hash',h,'B index',len(sB),'C url refs replaced',n0)
# D = A + tap-latency fixes: (1) list-all enter(): fit the map one frame after the list paints (was synchronous fitBounds inside the tap)
#                          (2) pointInItem: indexed loops instead of forEach + array destructuring (same even-odd/hole semantics)
sD=s
o1='setView("list"); LA.sig=sig(); render(); try{ layoutSide(); }catch(e){} fit(); }'
n1='setView("list"); LA.sig=sig(); render(); try{ layoutSide(); }catch(e){} requestAnimationFrame(()=>setTimeout(fit,0)); }'
assert sD.count(o1)==1; sD=sD.replace(o1,n1)
o2="""    rings.forEach((ring, ri) => {
      let c = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) c = !c;
      }
      if (ri === 0) inside = c; else if (c) inside = false;
    });"""
n2="""    for (let ri = 0; ri < rings.length; ri++) { const ring = rings[ri];
      let c = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const pi = ring[i], pj = ring[j], yi = pi[1], yj = pj[1];
        if ((yi > lat) !== (yj > lat) && lon < (pj[0] - pi[0]) * (lat - yi) / (yj - yi) + pi[0]) c = !c;
      }
      if (ri === 0) inside = c; else if (c) inside = false;
    }"""
assert sD.count(o2)==1; sD=sD.replace(o2,n2)
open(root('D')+'/v2/index.html','w').write(sD); print('D built')
