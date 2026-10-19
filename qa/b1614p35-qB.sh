#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1614p35-queueB.log; timeout 1100 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1614p35-queueB.log; }
r b1614p35-addr-wk.log python3 p35-addr2.py webkit 390x844 list,listr,map
r b1614p35-dcg-wk.log env ONLY=webkit python3 p35-orch-list-dc-globe.py $L
r b1614p35-cmr-wk.log env ONLY=webkit python3 p35-orch-city-map-reload.py $L
r b1614p35-states-wk.log python3 p35-states.py webkit 390x844 "Florida:Miami-Dade:drill,New York:Kings:drill" x r1614
r b1614p35-dcreload-wk.log python3 p35-dcreload.py webkit 390x844
r b1614p35-lay3-wk375.log python3 p35-lay3.py webkit 375
r b1614p35-lay3-wk320.log python3 p35-lay3.py webkit 320
r b1614p35-flow-wk.log python3 p35-flow.py webkit iphone390 ipad1024x768
echo "=== ALL B DONE $(date +%T)" >> b1614p35-queueB.log
