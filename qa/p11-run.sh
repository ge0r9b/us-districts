set -x
cd /workspace/w/lanes/qa/qa
timeout 900 python3 cmp.py > p11-cmp.log 2>&1
timeout 900 python3 p11-retest.py chromium > p11-retest-ch.log 2>&1
timeout 1500 python3 p11-flow.py chromium > p11-flow-ch.log 2>&1
for s in 390 375 320 1024x576 1024x768; do timeout 900 python3 p11-layout.py chromium $s > p11-layout-$s.log 2>&1; done
timeout 900 python3 p11-restore.py > p11-restore.log 2>&1
timeout 1500 python3 p11-flow.py webkit > p11-flow-wk.log 2>&1
echo ALLDONE
