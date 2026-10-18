"""2022 US Senate races: (state, race) -> (d-slot name token, r-slot name token).
race: 'regular' (full term; GA = Nov 8 general), 'special' (unexpired term: CA, OK), 'runoff' (GA Dec 6).
d slot rule (same as 2024): the Democratic nominee, unless an independent (not a Republican) outpolled the Democratic nominee
statewide or there was no Democratic nominee; then d = that independent. r = the Republican nominee.
Multi-candidate same-party fields: AK (top-four primary, ranked-choice general: first-round votes; r = the Republican with the
most first-round votes, Murkowski; Tshibaka and Kelley in all-others) and LA (jungle election: d = the Democrat with the most votes,
Chambers; r = Kennedy; other Democrats and Republicans in all-others)."""
RACES = {
 ('AL','regular'):('BOYD','BRITT'), ('AK','regular'):('CHESBRO','MURKOWSKI'), ('AZ','regular'):('MARK KELLY','MASTERS'),
 ('AR','regular'):('NATALIE JAMES','BOOZMAN'), ('CA','regular'):('PADILLA','MEUSER'), ('CA','special'):('PADILLA','MEUSER'),
 ('CO','regular'):('BENNET','ODEA'), ('CT','regular'):('BLUMENTHAL','LEVY'), ('FL','regular'):('DEMINGS','RUBIO'),
 ('GA','regular'):('WARNOCK','WALKER'), ('GA','runoff'):('WARNOCK','WALKER'), ('HI','regular'):('SCHATZ','MCDERMOTT'),
 ('ID','regular'):('ROTH','CRAPO'), ('IL','regular'):('DUCKWORTH','SALVI'), ('IN','regular'):('THOMAS M MCDERMOTT','TODD YOUNG'),
 ('IA','regular'):('FRANKEN','GRASSLEY'), ('KS','regular'):('HOLLAND','MORAN'), ('KY','regular'):('BOOKER','RAND PAUL'),
 ('LA','regular'):('CHAMBERS','JOHN KENNEDY'), ('MD','regular'):('VAN HOLLEN','CHAFFEE'), ('MO','regular'):('VALENTINE','SCHMITT'),
 ('NV','regular'):('CORTEZ MASTO','LAXALT'), ('NH','regular'):('HASSAN','BOLDUC'), ('NY','regular'):('SCHUMER','PINION'),
 ('NC','regular'):('BEASLEY','BUDD'), ('ND','regular'):('CHRISTIANSEN','HOEVEN'), ('OH','regular'):('TIM RYAN','VANCE'),
 ('OK','regular'):('MADISON HORN','LANKFORD'), ('OK','special'):('KENDRA HORN','MULLIN'), ('OR','regular'):('WYDEN','PERKINS'),
 ('PA','regular'):('FETTERMAN','OZ'), ('SC','regular'):('MATTHEWS','TIM SCOTT'), ('SD','regular'):('BENGS','THUNE'),
 ('UT','regular'):('MCMULLIN','MIKE LEE'), ('VT','regular'):('WELCH','MALLOY'), ('WA','regular'):('MURRAY','SMILEY'),
 ('WI','regular'):('BARNES','RON JOHNSON')}
FLAGGED = {('UT','regular'):'Evan McMullin (independent) in d; no Democratic nominee on the ballot',
           ('AK','regular'):'ranked-choice: first-round votes; d = Patricia Chesbro (D, top non-Republican); r = Lisa Murkowski (R, most first-round votes); Kelly Tshibaka (R) and Buzz Kelley (R) in all-others',
           ('LA','regular'):'jungle election (Nov 8): d = Gary Chambers Jr. (top Democrat); other Democrats and Republicans in all-others',
           ('GA','regular'):'Nov 8 general (no majority); the decisive Dec 6 runoff is race runoff',
           ('ND','regular'):'Katrina Christiansen (Democratic-NPL) in d; independent Rick Becker in all-others'}
NONVOTE = ('UNDERVOTE','OVERVOTE','OVER VOTE','UNDER VOTE','TOTAL VOTES','TOTAL BALLOTS','CONTEST TOTAL','BLANK','VOID','SPOILED','INVALID',
           'NONE OF THESE','PUBLIC COUNTER','ABSENTEE / MILITARY','AFFIDAVIT','NOT QUALIFIED','BALLOTS CAST','REGISTERED VOTERS')
def is_nonvote(name):
    u = name.upper(); return any(k in u for k in NONVOTE)
def slot(st, race, name):
    d, r = RACES[(st, race)]; u = ' '+name.upper().replace('.','').replace(',',' ').replace('’','').replace("'",'')+' '
    def has(s): return (' '+s+' ') in u if ' ' not in s else s in u
    if has(d): return 'd'
    if has(r): return 'r'
    return 'o'
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../2024/senate/tools'))
from races import USPS, NAME
