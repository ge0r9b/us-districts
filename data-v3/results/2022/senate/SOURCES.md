# Sources: 2022 US Senate

| Source | Used for | URL | License / terms |
|---|---|---|---|
| Clerk of the U.S. House, *Statistics of the Congressional Election of November 8, 2022*, compiled from official state sources | statewide official totals (state rows, statewide check); GA general from its footnote | https://clerk.house.gov/member_info/electionInfo/2022/statistics2022.pdf | US government work, public domain |
| MIT Election Data + Science Lab, 2022 precinct-level returns, `individual_states/2022-<st>-local-precinct-general.zip` | county, precinct and district values (all states except CA, ID, IN) | https://github.com/MEDSL/2022-elections-official | CC0 1.0 (per the MEDSL repo/Dataverse records) |
| Statewide Database (UC Berkeley), 2022 general Statement of Vote by SR precinct, `state_g22_sov_data_by_g22_srprec.zip` | CA county, precinct and district values (MEDSL 2022 has no CA Senate rows) | https://statewidedatabase.org/pub/data/G22/state/state_g22_sov_data_by_g22_srprec.zip | public data; credit the Statewide Database (see statewidedatabase.org) |
| Idaho Secretary of State, 2022 General Election canvass files (`2022_General_Canvass.zip` → `22 General Statewide - Precinct.xlsx`, sheet `US Sen`), linked from https://voteidaho.gov/election-results/ | ID county, precinct and district values (replaces MEDSL ID) | https://archive.sos.idaho.gov/elections/data/results/2022/2022_General_Canvass.zip | Idaho public record |
| Indiana Election Division, 2022 General Election results (final), "Download Offices data for Excel" | IN county, precinct and district values (replaces MEDSL IN) | https://enr.indianavoters.in.gov/archive/2022General/download/AllOfficeResults.csv | Indiana public record |
| MEDSL 2024 precinct returns (`individual_states/<st>24.zip`) | only to match MEDSL 2024 precincts to the v2 2024 polygons, the 2022 → 2024 bridge | https://github.com/MEDSL/2024-elections-official | CC0 1.0 |
| v2 2024 precinct polygons `v2/data/precincts2024/<State>.js` | the polygons the 2022 values sit on (v2 has no 2022 polygons) | this repo | NYT part: C-UDA, non-commercial (see v2/data/COVERAGE.md) |
| v2 district shapes `v2/data/uscd.js`, `ussldu.js`, `ussldl.js`, `ussch.js`; GEOIDs from `data-v3/geo/*.csv` | district layers | this repo | Census TIGER (public domain) |

Not used: OpenElections (no Idaho or Indiana 2022 files in openelections-data-id / -in); VEST 2022 (not needed after MEDSL + SWDB). The FEC 2022 file was not needed because the Clerk has every candidate.

Raw downloads (kept on the box at `/workspace/sen22/raw/`, not committed), SHA-256, retrieved 2026-10-18. The MEDSL 2022 ID and IN zips are listed but no longer used for any rows (replaced by the state files below):
```
c7c8d36011097cf9452cbfadcd9a2cbcef7757bcd316a0d62318e80c643388d5  2022-ak.zip
583f813604c4c9cdc3570cdbf7ab96ba69bb00c761df453ff7ca227e40fddd79  2022-al.zip
62b30f0e13eb703fb4933b8f5fcb21015edbd93782c05308c032dfd858d7076a  2022-ar.zip
0c2391b601a0180563fdf93736002c91bb3a26538535e1db7995bc391e2766db  2022-az.zip
39f79588ca56a53d9820901e5435920d6f70aeec258eab48c7e8e7f1676542af  2022-ca.zip
022bda98eb75237106e038c281379c047cb38682a717ad7f8038487d3774ec59  2022-co.zip
8c5265481e2cd5b2589f9af8d93c87fbe90709e330fc43c206eb3a9ee1433d8b  2022-ct.zip
434ed98274d82cae45c2a65f288c03fdb511788c250fc58d8627a9d307ff1e33  2022-fl.zip
92d77246fefe0d46f87bf0f1d3ff722e1a1b1574b08a25bde9eb13ee1933339c  2022-ga.zip
2177b7a872056f0dd4f0b890d50cd152b0f55bf45e684e1424ebf097ef58fdb5  2022-hi.zip
db5eb42db50cd11687c63bdd5773aa91fece6d31997d3b82eefabf7338d344a8  2022-ia.zip
0741d001efa90e00f250ae6a2781c819f25915d64ca14bebc20a99cd28a752d2  2022-id.zip
6e7322c18c0b54209edf140eb490718ce335a4703e7f99e37b54765eaee292d3  2022-il.zip
a9a3713a230c8060cada7469052fe4912ff59cec727aa2e3bd16908b8c0c219c  2022-in.zip
4cc7ea7f493b79b7b1c7dc391b88ea92c0b946dd3acbd06929b5118cd680a898  2022-ks.zip
af2e2ad9ee83268f3ccd22f6d3ad4e93db297dc80324750df66bd268d085a36d  2022-ky.zip
3120fa83fae338062e7e3979b9a5a9073661134b898eaceefdb4a3e5ea9bdff4  2022-la.zip
277f094d49575399b56071e8d51c6bba0099b500de702980ff2a47bdcc593cd9  2022-md.zip
f44de8fd7d2a11bfc0eed71b13ea7359bededd15174d71d48e85819c60f281e0  2022-mo.zip
df4cb07431f1b68036d490ddcc53a44dd37066f0f49bf7b99a52273ca80ef2cb  2022-nc.zip
9a44f1348c89ba39cccf4b61a09d3a4ca673c667536f5410e30a18ba10e33228  2022-nd.zip
6f50ab9884c6e690092e1338c41f9af5f491c24616c91c5dd897734a0321d61c  2022-nh.zip
2dded5c9520e3762af4429bc1961b83084b2a3b78a1d6b15f0c97a6353404a67  2022-nv.zip
7de9f4974e6ab397e181f411acd1b2c749b349d85aaae28bee378f7a41165dab  2022-ny.zip
3cc26dccb56b424e87daee75bd831de4265eaafc44713d64bb363cdd12fa65e3  2022-oh.zip
9526b85ec712c66e50ce039564166a0f34c39933f563cb20d949bba1d44ce7d9  2022-ok.zip
3a9b1ddb0eafc8cb922853f29bf7f88faa608b81fa981b2be2d6953805a7790e  2022-or.zip
3864c6827cea27ad489a1536be41857b2417d6590de94a6785540f77732bc29d  2022-pa.zip
3f0ca616aa8768cd1126d8f372bab13161973c8c2af0eb466380d40175687a19  2022-sc.zip
16921e945fa15de1d7afc5164c4dac8bb0397416fb39154aa531f4b86bb5cecb  2022-sd.zip
50df58615938799d77792d38137320f06f6ab01594b8089749886574bb420d58  2022-ut.zip
d89e103ea0d6d8072b13acd2fbee56f8ccf7b9e83da49e684651bc8ad4e89eb5  2022-vt.zip
b077669a89fee36a2b555ae1b67318ef3055c4b199b948ac689cc1330d4bf521  2022-wa.zip
2b9fe60f0704937b48cdb78ef079044f7e645e4baac642f6a2e2bb4cd02fcca3  2022-wi.zip
ef9b8cefcc44bebbdc4928bf346b50e00a72dd3bb54a71ed93ec60d4ebf47690  clerk_statistics2022.pdf
e1cf79cea43f8c117cd81c4ce74a9ad51ae7b6b9e5f30615bc582140512af249  state_g22_sov_data_by_g22_srprec.zip
27aac1e2c391b2d50541bc231550c48c101385714eeda53b92bd4fd6e83d5a69  id_sos/2022_General_Canvass.zip
3edb9c7dc674255227b4ea4e37c82584dfecfcce6a681cac6982760a5bf6189a  in_ied/AllOfficeResults.csv
```
MEDSL 2024 zips used only for the bridge, in addition to the 33 listed in `../../2024/senate/SOURCES.md` (`/workspace/sen22/raw24/`):
```
e501940935cccbf5df3884aa0a61cca7e4b61b7fcf78a861f45ecb9ea73b23f6  ak24.zip
4f961a27fd32497bee74601438d738e337b6e07d81910d4b1765b464dee0d024  al24.zip
22b54a19a514588c6f8b23f4975464baf659d6a22d469ba3b6b369461b9dce06  ar24.zip
a9e1758171d6bc32894fb832177f1bc4222c9fc56c492b7c43d1e51c0392cecd  co24.zip
36a86477d771ef5b6cf2a033cf941bbfe28eca5adab57ba803836f6b5bc954ed  ga24.zip
c31797ace26c06f9504ec4a815cfb717b8619507f529726ac4572dea68ecb7b2  ia24.zip
812fb85c14005fa2aded0fe0848d3ea4f039321c421c71b40dd2cda645af4a71  id24.zip
0fd0487cedb5c25437c667faedb9e0d58a65d8fb630d0af09c1f971e50d57457  il24.zip
9e18bccfb97333c735ca0ac08b01bf5de61cfd4fa1726305834254ba1a00b0e6  ks24.zip
6d23baa797cb794aa05e842558fc2b78314f4fef39ab9aafd9822833f73cefa9  ky24.zip
ec8bb9aae15a4a0508383e744ea0ffde9f45446bcdbb90410cc662a94a26346c  la24.zip
195f645d5555b6cd755b269d298d0a0be00caa5c9d68ce4ced3e8a9add22897a  nc24.zip
c867ecc11624afe64886754403c695e676343d0d0fa43868ec9a241d4aa5d6bd  nh24.zip
8ff2595d40fc86748ab4e8f908276c0dc12adc06f58e9ad261859998e7c7588b  ok24.zip
e6605eab53ca6a32e42e867bc753e203220855723e56ac5d360fa0115b7da34e  or24.zip
0a55d286d4a1034b801e27e7ca120c67cd98aa93b31510878da58a00866af599  sc24.zip
06517ec31937a56860cde5a6e105cd668bc6b2915e6d19d6eb8db693a0d91a3c  sd24.zip
```
