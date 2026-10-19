#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p29-queue.log; timeout 700 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p29-queue.log; }
r p29-back2-wk.log p29-back2.py webkit 390,1024x768 2
r p29-back2-ch.log p29-back2.py chromium 390 2
r p29-ylat-ch576.log p29-ylat.py chromium 1024 576 statehouse,senate,map
r p29-lay3-wk390.log p29-lay3.py webkit 390
r p29-lay3-ch768.log p29-lay3.py chromium 1024x768
r p29-own-ch390.log p29-own.py chromium iphone390
r p29-pa16-wk390.log p29-pa16.py webkit 390 844
r p29-menus-wk.log p29-menus.py webkit iphone390 ipad1024x768
r p29-flow-ch.log p29-flow.py chromium
echo "=== ALL DONE $(date +%T)" >> p29-queue.log
