#!/bin/bash
cd /workspace/w/lanes/qa/qa
while pgrep -f p26-t-year-tap-speed.py >/dev/null; do sleep 3; done
echo "=== $(date +%T) end p26-t-yeartap.log (queue restarted)" >> p26-queue.log
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p26-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p26-queue.log; }
r p26-ylat-ch576.log p26-ylat.py chromium 1024 576 statehouse,senate
r p26-ylat-ch390.log p26-ylat.py chromium 390 844 statehouse,map
r p26-rangebub-ch390.log p26-rangebub.py chromium 390 844
r p26-t-gbar.log p26-t-gbar-first-paint.py https://ge0r9b.github.io/us-districts/v2/ 390x844,320x568
r p26-col16-ch390.log p26-col16.py chromium iphone390
r p26-v95-ch390.log p26-v95.py chromium iphone390
r p26-flow-ch.log p26-flow.py chromium
r p26-lay2-ch390.log p26-lay2.py chromium 390
r p26-lay2-wk390.log p26-lay2.py webkit 390
r p26-pa16-wk390.log p26-pa16.py webkit 390 844
echo "=== ALL DONE $(date +%T)" >> p26-queue.log
