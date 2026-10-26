cd /workspace/w/lanes/qa/qa
timeout 500 python3 d26h07-own.py webkit iphone375 ipad1024x576 > d26h07-own.log 2>&1; echo own
timeout 400 python3 d26h07-col16.py chromium iphone390 > d26h07-col16.log 2>&1; echo c16
timeout 300 python3 d26h07-pa16.py webkit 390 844 > d26h07-pa16.log 2>&1; echo pa
timeout 300 python3 d26h07-menus.py chromium iphone320 ipad1024x768 > d26h07-menus.log 2>&1; echo me
timeout 400 python3 d26h07-sortchart.py chromium 1024x768 IL Cook > d26h07-sc.log 2>&1; echo sc
touch d26h07b.done
