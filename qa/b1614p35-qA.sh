#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1614p35-queue.log; timeout 1100 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1614p35-queue.log; }
r b1614p35-addr-ch.log python3 p35-addr2.py chromium 390x844 list,listr,map
r b1614p35-dcg-ch.log env ONLY=chromium python3 p35-orch-list-dc-globe.py $L
r b1614p35-cmr-ch.log env ONLY=chromium python3 p35-orch-city-map-reload.py $L
r b1614p35-states-ch.log python3 p35-states.py chromium 390x844 "Florida:Miami-Dade:ranges+drill,New York:Kings:drill" x r1614
r b1614p35-dcreload-ch.log python3 p35-dcreload.py chromium 390x844
r b1614p35-cmp.log python3 cmp.py
r b1614p35-flow-ch.log python3 p35-flow.py chromium
r b1614p35-other-ch.log python3 p35-other.py chromium
r b1614p35-chip-ch.log python3 p35-chip.py chromium
r b1614p35-074-ch.log python3 p35-074.py chromium 390x844 Ohio,Texas,California
r b1614p35-pa16-ch.log python3 p35-pa16.py chromium 390 844
r b1614p35-menus-ch.log python3 p35-menus.py chromium
r b1614p35-own-ch.log python3 p35-own.py chromium iphone390
r b1614p35-lay3-ch390.log python3 p35-lay3.py chromium 390
r b1614p35-lay3-ch768.log python3 p35-lay3.py chromium 1024x768
r b1614p35-lay3-ch576.log python3 p35-lay3.py chromium 1024x576
echo "=== ALL A DONE $(date +%T)" >> b1614p35-queue.log
