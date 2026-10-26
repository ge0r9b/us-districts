# Oct 25 ~9 PM EDT (1622) hourly batch B (verify items + open-bug rechecks)
set -x
python3 h2100-col16.py chromium iphone390
python3 h2100-pa16.py webkit 390 844
python3 h2100-own.py webkit iphone320 ipad1024x768
python3 h2100-own.py chromium iphone375
python3 h2100-q130.py chromium 390x844 'Pittsburgh|Boston'
python3 h2100-jeff3.py
python3 h2100-q127.py
python3 h2100-sortchart.py chromium 375x667 PA Allegheny
python3 h2100-menus.py webkit iphone390 ipad1024x576
echo DONE
