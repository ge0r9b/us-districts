#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p28-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p28-queue.log; }
r p28-addr-wk.log p28-addr.py webkit
r p28-addr-ch.log p28-addr.py chromium
r p28-ylat-ch576.log p28-ylat.py chromium 1024 576 statehouse,senate,map
r p28-ylat-ch390.log p28-ylat.py chromium 390 844 statehouse,senate,map
r p28-back2-wk.log p28-back2.py webkit 390 2
r p28-back2-ch.log p28-back2.py chromium 390 2
r p28-067.log p28-067.py webkit:390:844,chromium:375:667
r p28-lay3-wk390.log p28-lay3.py webkit 390
r p28-lay3-ch768.log p28-lay3.py chromium 1024x768
r p28-lay3-ch576.log p28-lay3.py chromium 1024x576
r p28-flow-ch.log p28-flow.py chromium
r p28-own-ch390.log p28-own.py chromium iphone390
r p28-pa16-wk390.log p28-pa16.py webkit 390 844
r p28-menus-wk.log p28-menus.py webkit iphone390 ipad1024x768
echo "=== ALL DONE $(date +%T)" >> p28-queue.log
