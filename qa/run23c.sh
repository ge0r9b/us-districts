timeout 400 python3 h2300-alprobe.py webkit 390x844 "Maine,District of Columbia,Alaska,Colorado" > h2300-alprobe.log 2>&1; echo al
timeout 300 python3 h2300-pa16.py webkit 390 844 > h2300-pa16.log 2>&1; echo pa
timeout 400 python3 h2300-col16.py chromium iphone390 > h2300-col16.log 2>&1; echo col
timeout 300 python3 h2300-sortchart.py chromium 375x667 Colorado Denver > h2300-sortchart.log 2>&1; echo sc
timeout 300 python3 h2300-menus.py chromium iphone375 ipad1024x768 > h2300-menus.log 2>&1; echo me
timeout 900 python3 h2300-addr.py webkit 390x844 map,list > h2300-addr.log 2>&1; echo ad
