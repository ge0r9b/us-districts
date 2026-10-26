# Oct 26 ~10 AM (1623) batch 3: QA-124 / QA-127 / QA-113 / QA-130
(timeout 700 python3 d26h10-cityN.py chromium 390x844 "Pennsylvania|Allegheny|Pittsburgh city|Baldwin#Pennsylvania|Allegheny|Baldwin township|Pittsburgh#North Carolina|Alamance|Burlington city|Graham;West Graham#Wisconsin|Kenosha|Kenosha city|Pleasant Prairie;SOMERS" ch390 > d26h10-cityN-ch390.log 2>&1; timeout 400 python3 d26h10-q127.py > d26h10-q127.log 2>&1; touch d26h10-r3a.done) &
(timeout 700 python3 d26h10-geo2.py chromium 320x568 map > d26h10-geo2-ch320.log 2>&1; timeout 500 python3 d26h10-q130.py webkit 390x844 "Pittsburgh|Boston" > d26h10-q130-we390.log 2>&1; touch d26h10-r3b.done) &
wait
