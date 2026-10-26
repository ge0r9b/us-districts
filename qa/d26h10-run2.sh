# Oct 26 ~10 AM (1623) batch 2
(timeout 900 python3 d26h10-own.py webkit iphone390 ipad1024x768 > d26h10-own-we.log 2>&1; timeout 600 python3 d26h10-col16.py chromium iphone375 > d26h10-col16-ch375.log 2>&1; timeout 600 python3 d26h10-menus.py webkit iphone320 ipad1024x576 > d26h10-menus-we.log 2>&1; touch d26h10-r2a.done) &
(timeout 900 python3 d26h10-sortnum.py chromium 375x667 GA Fulton > d26h10-sortnum-ch375-GA.log 2>&1; timeout 900 python3 d26h10-sortnum.py webkit 1024x576 IL Cook > d26h10-sortnum-we1024x576-IL.log 2>&1; timeout 400 python3 d26h10-q091.py webkit > d26h10-q091-we.log 2>&1; touch d26h10-r2b.done) &
(for a in "webkit 375" "chromium 320" "webkit 1024x576" "chromium 390"; do set -- $a; timeout 700 python3 d26h10-lay3.py $1 $2 > d26h10-lay3-${1:0:2}-$2.log 2>&1; done; touch d26h10-r2c.done) &
wait
