cd /workspace/w/lanes/qa/qa
timeout 400 python3 h0400-states.py webkit 390x844 "Michigan:Wayne:types" x we390solo > h0400-states-we390solo.log 2>&1; echo s1
timeout 400 python3 h0400-states.py chromium 1024x768 "Ohio:Franklin:types" x ch1024solo > h0400-states-ch1024solo.log 2>&1; echo s2
timeout 500 python3 h0400-lay3.py webkit 375 -solo > h0400-lay3-we-375-solo.log 2>&1; echo l
timeout 300 python3 h0400-audit.py > h0400-audit.log 2>&1; echo au
touch h0400b.done
