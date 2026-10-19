#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p32-queue.log; timeout 900 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p32-queue.log; }
laneA(){
r p32-orch-ch.log env ONLY=chromium python3 p32-orch-list-dc-globe.py $L
r p32-globe-ch390.log python3 p32-globe.py chromium 390x844
r p32-addr-ch.log python3 p32-addr.py chromium 390x844 allstates,phila,allstates
r p32-globe-ch1024.log python3 p32-globe.py chromium 1024x768
r p32-addr2-ch.log python3 p32-addr2.py chromium 390x844 list,map
r p32-chip-ch.log python3 p32-chip.py
r p32-074-ch.log python3 p32-074.py chromium 390x844 Ohio,Texas,California
}
laneB(){
r p32-states-b.log python3 p32-states.py chromium 390x844 "Texas,Florida,New York,Michigan,Arizona" types,drill b
r p32-other-ch.log python3 p32-other.py chromium
r p32-own-ch390.log python3 p32-own.py chromium iphone390
}
laneA & laneB & wait
echo "=== CH-FUNC DONE $(date +%T)" >> p32-queue.log
r p32-ylat-ch576.log python3 p32-ylat.py chromium 1024 576 statehouse,senate,map
r p32-flow-ch.log python3 p32-flow.py chromium
echo "=== CH DONE $(date +%T)" >> p32-queue.log
laneW(){
r p32-orch-wk.log env ONLY=webkit python3 p32-orch-list-dc-globe.py $L
r p32-globe-wk390.log python3 p32-globe.py webkit 390x844
r p32-addr-wk.log python3 p32-addr.py webkit 390x844 phila,allstates
r p32-globe-wk1024.log python3 p32-globe.py webkit 1024x768
}
laneW2(){
r p32-lay3-wk390.log python3 p32-lay3.py webkit 390
r p32-lay3-wk1024.log python3 p32-lay3.py webkit 1024x768
r p32-pa16-wk.log python3 p32-pa16.py webkit 390 844
r p32-menus-wk.log python3 p32-menus.py webkit
}
laneW & laneW2 & wait
echo "=== ALL DONE $(date +%T)" >> p32-queue.log
