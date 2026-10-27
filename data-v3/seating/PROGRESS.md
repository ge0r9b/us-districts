# results matching – progress log (2026-10-18)
Pipeline: tools/build_v3data.py -> tools/results/congress_parse.py -> tools/results/bp_district_parse.py -> tools/build_results.py -> tools/build_pack.py
Raw caches: src/results (FEC, Clerk 2024, MEDSL Senate, Klarner SLERs), src/bp/districts/*.html.gz (6,812 pages), src/bp/court_elections/*.html
Done: Congress 2016-2024 (+specials/runoffs), state chambers (Ballotpedia district pages + Klarner fill/cross-check), courts (Ballotpedia), back-fill, pack.
- 10:19 rerun done: FL/WA/ID 2024 linked fully; docs updated
- 10:30 dropped CA/KS/WV courts + pre-2017 court contests (build filters), orphan people pruned; validated
- 12:03 city councils + mayors added (50 bodies); validated; keys stable
- 12:16 added Indianapolis, San Francisco, Nashville, DC, Louisville councils + mayors (b 188-197, 10 bodies; 198 total); DC delegate contests kept out of results (ST50 = legislature states); validated (0 replay mismatches, 0 overlaps, 0 orphans/dangling, first 188 keys unchanged)
- 00:02 shared-cid fix: (slug,state)-only linking, cid_links.csv + cid_collisions.csv, MI Rogers -> R000572; validated
