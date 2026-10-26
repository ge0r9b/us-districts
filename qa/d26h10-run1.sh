# Oct 26 ~10 AM (1623) batch 1
(timeout 400 python3 d26h10-backreload.py webkit 375x667 TX Harris > d26h10-backreload-we375.log 2>&1; timeout 400 python3 d26h10-backreload.py chromium 390x844 MA Worcester > d26h10-backreload-ch390.log 2>&1; timeout 600 python3 d26h10-detroit.py > d26h10-detroit.log 2>&1; timeout 600 python3 d26h10-denver.py > d26h10-denver.log 2>&1; touch d26h10-r1a.done) &
(timeout 600 python3 d26h10-addr.py webkit 375x667 list,map > d26h10-addr-we375.log 2>&1; timeout 400 python3 d26h10-crumb.py webkit 1024x768 "Oklahoma:Oklahoma County,Alabama:Jefferson County" > d26h10-crumb-we1024.log 2>&1; timeout 600 python3 d26h10-pa16.py chromium 390 844 > d26h10-pa16-ch390.log 2>&1; touch d26h10-r1b.done) &
(timeout 700 python3 d26h10-lay3.py webkit 390 > d26h10-lay3-we-390.log 2>&1; timeout 700 python3 d26h10-lay3.py chromium 1024x768 > d26h10-lay3-ch-1024x768.log 2>&1; touch d26h10-r1c.done) &
wait
