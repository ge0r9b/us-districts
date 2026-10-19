#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p25-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p25-queue.log; }
r p25-bubble-ch390.log p25-bubble.py chromium 390 844
r p25-bubble-ch375.log p25-bubble.py chromium 375 667
r p25-bubble-ch320.log p25-bubble.py chromium 320 568
r p25-bubble-ch576.log p25-bubble.py chromium 1024 576
r p25-bubble-ch768.log p25-bubble.py chromium 1024 768
r p25-bubble-wk390.log p25-bubble.py webkit 390 844
r p25-bubble-wk768.log p25-bubble.py webkit 1024 768
r p25-rowfr-ch390.log p25-rowfr.py chromium 390 844
r p25-rowfr-wk390.log p25-rowfr.py webkit 390 844
r p25-ylat-ch576.log p25-ylat.py chromium 1024 576 statehouse,senate
r p25-ylat-ch390.log p25-ylat.py chromium 390 844 statehouse,map
r p25-ushouse.log p25-ushouse-in-county.py https://ge0r9b.github.io/us-districts/v2/
r p25-v95-ch390.log p25-v95.py chromium iphone390
r p25-col16-ch390.log p25-col16.py chromium iphone390
r p25-pa16-wk390.log p25-pa16.py webkit 390 844
r p25-own-ch390.log p25-own.py chromium iphone390
r p25-menus-wk.log p25-menus.py webkit iphone390 ipad1024x768
r p25-flow-ch.log p25-flow.py chromium
r p25-numjit-ch390.log p25-numjit.py chromium 390 844
r p25-lay2-ch390.log p25-lay2.py chromium 390
r p25-lay2-wk390.log p25-lay2.py webkit 390
r p25-lay2-ch768.log p25-lay2.py chromium 1024x768
r p25-previews.log p25-previews.py
echo "=== ALL DONE $(date +%T)" >> p25-queue.log
