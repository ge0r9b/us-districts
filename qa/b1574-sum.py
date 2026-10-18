import json,sys
for fn in sys.argv[1:]:
 d=json.load(open(fn))
 for k,R in d.items():
  print('#####',fn,k,R.get('build'),R.get('EXC'))
  if 'EXC' in R: continue
  S=lambda v: json.dumps({a:v.get(a) for a in ('ym','y16','hi','ysl','chart','view','lv','crumbs','ynote','cands','opts','cmain','rows','cls','nrows')})[:900]
  print('US20',S(R['US20'])[:400])
  for L in ['US','States','PA','PhilaCo','Prec']:
    x=R[L]; print('==',L,'slider',x.get('slider_lat'),'tap',x.get('tap_lat')); print('  page',S(x['page']))
    for kk in ('reload','line','after_line','line_set16','line16','reload_line','pie','after_pie','bar','after_bar','num_page','shifts','shifts_slider','cmp20_24','cmp16'):
      if kk in x:
        v=x[kk]; print('  ',kk, S(v) if isinstance(v,dict) and 'ym' in v else json.dumps(v)[:500])
  print('err',R['err'],R['http'],R['reqfail'])
