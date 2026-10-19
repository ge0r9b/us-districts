#!/bin/bash
cd /workspace/w/lanes/qa/qa
while pgrep -f 'python3 p27-' >/dev/null; do sleep 3; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p27-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p27-queue.log; }
DONE=$(grep -c 'end p27-067.log' p27-queue.log)
[ "$DONE" = 0 ] && r p27-067.log p27-067.py webkit:390:844,chromium:375:667,webkit:1024:768
r p27-ylat-ch576.log p27-ylat.py chromium 1024 576 statehouse,senate,map
URL=http://127.0.0.1:8850/v2/ r p27-back2-ch-local1602.log p27-back2.py chromium 390 1
URL=http://127.0.0.1:8851/v2/ r p27-back2-ch-local1604.log p27-back2.py chromium 390 1
r p27-ylat-ch390.log p27-ylat.py chromium 390 844 statehouse,senate,map
r p27-lay2-wk390.log p27-lay2.py webkit 390
r p27-flow-ch.log p27-flow.py chromium
r p27-col16-ch390.log p27-col16.py chromium iphone390
r p27-pa16-wk390.log p27-pa16.py webkit 390 844
r p27-lay2-ch390.log p27-lay2.py chromium 390
r p27-v95-ch390.log p27-v95.py chromium iphone390
r p27-menus-wk.log p27-menus.py webkit iphone390 ipad1024x768
echo "=== ALL DONE $(date +%T)" >> p27-queue.log
