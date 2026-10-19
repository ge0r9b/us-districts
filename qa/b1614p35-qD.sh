#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1614p35-queueD.log; timeout 1100 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1614p35-queueD.log; }
r b1614p35-cmr-ch.log env ONLY=chromium python3 p35-orch-city-map-reload.py $L
r b1614p35-states-ch.log python3 p35-states.py chromium 390x844 "Florida:Miami-Dade:ranges+drill,New York:Kings:drill" x r1614
r b1614p35-dcreload-ch.log python3 p35-dcreload.py chromium 390x844
r b1614p35-cmp.log python3 cmp.py
r b1614p35-other-ch.log python3 p35-other.py chromium
r b1614p35-chip-ch.log python3 p35-chip.py chromium
r b1614p35-074-ch.log python3 p35-074.py chromium 390x844 Ohio,Texas,California
echo "=== ALL D DONE $(date +%T)" >> b1614p35-queueD.log
