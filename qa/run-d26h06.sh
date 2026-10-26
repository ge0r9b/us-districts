cd /workspace/w/lanes/qa/qa
(timeout 1500 python3 d26h06-states.py webkit 375x667 "Nevada:Clark:types+ranges+drill,New Mexico:Bernalillo:types+ranges+drill" x we375 > d26h06-states-we375.log 2>&1; echo st1) &
(timeout 1500 python3 d26h06-states.py chromium 1024x576 "Oregon:Multnomah:types+ranges+drill,Kentucky:Jefferson:types+ranges+drill" x ch1024 > d26h06-states-ch1024.log 2>&1; echo st2) &
wait
timeout 500 python3 d26h06-lay3.py webkit 1024x576 > d26h06-lay3-we-1024x576.log 2>&1; echo l1
timeout 500 python3 d26h06-lay3.py chromium 320 > d26h06-lay3-ch-320.log 2>&1; echo l2
timeout 500 python3 d26h06-lay3.py webkit 390 > d26h06-lay3-we-390.log 2>&1; echo l3
timeout 500 python3 d26h06-own.py chromium iphone390 ipad1024x768 > d26h06-own.log 2>&1; echo own
timeout 400 python3 d26h06-col16.py webkit iphone320 > d26h06-col16.log 2>&1; echo c16
timeout 300 python3 d26h06-pa16.py chromium 1024 768 > d26h06-pa16.log 2>&1; echo pa
timeout 300 python3 d26h06-menus.py webkit iphone375 ipad1024x576 > d26h06-menus.log 2>&1; echo me
timeout 300 python3 d26h06-sortchart.py webkit 1024x576 GA Fulton > d26h06-sc.log 2>&1; echo sc
touch d26h06.done
