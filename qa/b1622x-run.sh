set -x
python3 b1622x-empty.py Illinois,Minnesota,Iowa,Indiana,Michigan,Ohio,Missouri,Nebraska,New\ Jersey,Pennsylvania,Vermont,Rhode\ Island,Massachusetts,Wisconsin,Georgia,North\ Carolina a
python3 b1622x-tot.py
python3 b1622x-jeff3.py
python3 b1622x-cityN.py webkit 390x844 "New Jersey|Camden County|Gloucester City city|Gloucester township#New Jersey|Camden County|Gloucester township|Gloucester City#Michigan|Alpena County|Alpena city|Alpena township#Michigan|Alpena County|Alpena township|Alpena city#Michigan|Oakland County|Royal Oak city|Royal Oak charter;Clawson#Pennsylvania|Bucks County|Bristol township|Bristol borough#Vermont|Washington County|Barre town|Barre city#Illinois|Cook County|Skokie village|Evanston;Niles#Pennsylvania|Allegheny County|Baldwin township|Baldwin borough;Pittsburgh#Wisconsin|Kenosha County|Kenosha city|Pleasant Prairie;Village of#North Carolina|Alamance County|Burlington city|Graham;West Graham#Georgia|Clayton County|Forest Park city|Morrow#Georgia|Clayton County|Morrow city|Forest Park#Ohio|Franklin County|Jackson township|Grove City#Vermont|Chittenden County|Burlington city|South Burlington#Rhode Island|Kent County|Warwick city|West Warwick#Pennsylvania|Montgomery County|Pottstown borough|West Pottsgrove" a
python3 b1622x-q129.py chromium 390x844 "Pittsburgh|Boston|Columbus"
python3 b1622x-addr2.py webkit 390x844 GA,NC,NV,TX
python3 b1622x-sortchart.py chromium 320x568 NC Mecklenburg
python3 b1622x-sortchart.py webkit 1024x768 GA Fulton
python3 b1622x-chartval.py webkit 1024x768 Texas,Georgia,Nevada
for s in 390 375 320 1024x576 1024x768; do for e in chromium webkit; do python3 b1622x-lay3.py $e $s; done; done
python3 b1622x-q115.py
echo DONE
