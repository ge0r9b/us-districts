import json,sys
for f in sys.argv[1:]:
  print('==',f)
  for k,R in json.load(open(f)).items():
    print(k, 'tapC',bool(R.get('tapC')),'tapT',bool(R.get('tapT')),'county rows',R['county'][2],'cand',R['county'][3][:6])
    print('   town',R['town'][0]['crumbs'],R['town'][1],'rows',R['town'][2],R['town'][3][:3])
    print('   num',R['town_num'][0],'SUSPECT',R['suspect'],R.get('afterS'),R['err'])
