#!/bin/bash
cd /workspace/w/lanes/qa/qa
while pgrep -f 'p27-queue[23].sh' >/dev/null; do sleep 3; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p27-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p27-queue.log; }
r p27-lay3-wk390.log p27-lay3.py webkit 390
r p27-lay3-ch768.log p27-lay3.py chromium 1024x768
echo "=== ALL DONE 4 $(date +%T)" >> p27-queue.log
