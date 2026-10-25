#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p33-queue.log; timeout 900 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p33-queue.log; }
while ! grep -q "end p33-v95-ch.log" p33-queue.log; do sleep 2; done
pkill -f p33-queue2.sh; pkill -f p33-queue.sh; sleep 1; pkill -f "p33-other.py"; sleep 2
echo "=== $(date +%T) queue1/2 stopped; build 1612 re-test queue" >> p33-queue.log
r p33-orch-dcg-ch.log env ONLY=chromium python3 p33-orch-list-dc-globe.py $L
r p33-orch-cot-ch.log env ONLY=chromium python3 p33-orch-county-own-totals.py $L
r p33-dcreload-ch2.log python3 p33-dcreload.py chromium 390x844
r p33-addr2-ch2.log python3 p33-addr2.py chromium 390x844 list,map
r p33-states-r2.log python3 p33-states.py chromium 390x844 "Texas:Harris:drill,Florida:Miami-Dade:types+drill,New York:Kings:types+drill,Michigan:Wayne:types,Wisconsin:Milwaukee:types" x r1612
r p33-chip-ch2.log python3 p33-chip.py
r p33-074-ch.log python3 p33-074.py chromium 390x844 Ohio,Texas,California
r p33-other-ch.log python3 p33-other.py chromium
r p33-own-ch390.log python3 p33-own.py chromium iphone390
r p33-qa005.log python3 p33-t-ushouse-in-county.py $L
echo "=== CH3 DONE $(date +%T)" >> p33-queue.log
r p33-orch-dcg-wk.log env ONLY=webkit python3 p33-orch-list-dc-globe.py $L
r p33-dcreload-wk.log python3 p33-dcreload.py webkit 390x844
r p33-flow-wk.log python3 p33-flow.py webkit
r p33-lay3-wk375.log python3 p33-lay3.py webkit 375
r p33-lay3-wk320.log python3 p33-lay3.py webkit 320
r p33-lay3-wk576.log python3 p33-lay3.py webkit 1024x576
r p33-ylat-wk576.log python3 p33-ylat.py webkit 1024 576 statehouse,senate,map
r p33-067-wk.log python3 p33-067.py webkit:390:844
r p33-pa16-wk.log python3 p33-pa16.py webkit 390 844
r p33-quick-ch.log python3 p33-quick.py chromium "Maine,Nebraska,Alaska"
echo "=== Q3 DONE $(date +%T)" >> p33-queue.log
