#!/bin/bash
cd /workspace/w/lanes/qa/qa
L=https://ge0r9b.github.io/us-districts/v2/
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p34-queue.log; timeout 900 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p34-queue.log; }
echo "=== $(date +%T) pass 34 restart (1613)" >> p34-queue.log
r p34-addr2-ch.log python3 p33-addr2.py chromium 390x844 list
r p34-states-ch.log python3 p33-states.py chromium 390x844 "Florida:Miami-Dade:types+drill" x r1613
echo "=== STAGE1 DONE $(date +%T)" >> p34-queue.log
r p34-cot-wk.log env ONLY=webkit python3 p33-orch-county-own-totals.py $L
r p34-addr2-wk.log python3 p33-addr2.py webkit 390x844 list,map
r p34-states-wk.log python3 p33-states.py webkit 390x844 "Michigan:Wayne:types,New York:Kings:types+drill" x r1613
echo "=== STAGE2 DONE $(date +%T)" >> p34-queue.log
r p34-cmp.log python3 cmp.py
r p34-flow-ch.log python3 p33-flow.py chromium
r p34-dcg-wk.log env ONLY=webkit python3 p33-orch-list-dc-globe.py $L
echo "=== ALL DONE $(date +%T)" >> p34-queue.log
