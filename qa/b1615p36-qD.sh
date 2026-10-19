#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1615p36-queueD.log; timeout 700 nice -n 5 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1615p36-queueD.log; }
r b1615p36-ylat-ch576.log python3 p36-ylat.py chromium 1024 576 statehouse,map
r b1615p36-lat-ch.log python3 p36-lat.py chromium 390x844
echo "=== ALL D DONE $(date +%T)" >> b1615p36-queueD.log
