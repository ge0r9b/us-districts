import json,sys
d=json.load(open(sys.argv[1]))
for st,R in d.items():
  print('==',st,R['build'],R['map'][1],R['tot'].get('2024'),'err',R.get('err'))
  for k,T in R.get('types',{}).items():
    print(' ',k,'n',T['n'],'lat',T['lat'],'tolist',T['lat_tolist'],'numpick',T.get('lat_numpick'),'sort',T['hdr']['sort'],'| th',T['th'],'th#',T['th_num'],'| rows',T['rows'][:3],'rows#',T['rows_num'][:2],'| lay',T['layout'],T['layout_num'])
    if 'reload' in T: print('   reload',T['reload']['before']==T['reload']['after'],T['reload']['after'][:200],T['reload']['hdr'],T['reload']['n'])
  for k,G in R.get('ranges',{}).items():
    print('  range',k,G['ysl'],G['ym'],G['th'],G['opts'],{c:(v['lat'],v['mode'],v['layout']) for c,v in G['charts'].items()})
  D=R.get('drill')
  if D:
    for k in ['lat_counties','n1','rows1','lat_county','hdr2','n2','rows2','th2','lat_sub','hdr3','n3','rows3','th3','map3','layout2']:
      print('  drill',k,D.get(k))
    if 'reload' in D: print('  drill reload same',D['reload']['before']==D['reload']['after'],D['reload']['hdr'],D['reload']['th'])
