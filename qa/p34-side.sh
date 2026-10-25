#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p34-side.log; timeout 900 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p34-side.log; }
r p34-ny-ch.log env ONLY=chromium python3 p33-orch-ny-data.py https://ge0r9b.github.io/us-districts/v2/
r p34-lay3-ch390.log python3 p33-lay3.py chromium 390
r p34-lay3-ch768.log python3 p33-lay3.py chromium 1024x768
r p34-pa16-ch.log python3 p33-pa16.py chromium 390 844
r p34-menus-ch.log python3 p33-menus.py chromium
r p34-lay3-wk375.log python3 p33-lay3.py webkit 375
r p34-lay3-ch576.log python3 p33-lay3.py chromium 1024x576
echo "=== SIDE DONE $(date +%T)" >> p34-side.log
