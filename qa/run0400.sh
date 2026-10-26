cd /workspace/w/lanes/qa/qa
(timeout 1500 python3 h0400-states.py webkit 390x844 "Arizona:Maricopa:types+ranges+drill,Wisconsin:Milwaukee:types+ranges+drill,Michigan:Wayne:types+ranges+drill" x we390 > h0400-states-we390.log 2>&1; echo st1) &
(timeout 1500 python3 h0400-states.py chromium 1024x768 "Indiana:Marion:types+ranges+drill,Ohio:Franklin:types+ranges+drill,New Hampshire:Hillsborough:types+ranges+drill,Delaware:New Castle:types+ranges+drill" x ch1024 > h0400-states-ch1024.log 2>&1; echo st2) &
wait
timeout 500 python3 h0400-lay3.py chromium 1024x768 > h0400-lay3-ch-1024x768.log 2>&1; echo l1
timeout 500 python3 h0400-lay3.py webkit 375 > h0400-lay3-we-375.log 2>&1; echo l2
timeout 500 python3 h0400-lay3.py chromium 390 > h0400-lay3-ch-390.log 2>&1; echo l3
timeout 500 python3 h0400-own.py webkit iphone320 ipad1024x576 > h0400-own.log 2>&1; echo own
timeout 400 python3 h0400-col16.py chromium iphone375 > h0400-col16.log 2>&1; echo c16
timeout 300 python3 h0400-pa16.py webkit 1024 576 > h0400-pa16.log 2>&1; echo pa
timeout 300 python3 h0400-menus.py chromium iphone320 ipad1024x768 > h0400-menus.log 2>&1; echo me
timeout 300 python3 h0400-sortchart.py chromium 1024x768 OH Franklin > h0400-sc.log 2>&1; echo sc
touch h0400.done
