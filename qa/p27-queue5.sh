#!/bin/bash
cd /workspace/w/lanes/qa/qa
while pgrep -f 'p27-queue4.sh' >/dev/null; do sleep 3; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p27-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p27-queue.log; }
r p27-own-ch390.log p27-own.py chromium iphone390
echo "=== ALL DONE 5 $(date +%T)" >> p27-queue.log
