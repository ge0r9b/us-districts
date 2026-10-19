#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1615p36-queue.log; timeout 900 nice -n 5 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1615p36-queue.log; }
r b1615p36-lay3-wk390.log python3 p36-lay3.py webkit 390
r b1615p36-lay3-wk768.log python3 p36-lay3.py webkit 1024x768
r b1615p36-lay3-ch320.log python3 p36-lay3.py chromium 320
r b1615p36-lay3-ch576.log python3 p36-lay3.py chromium 1024x576
r b1615p36-pa16-wk.log python3 p36-pa16.py webkit 390 844
r b1615p36-own-ch.log python3 p36-own.py chromium iphone390
r b1615p36-menus-ch.log python3 p36-menus.py chromium
echo "=== ALL A DONE $(date +%T)" >> b1615p36-queue.log
