#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p31-queue.log; timeout 700 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p31-queue.log; }
r p31-globe-ch.log p31-globe.py chromium
r p31-lay3-ch576.log p31-lay3.py chromium 1024x576
r p31-other-ch.log p31-other.py chromium
r p31-own-ch390.log p31-own.py chromium iphone390
echo "=== CH DONE $(date +%T)" >> p31-queue.log
while [ ! -f go-wk ]; do sleep 5; done
r p31-globe-wk.log p31-globe.py webkit
r p31-lay3-wk375.log p31-lay3.py webkit 375
r p31-lay3-wk320.log p31-lay3.py webkit 320
r p31-flow-wk.log p31-flow.py webkit
r p31-ylat-wk390.log p31-ylat.py webkit 390 844 statehouse,senate,map
echo "=== WK DONE $(date +%T)" >> p31-queue.log
while [ ! -f go-ch2 ]; do sleep 5; done
r p31-ylat-ch390.log p31-ylat.py chromium 390 844 statehouse,senate,map
echo "=== ALL DONE $(date +%T)" >> p31-queue.log
