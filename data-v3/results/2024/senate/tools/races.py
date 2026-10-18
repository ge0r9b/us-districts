"""2024 US Senate races: (state, race_id) -> d-slot surname, r surname. race 'regular' = full term; 'special' = unexpired term (CA, NE).
d slot rule: the Democratic nominee, except where an independent (not a Republican) outpolled the Democratic nominee statewide;
then d = that independent (ME King, VT Sanders [no Democratic nominee], NE regular Osborn [no Democratic nominee]). r = Republican nominee."""
RACES = {
 ('AZ','regular'):('GALLEGO','LAKE'), ('CA','regular'):('SCHIFF','GARVEY'), ('CA','special'):('SCHIFF','GARVEY'),
 ('CT','regular'):('MURPHY','COREY'), ('DE','regular'):('ROCHESTER','HANSEN'), ('FL','regular'):('MUCARSEL-POWELL','RICK SCOTT'),
 ('HI','regular'):('HIRONO','MCDERMOTT'), ('IN','regular'):('MCCRAY','BANKS'), ('ME','regular'):('KING','KOUZOUNAS'),
 ('MD','regular'):('ALSOBROOKS','HOGAN'), ('MA','regular'):('WARREN','DEATON'), ('MI','regular'):('SLOTKIN','ROGERS'),
 ('MN','regular'):('KLOBUCHAR','ROYCE WHITE'), ('MS','regular'):('PINKINS','WICKER'), ('MO','regular'):('KUNCE','HAWLEY'),
 ('MT','regular'):('TESTER','SHEEHY'), ('NE','regular'):('OSBORN','FISCHER'), ('NE','special'):('LOVE','RICKETTS'),
 ('NV','regular'):('ROSEN','BROWN'), ('NJ','regular'):('ANDY KIM','BASHAW'), ('NM','regular'):('HEINRICH','DOMENICI'),
 ('NY','regular'):('GILLIBRAND','SAPRAICONE'), ('ND','regular'):('CHRISTIANSEN','CRAMER'), ('OH','regular'):('SHERROD','MORENO'),
 ('PA','regular'):('CASEY','MCCORMICK'), ('RI','regular'):('WHITEHOUSE','MORGAN'), ('TN','regular'):('GLORIA JOHNSON','BLACKBURN'),
 ('TX','regular'):('ALLRED','CRUZ'), ('UT','regular'):('GLEICH','CURTIS'), ('VT','regular'):('SANDERS','MALLOY'),
 ('VA','regular'):('KAINE','CAO'), ('WA','regular'):('CANTWELL','GARCIA'), ('WV','regular'):('ELLIOTT','JUSTICE'),
 ('WI','regular'):('BALDWIN','HOVDE'), ('WY','regular'):('MORROW','BARRASSO')}
FLAGGED = {('ME','regular'):'Angus King (I) in d; Democratic nominee David Costello counted in total only',
           ('VT','regular'):'Bernie Sanders (I) in d; no Democratic nominee on the ballot',
           ('NE','regular'):'Dan Osborn (independent, "By Petition") in d; no Democratic nominee on the ballot'}
# not votes for a candidate: excluded from t
NONVOTE = ('UNDERVOTE','OVERVOTE','OVER VOTE','UNDER VOTE','TOTAL VOTES','TOTAL BALLOTS','CONTEST TOTAL','BLANK','VOID','SPOILED','INVALID','NONE OF THESE')
def is_nonvote(name):
    u = name.upper(); return any(k in u for k in NONVOTE)
def slot(st, race, name):
    d, r = RACES[(st, race)]; u = ' '+name.upper().replace('.','').replace(',',' ')+' '
    def has(s): return (' '+s+' ') in u if ' ' not in s else s in u
    if has(d): return 'd'
    if has(r): return 'r'
    return 'o'
USPS = {'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
NAME = {v:k for k,v in USPS.items()}
