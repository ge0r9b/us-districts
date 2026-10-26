cd /workspace/w/lanes/qa/qa
(timeout 1100 python3 h0300-states.py webkit 1024x768 "Alabama:Jefferson:types+ranges+drill,Arkansas:Pulaski:types+ranges+drill,Oklahoma:Oklahoma:types+ranges+drill" x we1024 > h0300-states-we1024.log 2>&1; echo st1) &
(timeout 1100 python3 h0300-states.py chromium 320x568 "Idaho:Ada:types+ranges+drill,Montana:Yellowstone:types+ranges+drill,Wyoming:Laramie:types+ranges+drill" x ch320 > h0300-states-ch320.log 2>&1; echo st2) &
wait
timeout 500 python3 h0300-lay3.py webkit 390 > h0300-lay3-we-390.log 2>&1; echo l1
timeout 500 python3 h0300-lay3.py chromium 1024x576 > h0300-lay3-ch-1024x576.log 2>&1; echo l2
timeout 500 python3 h0300-lay3.py chromium 375 > h0300-lay3-ch-375.log 2>&1; echo l3
timeout 300 python3 h0300-sortchart.py webkit 390x844 AL Jefferson > h0300-sc.log 2>&1; echo sc
touch h0300.done
