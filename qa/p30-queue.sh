#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p30-queue.log; timeout 700 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p30-queue.log; }
r p30-back2-wk.log p30-back2.py webkit 390,1024x768 2
r p30-back2-ch.log p30-back2.py chromium 390 2
r p30-addr-wk.log p30-addr.py webkit 390x844
r p30-addr-wk-rep.log p30-addr.py webkit 390x844 phila,allstates,phila rep
r p30-addr-ch.log p30-addr.py chromium 390x844
r p30-ylat-ch576.log p30-ylat.py chromium 1024 576 statehouse,senate,map
r p30-lay3-wk390.log p30-lay3.py webkit 390
r p30-lay3-ch768.log p30-lay3.py chromium 1024x768
r p30-own-ch390.log p30-own.py chromium iphone390
r p30-v95-ch390.log p30-v95.py chromium iphone390
r p30-pa16-wk390.log p30-pa16.py webkit 390 844
r p30-menus-wk.log p30-menus.py webkit iphone390 ipad1024x768
r p30-flow-ch.log p30-flow.py chromium
echo "=== ALL DONE $(date +%T)" >> p30-queue.log
