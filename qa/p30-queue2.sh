#!/bin/bash
cd /workspace/w/lanes/qa/qa
while ! grep -q 'ALL DONE' p30-queue.log; do sleep 5; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p30-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p30-queue.log; }
r p30-other-ch.log p30-other.py chromium
r p30-067-ch.log p30-067.py chromium:375:667
echo "=== Q2 DONE $(date +%T)" >> p30-queue.log
