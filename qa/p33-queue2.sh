#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p33-queue.log; timeout 900 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p33-queue.log; }
while pgrep -f p33-queue.sh >/dev/null; do sleep 5; done
r p33-quick-ch.log python3 p33-quick.py chromium "Maine,Nebraska,Alaska"
echo "=== Q2 DONE $(date +%T)" >> p33-queue.log
