# aggFor prototypes on the current tree: A2 = as shipped, E = idle warm-up (rIC, resumable job), F = build-time table (data/pxd/<State>.js)
import os,shutil,sys
SRC='/workspace/w/perf'; OUT='/workspace/perf/proto'; T=os.path.dirname(os.path.abspath(__file__))
L=open(f'{SRC}/v2/index.html').read().split('\n')
DBG='window.__aggDbg=()=>({AGG,aggFor,grid,gq,pointInItem}); /* perf test hook only */'
i0=next(i for i,l in enumerate(L) if l.startswith('function aggFor(k,yr){')); i1=next(i for i in range(i0,i0+40) if L[i].startswith('  return AGG[key]=res;'))+1
assert L[i1].strip()=='}', L[i1]; i1+=1
def root(name,datadir=False):
  r=f'{OUT}/{name}'; shutil.rmtree(r,ignore_errors=True); os.makedirs(f'{r}/v2')
  for d in ('data','lib'): os.symlink(f'{SRC}/{d}',f'{r}/{d}')
  os.symlink(f'{SRC}/v2/img',f'{r}/v2/img')
  if datadir:
    os.makedirs(f'{r}/v2/data'); [os.symlink(f'{SRC}/v2/data/{e}',f'{r}/v2/data/{e}') for e in os.listdir(f'{SRC}/v2/data')]
  else: os.symlink(f'{SRC}/v2/data',f'{r}/v2/data')
  return r
open(root('A2')+'/v2/index.html','w').write('\n'.join(L[:i1]+[DBG]+L[i1:]))
E_=L[:i0]+open(f'{T}/aggE.js').read().rstrip('\n').split('\n')+[DBG]+L[i1:]
open(root('E')+'/v2/index.html','w').write('\n'.join(E_))
F_=L[:i1]+open(f'{T}/aggF.js').read().rstrip('\n').split('\n')+[DBG]+L[i1:]
rF=root('F',True); open(rF+'/v2/index.html','w').write('\n'.join(F_)); os.makedirs(rF+'/v2/data/pxd')
src=f'{T}/../raw/pxd-Pennsylvania.js'
if os.path.exists(src): shutil.copy(src,rF+'/v2/data/pxd/Pennsylvania.js')
print('aggFor lines',i0+1,'-',i1,'| E',len(E_),'F',len(F_),'pxd',os.path.exists(src))
