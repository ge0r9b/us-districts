cp b1622h2300-layout3-webkit-1024x768.json b1622h2300-layout3-webkit-1024x768-s1.json
for i in 2 3; do timeout 400 python3 h2300-lay3.py webkit 1024x768 > h2300-lay3-webkit-1024x768-s$i.log 2>&1; cp b1622h2300-layout3-webkit-1024x768.json b1622h2300-layout3-webkit-1024x768-s$i.json; echo done $i; done
cp b1622h2300-layout3-webkit-1024x768-s1.json b1622h2300-layout3-webkit-1024x768.json
