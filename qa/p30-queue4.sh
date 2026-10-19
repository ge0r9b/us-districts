#!/bin/bash
cd /workspace/w/lanes/qa/qa
while ! grep -q 'Q3 DONE' p30-queue.log; do sleep 5; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p30-queue.log; timeout 500 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p30-queue.log; }
r p30-addr-wk1609.log p30-addr.py webkit 390x844 phila,allstates,phila,tapdc b1609
r p30-back2-wk1609.log p30-back2.py webkit 390 1
echo "=== Q4 DONE $(date +%T)" >> p30-queue.log
