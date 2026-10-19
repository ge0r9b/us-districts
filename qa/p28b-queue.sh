#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p28-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p28-queue.log; }
r p28b-067.log p28b-067.py webkit:390:844,chromium:375:667
r p28b-lay3-wk390.log p28b-lay3.py webkit 390
r p28b-lay3-ch768.log p28b-lay3.py chromium 1024x768
r p28b-back2-wk.log p28b-back2.py webkit 390,1024x768 2
r p28b-back2-ch.log p28b-back2.py chromium 390 2
r p28b-addr-ch.log p28b-addr.py chromium
echo "=== ALL DONE B $(date +%T)" >> p28-queue.log
