# Sources: 2024 US Senate

| Source | Used for | URL | License / terms |
|---|---|---|---|
| Clerk of the U.S. House, *Statistics of the Presidential and Congressional Election of November 5, 2024* (published Mar 10, 2025), compiled from official state sources | statewide official totals (state rows, statewide check) | https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf | US government work, public domain |
| MIT Election Data + Science Lab, 2024 precinct-level returns, `individual_states/<st>24.zip` (also Harvard Dataverse doi:10.7910/DVN/NYTPDU; Senate subset doi:10.7910/DVN/ZCM3BN) | county, precinct and district values | https://github.com/MEDSL/2024-elections-official | CC0 1.0 (per the Dataverse record) |
| v2 2024 precinct polygons, `v2/data/precincts2024/<State>.js` (NYT 2024 precinct map + Census/VEST, merged; see v2/data/COVERAGE.md) | polygons the Senate precinct values sit on; the president 2024 values used to match | this repo | NYT part: C-UDA, non-commercial (see COVERAGE.md) |
| v2 district shapes `v2/data/uscd.js`, `ussldu.js`, `ussldl.js`, `ussch.js`; GEOIDs from `data-v3/geo/*.csv` | district layers | this repo | Census TIGER (public domain) |

Not used: the FEC 2024 file (`federalelections2024.xlsx` is not published yet; the FEC page lists only presidential 2024 results). VEST 2024 is subscription-only (UF Election Lab). OpenElections was not needed.

Raw downloads (kept on the box at `/workspace/sen24/raw/`, not committed, about 100 MB), SHA-256, retrieved 2026-10-18:
```
bff8059944b3f58f13228518f9fbeff58a556677d5ab05ab49ca5a4a524555a6  az24.zip
6b27046e88c982c585f593b0defc01ab1e912a4de529bf3f2909449a87682a3f  ca24.zip
e997c5e0b734e334625814871d464fb70d93a3d9720f295e06c8f124c0b508da  ct24.zip
608070838aca6776139d6de7624b396ccb83ab80f0b5ba07d8ede577eb7b749a  de24.zip
192e85fa68ce8e6711c6c13f0a525e3ef6cac95236fd1f0888b3ecc9bc02eebf  fl24.zip
4878049b21d84970b59eb95f70ba2f00c72bf53d87aa1990afd609d5bf4591b0  hi24.zip
0fbb2d8ec7e9446e3ba35a5a57f733f25f4653804188af7230fbc384619758dc  in24.zip
a6b3ed9a62332d48ce585afa63f45351610ba2b9590482a591881361e493762a  ma24.zip
93ebe28bcb6fc2df538a5989d0802c1a7980618bf120c67535448f4177d578cc  md24.zip
e6f3f6068004d8627aceb0a029886cd0d2e6685d7790c708e6e0989857ed31a1  me24.zip
6d6a8a9d61f9568f8390678dc822042643cb975d7fecf9d3dcd2d370ce92a6d9  mi24.zip
57255a4da067d8fb686815aae6afc29f91543878be240cb0781ca1a50cca24e5  mn24.zip
48db595d464b1b25570313fe7c2fc06be46ae7189b92ad457d3f523e462ecf84  mo24.zip
a20fe0439114878a9102a0c14febb1d3cc0338618dae18432924c05b10ab3181  ms24.zip
bdd07192021d298d0ad69446f3c6fc6b3bacb661715958a16087c483168dd422  mt24.zip
15e7f0be4db268e007d87c4512491e02e9a8fa9ced57a8a7807df786667b91fd  nd24.zip
34b3334e65bb7fc35469e399fbf2caf4df18434557e654901966f634028b05ab  ne24.zip
1b7652f2ca65d70dbe6df2ea4b61758909e76864669ca1cb5a2563392a62be56  nj24.zip
82f44603db89e7cd0034cdec1681df0da811f245b63b6a9242bd0398228c0d58  nm24.zip
719b6e32a6d6c62b0eaa6433e52885028bd5c9330fbb081489149aad777a6dc1  nv24.zip
5c3608ba2a74b999f48e181abb764d6ccf91b5506a011f2fe873b8e52f8b2508  ny24.zip
b6b9ff0b4192c1bd2a86ecc7685e8cc42305cb14a002025acc41c49fbc5543fd  oh24.zip
f134e829a9df0925209f8cad77fc2448c8c780400e2a0190de1d42866f4075ee  pa24.zip
351b15dc031b83626e16b1d63f2b93fd47cb997018c1541dcdff9a6c9a97ef1e  ri24.zip
363f8de018de7afa39843c4e09ad3f661966323a7286911f3852dc1a2706e2ca  tn24.zip
9202fc83607e296bc38be68bde0f0121a0eadb0b6edee4a115c6cf81fd00371f  tx24.zip
ba5a98ceb3de09737c03c5ff7f3cb61520658ed62e05ec709aae67f2fbdd7741  ut24.zip
bab46d1a9bf925eb806673af50dd775334542ad2d5b924286585961b8a99bd68  va24.zip
4351cacd9a326950826e537e575e393d670c716c22c6148c4caae514bfdfb9e8  vt24.zip
ee73bdffa3ddb95c546f1e77fa9c7b71ce7a25fdd5bab7d5b60a9711e8d7532c  wa24.zip
1dd9b34caae5bda405087f909bf08522e2c58b407ef93529aa92c170a2444b09  wi24.zip
44b84cd72005838eb5bcc6be084960708e2163da40590d8da28d8afa92bdd153  wv24.zip
90891ad168f5c907aa2520eb21f7f1734caf42d80f53ef2ef35b125c459d7fc6  wy24.zip
d4ba800fc17135b616ae556c92861080ab962d95916ace34b546c5aac824aec4  clerk_statistics2024.pdf
```
