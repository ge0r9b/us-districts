#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1614p35-queueC.log; timeout 1100 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1614p35-queueC.log; }
r b1614p35-lay3-ch390.log python3 p35-lay3.py chromium 390
r b1614p35-pa16-ch.log python3 p35-pa16.py chromium 390 844
r b1614p35-menus-ch.log python3 p35-menus.py chromium
r b1614p35-own-ch.log python3 p35-own.py chromium iphone390
r b1614p35-lay3-ch768.log python3 p35-lay3.py chromium 1024x768
r b1614p35-lay3-ch576.log python3 p35-lay3.py chromium 1024x576
echo "=== ALL C DONE $(date +%T)" >> b1614p35-queueC.log
