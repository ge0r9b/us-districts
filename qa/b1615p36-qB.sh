#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1615p36-queueB.log; timeout 900 nice -n 5 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1615p36-queueB.log; }
r b1615p36-sort-ch.log python3 p36-fresh.py chromium 390x844 sort
r b1615p36-charts-ch.log python3 p36-fresh.py chromium 390x844 charts
r b1615p36-drag-ch.log python3 p36-fresh.py chromium 1024x768 drag
r b1615p36-drag-wk.log python3 p36-fresh.py webkit 1024x768 drag
r b1615p36-addr-ch.log python3 p36-addr2.py chromium 390x844 list,map
echo "=== ALL B DONE $(date +%T)" >> b1615p36-queueB.log
