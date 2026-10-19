#!/bin/bash
cd /workspace/w/lanes/qa/qa
r(){ log=$1; shift; echo "=== $(date +%T) start $log" >> b1615p36-queueC.log; timeout 1000 nice -n 5 "$@" > $log 2>&1; echo "=== $(date +%T) end $log rc=$?" >> b1615p36-queueC.log; }
r b1615p36-states-ch.log python3 p36-states.py chromium 390x844 "Colorado:Denver:types+drill,Minnesota:Hennepin:types+drill,Virginia:Fairfax:types+drill,Washington:King:types+drill" x r1615
r b1615p36-addr-wk.log env ONLYA=CO,GA,NV,OH python3 p36-addr2.py webkit 390x844 list
echo "=== ALL C DONE $(date +%T)" >> b1615p36-queueC.log
