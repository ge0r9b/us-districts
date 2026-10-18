set -x
cd /workspace/w/lanes/qa/qa
curl -s https://ge0r9b.github.io/us-districts/v2/index.html | sed -n 9p
timeout 900 python3 p13-addr2.py chromium 375 667
timeout 900 python3 p13-addr2.py webkit 1024 576
timeout 600 python3 p13-dist2.py chromium 390 844
timeout 900 python3 p13-thumbs.py 390 AL,DE
timeout 900 python3 p13-layout.py chromium 375
timeout 900 python3 p13-layout.py chromium 320
timeout 900 python3 p13-layout.py chromium 1024x576
timeout 1200 python3 p13-flow.py webkit iphone375 iphone320 ipad1024x576
curl -s https://ge0r9b.github.io/us-districts/v2/index.html | sed -n 9p
echo ALLDONE
