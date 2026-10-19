#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p26-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p26-queue.log; }
r p26-t-batch.log p26-t-qa-batch-1600.py https://ge0r9b.github.io/us-districts/v2/
r p26-t-rangeclosed.log p26-t-range-bubble-closed.py https://ge0r9b.github.io/us-districts/v2/
r p26-t-yeartap.log p26-t-year-tap-speed.py https://ge0r9b.github.io/us-districts/v2/
r p26-rangebub-wk390.log p26-rangebub.py webkit 390 844
r p26-rangebub-ch390.log p26-rangebub.py chromium 390 844
r p26-ylat-ch576.log p26-ylat.py chromium 1024 576 statehouse,senate
r p26-ylat-ch390.log p26-ylat.py chromium 390 844 statehouse,map
r p26-ylat-wk390.log p26-ylat.py webkit 390 844 statehouse,map
r p26-t-gbar.log p26-t-gbar-first-paint.py https://ge0r9b.github.io/us-districts/v2/ 390x844,320x568
r p26-rowfr-ch390.log p26-rowfr.py chromium 390 844
r p26-rowfr-wk390.log p26-rowfr.py webkit 390 844
r p26-t-iconbub.log p26-t-icon-bubble.py https://ge0r9b.github.io/us-districts/v2/
r p26-t-ushouse.log p26-t-ushouse-in-county.py https://ge0r9b.github.io/us-districts/v2/
r p26-col16-ch390.log p26-col16.py chromium iphone390
r p26-pa16-wk390.log p26-pa16.py webkit 390 844
r p26-v95-ch390.log p26-v95.py chromium iphone390
r p26-menus-wk.log p26-menus.py webkit iphone390 ipad1024x768
r p26-flow-ch.log p26-flow.py chromium
r p26-lay2-ch390.log p26-lay2.py chromium 390
r p26-lay2-wk390.log p26-lay2.py webkit 390
r p26-lay2-ch768.log p26-lay2.py chromium 1024x768
echo "=== ALL DONE $(date +%T)" >> p26-queue.log
