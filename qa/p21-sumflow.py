import json,sys
for f in sys.argv[1:]:
  d=json.load(open(f))
  for tag,R in d.items():
    slow={k:v for k,v in R['lat'].items() if v and v>100}
    print('==',f,tag,'slow>100:',slow)
    print('  lat',R['lat'])
    print('  notes',R['notes'])
    print('  rows_default',R.get('rows_default',[])[:3],' num',R.get('num_mode'),R.get('rows_num',[])[:2])
    print('  chart_opts',R.get('chart_opts'),R.get('chart_opts_single'),R.get('chart_mode'),R.get('chart_now'))
    print('  PA',R.get('PA_info'),R.get('PA_rows',[])[:2]); print('  county',R.get('county_info'),R.get('county_rows',[])[:2]); print('  town',R.get('town_info'),R.get('town_rows',[])[:2])
    print('  after_back',R.get('after_back')); print('  ushouse_rows',len(R.get('ushouse_rows',[])),R.get('ushouse_rows',[])[:2])
    print('  restore',R.get('restore',[None,None,None])[2],(R.get('restore') or ['',''])[1][:150])
    print('  addr',R.get('addr_result'))
    print('  cls',R.get('cls'),'err',R['pageerr'][:3],[x for x in R['console'] if x.startswith('error')][:3],'reqfail',R['reqfail'][:3],'http',R['http'][:3])
    lay={k:v for k,v in R['layout'].items() if v['over'] or v['off']}
    print('  layout issues',json.dumps(lay)[:800])
