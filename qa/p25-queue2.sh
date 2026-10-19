#!/bin/bash
cd /workspace/w/lanes/qa/qa
while pgrep -f p25-queue.sh >/dev/null; do sleep 3; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p25-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p25-queue.log; }
true
r p25-gbar-first-paint.log p25-gbar-rows-first-paint.py https://ge0r9b.github.io/us-districts/v2/ 390x844,320x568
r p25-rangebub-wk768.log p25-rangebub.py webkit 1024 768
echo "=== ALL2 DONE $(date +%T)" >> p25-queue.log
