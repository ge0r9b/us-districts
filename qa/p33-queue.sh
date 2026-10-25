#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p33-queue.log; timeout 900 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p33-queue.log; }
r p33-dcreload-ch.log python3 p33-dcreload.py chromium 390x844
r p33-addr2-ch.log python3 p33-addr2.py chromium 390x844 list
r p33-states-r.log python3 p33-states.py chromium 390x844 "Texas:Harris:drill,Florida:Miami-Dade:ranges+drill,New York:Kings:types+drill,Michigan:Wayne:types" x r
r p33-states-f.log python3 p33-states.py chromium 390x844 "Georgia:Fulton:types+drill,North Carolina:Mecklenburg:types+drill,Wisconsin:Milwaukee:types+drill,Nevada:Clark:types+drill,Maine:Cumberland:types+drill,Nebraska:Douglas:types+drill,Alaska:Anchorage:types+drill" x f
r p33-chip-ch.log python3 p33-chip.py
r p33-v95-ch.log python3 p33-v95.py chromium iphone390 iphone375 iphone320 ipad1024x576 ipad1024x768
r p33-other-ch.log python3 p33-other.py chromium
r p33-own-ch390.log python3 p33-own.py chromium iphone390
r p33-qa005.log python3 p33-t-ushouse-in-county.py $L
r p33-dcschools-ch.log python3 p33-dcschools.py chromium 390 844
echo "=== CH DONE $(date +%T)" >> p33-queue.log
r p33-dcreload-wk.log python3 p33-dcreload.py webkit 390x844
r p33-flow-wk.log python3 p33-flow.py webkit
r p33-lay3-wk375.log python3 p33-lay3.py webkit 375
r p33-lay3-wk320.log python3 p33-lay3.py webkit 320
r p33-lay3-wk576.log python3 p33-lay3.py webkit 1024x576
r p33-ylat-wk576.log python3 p33-ylat.py webkit 1024 576 statehouse,senate,map
r p33-067-wk.log python3 p33-067.py webkit:390:844
r p33-dcschools-wk.log python3 p33-dcschools.py webkit 390 844
r p33-pa16-wk.log python3 p33-pa16.py webkit 390 844
echo "=== WK DONE $(date +%T)" >> p33-queue.log
r p33-lay3-ch375.log python3 p33-lay3.py chromium 375
r p33-lay3-ch320.log python3 p33-lay3.py chromium 320
r p33-lay3-ch576.log python3 p33-lay3.py chromium 1024x576
echo "=== ALL DONE $(date +%T)" >> p33-queue.log
