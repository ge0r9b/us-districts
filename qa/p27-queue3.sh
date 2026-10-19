#!/bin/bash
cd /workspace/w/lanes/qa/qa
while pgrep -f p27-queue2.sh >/dev/null; do sleep 3; done
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> p27-queue.log; timeout 600 python3 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> p27-queue.log; }
URL=http://127.0.0.1:8850/v2/ r p27-back2-wk-local1602.log p27-back2.py webkit 390 1
cp b1602p27-back2-webkit.json b1602p27-back2-webkit-local.json 2>/dev/null
URL=http://127.0.0.1:8851/v2/ r p27-back2-wk-local1604.log p27-back2.py webkit 390 1
cp b1604p27-back2-webkit.json b1604p27-back2-webkit-local390.json 2>/dev/null
echo "=== ALL DONE 3 $(date +%T)" >> p27-queue.log
