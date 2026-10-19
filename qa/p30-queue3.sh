#!/bin/bash
cd /workspace/w/lanes/qa/qa
while ! grep -q 'Q2 DONE' p30-queue.log; do sleep 5; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p30-queue.log; timeout 400 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p30-queue.log; }
r p30-globe-ch.log p30-globe.py chromium
r p30-globe-wk.log p30-globe.py webkit
echo "=== Q3 DONE $(date +%T)" >> p30-queue.log
