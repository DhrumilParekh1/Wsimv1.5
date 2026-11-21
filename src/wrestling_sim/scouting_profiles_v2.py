"""Individually authored public-performance attributes for the 80 curated wrestlers.

These are strong, differentiated *editorial game estimates* anchored to public
career accomplishments, 2026 PWI rankings and public match/character history.
They are not official ratings, medical assessments, or judgments about private
life. Data reviewed 2026-11-21. Date-sensitive momentum is a 2026 snapshot.

Columns:
workrate, technique, moves, sequences, flair, athleticism, agility,
determination (on-screen), selling, stamina, mic_skills, charisma,
character_work, presence, fan_connection, popularity, relevance,
momentum (recent booking), experience (career history), promotion.
"""
from __future__ import annotations

PUBLIC_KEYS=(
    "workrate","technique","moves","sequences","flair","athleticism",
    "agility","determination","selling","stamina","mic_skills",
    "charisma","character_work","presence","fan_connection",
    "popularity","relevance","momentum","experience","promotion",
)
# One explicit row per person; numbers are independently assessed, not merely
# inferred from a class such as 'powerhouse' or 'technical'.
PUBLIC_RATINGS={
# WWE — men
"Cody Rhodes": "22 20 20 22 20 20 19 24 23 22 24 24 24 23 24 24 24 24 22 23",
"CM Punk": "18 17 17 21 16 13 12 22 22 17 25 24 25 22 24 24 24 23 25 23",
"Roman Reigns": "19 15 16 20 15 21 15 22 20 17 22 24 24 25 25 25 25 21 22 22",
"Gunther": "25 25 23 24 16 21 16 23 24 24 18 20 23 24 21 22 23 22 21 19",
"Seth Rollins": "23 22 22 23 22 21 22 23 22 21 23 23 23 22 23 23 24 22 23 22",
"Drew McIntyre": "22 20 21 21 18 22 16 23 22 21 22 22 24 24 22 23 23 23 22 21",
"Bron Breakker": "22 17 19 18 20 25 22 22 19 22 17 19 19 24 20 21 22 22 13 18",
"Jey Uso": "17 15 16 16 17 19 17 21 18 17 20 23 20 21 25 24 23 19 19 23",
"Damian Priest": "20 18 19 19 16 22 16 20 20 20 18 19 20 22 19 19 19 17 18 18",
"Carmelo Hayes": "23 20 23 23 24 23 24 20 21 21 19 20 19 18 18 19 19 21 14 18",
"Dominik Mysterio": "16 14 15 17 16 17 16 18 20 18 21 22 24 19 21 22 22 22 14 18",
"Randy Orton": "20 19 17 23 17 19 15 21 24 18 20 23 23 25 24 24 22 18 25 20",
# WWE — women
"Rhea Ripley": "22 20 22 22 20 24 20 24 23 22 21 23 23 25 24 24 24 21 18 22",
"Becky Lynch": "20 18 20 21 18 18 17 23 23 19 24 24 25 23 24 23 22 18 22 22",
"Bianca Belair": "24 21 22 22 22 25 24 23 21 24 19 22 20 24 23 23 21 17 18 20",
"Charlotte Flair": "22 22 23 22 21 22 20 22 21 21 20 22 22 24 22 23 21 19 24 19",
"Iyo Sky": "25 24 25 24 25 23 25 23 23 23 16 20 19 21 22 23 23 21 21 18",
"Bayley": "21 19 20 21 18 18 17 22 24 20 23 23 24 21 23 22 21 18 21 20",
"Jade Cargill": "15 12 15 13 18 24 17 18 14 16 17 21 17 25 21 21 20 19 10 20",
"Tiffany Stratton": "22 18 21 20 23 24 25 21 19 21 19 22 21 22 21 22 21 18 12 22",
# AEW — men
"Will Ospreay": "25 24 25 25 25 25 25 24 24 24 20 22 21 23 22 23 22 19 21 21",
"MJF": "22 20 20 23 17 18 17 22 24 21 25 25 25 24 25 25 25 25 19 24",
"Kenny Omega": "24 23 24 24 24 22 21 23 23 21 19 23 22 23 24 24 22 21 25 22",
"Jon Moxley": "22 18 21 21 17 18 15 25 24 22 22 23 23 23 22 23 23 21 23 21",
"Darby Allin": "23 19 23 23 25 24 24 25 23 23 17 21 21 20 22 22 22 21 17 19",
"Swerve Strickland": "23 21 23 23 22 23 21 22 22 22 22 23 23 23 22 23 23 21 18 22",
"Kazuchika Okada": "24 24 22 25 20 20 18 22 24 22 17 22 22 24 23 23 22 18 25 20",
"Samoa Joe": "21 19 20 22 14 18 12 22 22 19 22 23 24 24 22 22 21 18 25 20",
"Claudio Castagnoli": "24 24 23 23 21 24 22 24 23 25 14 18 18 21 20 21 20 20 24 16",
"Jay White": "22 23 21 24 18 18 18 22 23 22 22 22 24 21 20 21 19 17 20 19",
"Kyle Fletcher": "24 23 24 23 24 24 23 23 22 23 18 20 20 22 20 21 22 23 15 19",
"Jack Perry": "19 17 18 18 19 21 21 20 20 19 20 19 21 18 18 19 18 17 16 17",
# AEW — women
"Mercedes Moné": "23 21 23 23 23 22 23 22 21 21 20 23 22 23 22 23 23 24 21 22",
"Kris Statlander": "23 19 23 22 20 25 21 21 20 22 17 20 19 23 21 21 22 22 17 19",
"Willow Nightingale": "22 19 20 21 19 22 20 23 22 22 22 24 23 22 23 22 24 24 15 20",
"Jamie Hayter": "23 22 22 23 18 21 16 24 24 21 20 21 22 22 21 21 19 16 18 18",
"Riho": "22 21 22 23 23 18 24 20 23 20 14 18 18 15 20 20 18 15 21 17",
"Tay Melo": "17 15 17 16 17 20 19 19 17 17 16 18 17 18 16 17 16 13 15 17",
"Megan Bayne": "20 17 19 19 18 24 17 21 18 20 14 18 18 24 16 18 19 20 12 16",
"Anna Jay": "18 16 18 17 16 19 19 19 18 18 18 19 19 18 18 18 18 16 13 16",
# TNA — men
"Leon Slater": "23 21 24 22 25 24 25 22 21 22 17 20 20 19 19 19 20 22 11 18",
"Moose": "20 17 20 19 18 24 19 21 20 19 18 19 20 24 19 19 19 18 21 17",
"Nic Nemeth": "22 19 20 21 18 19 17 23 25 23 21 22 21 21 20 20 22 23 25 20",
"Mustafa Ali": "23 22 23 24 23 22 23 22 22 22 21 22 22 21 19 20 20 21 20 20",
"Frankie Kazarian": "21 21 19 22 17 17 16 21 23 20 21 21 22 20 18 18 19 16 25 17",
"Jeff Hardy": "17 14 18 17 22 17 16 21 20 16 14 22 19 23 22 22 18 17 25 19",
"Matt Hardy": "15 13 15 16 14 13 11 20 20 15 20 21 21 21 21 20 18 17 25 18",
"Cedric Alexander": "23 22 23 23 22 23 23 22 21 22 15 17 17 18 17 17 20 21 19 16",
"Eddie Edwards": "20 18 19 19 15 17 15 23 21 20 18 19 20 20 17 17 17 16 23 17",
"Brian Myers": "17 16 17 17 14 16 16 20 19 18 19 20 19 18 16 16 16 15 22 18",
"AJ Francis": "14 12 14 13 12 20 14 17 15 15 19 18 20 22 16 16 15 14 16 16",
"Jason Hotch": "20 20 21 21 21 20 21 21 20 20 14 16 16 16 13 13 17 19 11 14",
# TNA — women
"Indi Hartwell": "17 15 17 17 15 18 16 19 19 18 19 20 20 19 18 18 18 17 15 19",
"Xia Brookside": "20 21 19 21 20 19 21 19 20 19 16 18 18 18 16 17 20 22 16 15",
"Alisha Edwards": "14 13 14 15 13 14 14 18 18 17 19 19 20 17 15 15 14 14 19 15",
"Tasha Steelz": "19 18 19 19 18 20 21 19 19 19 20 19 20 18 17 17 18 17 16 17",
"Jada Stone": "20 17 20 19 22 22 23 18 18 19 14 17 16 17 15 15 18 21 11 15",
"Heather By Elegance": "16 14 16 15 17 17 17 17 17 17 20 21 21 19 16 16 18 20 14 19",
"Kiera Hogan": "18 16 17 18 18 20 19 19 19 19 16 18 18 18 17 17 17 15 15 17",
"Elayna Black": "17 16 17 16 17 17 17 18 18 18 20 20 21 19 17 17 17 16 13 18",
# ROH — men
"Bandido": "24 23 24 24 25 24 24 23 22 23 16 21 20 22 20 21 22 24 20 19",
"Lee Moriarty": "22 25 21 24 19 19 19 22 22 21 15 17 17 17 16 16 19 21 13 15",
"Dalton Castle": "19 17 18 19 18 17 16 20 21 18 24 25 24 23 20 20 19 18 23 19",
"Shane Taylor": "19 17 18 18 13 19 11 22 20 18 20 20 20 22 16 17 16 15 20 16",
"Angelico": "21 24 21 22 19 19 21 19 21 21 14 17 18 17 15 15 15 13 22 15",
"Carlie Bravo": "16 15 16 16 16 18 18 18 18 19 17 17 18 16 13 13 14 14 12 15",
"Komander": "22 19 23 21 25 24 25 21 19 22 13 16 16 16 16 17 19 20 12 16",
"Tony Nese": "20 19 20 20 17 24 22 21 20 23 15 17 17 18 15 16 16 14 22 15",
"AR Fox": "22 21 22 22 23 21 22 22 22 21 14 17 17 18 16 16 18 18 23 15",
"Lee Johnson": "20 20 20 20 20 22 22 20 20 21 15 17 17 18 15 15 16 16 13 16",
"Griff Garrison": "16 14 16 15 13 18 16 17 16 17 13 16 15 19 13 13 13 12 12 14",
"Serpentico": "18 17 18 19 19 19 20 21 23 20 15 18 20 15 14 14 14 13 21 16",
# ROH — women
"Athena": "24 23 24 24 23 23 23 24 23 24 21 23 24 22 23 23 23 24 20 20",
"Red Velvet": "20 19 20 20 21 21 21 20 21 20 17 19 18 18 17 18 19 20 16 17",
"Deonna Purrazzo": "22 24 20 23 16 17 16 21 23 21 20 21 22 19 19 19 20 20 21 18",
"Billie Starkz": "23 21 23 22 23 22 23 22 22 22 17 19 20 19 18 19 19 19 12 18",
"Diamante": "18 17 18 19 17 19 18 21 20 19 17 18 19 18 16 16 16 16 19 17",
"Trish Adora": "20 22 20 21 17 20 17 21 21 20 16 19 18 20 16 17 17 18 15 16",
"Robyn Renegade": "17 17 17 17 17 19 19 18 18 19 16 18 17 17 14 14 15 15 12 15",
"Rachael Ellering": "19 18 18 18 15 19 15 19 20 20 17 18 18 20 16 16 16 16 18 16",
}

PROFILES={}
for _name,_numbers in PUBLIC_RATINGS.items():
    _values=tuple(int(x) for x in _numbers.split())
    if len(_values)!=len(PUBLIC_KEYS):
        raise AssertionError(f"Incorrect number of scouting fields for {_name}: {len(_values)}")
    if not all(0<=n<=25 for n in _values):
        raise AssertionError(f"Out-of-range scouting field for {_name}")
    PROFILES[_name]=dict(zip(PUBLIC_KEYS,_values))

# Each profile gets an actual strength and an explicit limitation.
# Strengths/limitations describe on-screen work, not private identity or health.
SCOUTING_NOTES={
"Cody Rhodes":("Big-match character psychology; crowd connection","Not an extreme aerial or technical specialist"),
"CM Punk":("Elite promos and audience investment","Less explosive agility and pace than modern high-flyers"),
"Roman Reigns":("Main-event aura, story and audience recognition","More limited move variety than technical specialists"),
"Gunther":("Top-level technical control and match pacing","Less flashy acrobatics; moderate promo versatility"),
"Seth Rollins":("High all-round ring and microphone skills","Below peak aerial specialists in flight complexity"),
"Drew McIntyre":("Power, intensity and persuasive antagonism","Not a quick aerial technician"),
"Bron Breakker":("Exceptional explosive power and developing ring work","Mic and long-match psychology still developing"),
"Jey Uso":("Outstanding crowd connection and entrance charisma","Narrower technical repertoire"),
"Damian Priest":("Strong presence and power-based offence","Not a standout technical or promo specialist"),
"Carmelo Hayes":("Fast combinations and athletic creativity","Still building top-card audience recognition"),
"Dominik Mysterio":("Very effective heel character and reactions","In-ring complexity and technique behind elite workers"),
"Randy Orton":("Timing, subtle psychology, superstar recognition","Less athletic variety than in earlier career"),
"Rhea Ripley":("Presence, character, power and complete ring execution","Not the division's top aerial specialist"),
"Becky Lynch":("Excellent promo storytelling and crowd chemistry","Athletic explosiveness not her main strength"),
"Bianca Belair":("High-end athletic execution and power","Promo nuance trails strongest talkers"),
"Charlotte Flair":("Big-match experience, technique and presence","Recent momentum below historical peak"),
"Iyo Sky":("Elite movement, pace and intricate in-ring sequences","Language-dependent live promo work less central"),
"Bayley":("Strong character changes and opponent selling","Less athletic spectacle than elite high-flyers"),
"Jade Cargill":("Striking presentation and power-star potential","Technical transitions and selling remain weaker"),
"Tiffany Stratton":("Athletic movement and developing star presentation","Technical finesse and deep career experience evolving"),
"Will Ospreay":("Near-ceiling ring speed, sequences and aerial execution","Promo skill and recent booking momentum trail ring peak"),
"MJF":("Top-end heel promos, match psychology, star presence","Aerial athleticism not a specialty"),
"Kenny Omega":("Outstanding career match catalogue and complex sequences","Current form rated separately from career peak"),
"Jon Moxley":("Physical storytelling, intensity and believable brawling","Less clean aerial technique"),
"Darby Allin":("Risk-taking ring style and distinctive crowd reactions","Promo variety below technical/ring spectacle"),
"Swerve Strickland":("Balanced ring creativity, music/character presence","Not as technically precise as specialist grapplers"),
"Kazuchika Okada":("Veteran main-event pacing and elite timing","Mic versatility not his principal asset"),
"Samoa Joe":("Believable character, pressure and ring psychology","Lower aerial speed and agility"),
"Claudio Castagnoli":("Outstanding mechanics, strength and conditioning","Mic delivery below top talkers"),
"Jay White":("Counterwrestling and layered heel psychology","Current momentum below established career peak"),
"Kyle Fletcher":("Top-tier athletic matches and current trajectory","Mic delivery not yet elite"),
"Jack Perry":("Athletic timing and developing character presentation","Not currently a top in-ring or audience draw"),
"Mercedes Moné":("Proven women's division star and ring creativity","Promo precision below best live talkers"),
"Kris Statlander":("Strong physical ring execution and improvement","Mic delivery not a standout quality"),
"Willow Nightingale":("Current momentum, authentic connection and match energy","Less intricate technical work than specialists"),
"Jamie Hayter":("Convincing strikes, ring intensity and selling","Current form below top-career potential"),
"Riho":("Fast precise sequences and imaginative counters","Limited live speaking prominence and power game"),
"Tay Melo":("Athletic upside and character familiarity","Match consistency below top-tier specialists"),
"Megan Bayne":("Power-based offense and intimidating presentation","Promo development and nuanced selling still evolving"),
"Anna Jay":("Character growth and improved timing","Technical precision and promo ceiling not established"),
"Leon Slater":("Breakout youth, aerial speed, recent spotlight","Less experience and established mic range"),
"Moose":("Powerful big-match presence and athletic bursts","Technical refinement not his strongest dimension"),
"Nic Nemeth":("High-selling veteran with extensive career history","Explosiveness below career peak"),
"Mustafa Ali":("Aerial precision and creative in-ring transitions","Mainstream audience reach below major-company headliners"),
"Frankie Kazarian":("Deep experience and reliable technical pacing","Athletic explosiveness below younger peak"),
"Jeff Hardy":("Iconic legacy, imagination and audience memory","Present-day match speed below prime"),
"Matt Hardy":("Character reinvention and veteran storytelling","Modern pace and agility below peak"),
"Cedric Alexander":("Very good clean ring work and movement","Mic presence and audience pull comparatively lower"),
"Eddie Edwards":("Dependable veteran brawling and match experience","Limited high-speed athletic ceiling"),
"Brian Myers":("Solid character-role and veteran fundamentals","Not a top athletic or technical spectacle wrestler"),
"AJ Francis":("Bigger-than-life act and speaking presence","Technical sequencing below polished ring specialists"),
"Jason Hotch":("Crisp ring transitions and improving performances","Still limited broad recognition and promo record"),
"Indi Hartwell":("Character sympathy and crowd-facing presentation","Technical variety below elite technicians"),
"Xia Brookside":("Quick technical combinations and current local form","Mainstream recognition remains limited"),
"Alisha Edwards":("Experienced heel character and speaking work","Ring offence behind more technical competitors"),
"Tasha Steelz":("Compact athletic offense and character versatility","Recognition and detailed sequencing still midcard"),
"Jada Stone":("Fast aerial execution and recent upward momentum","Limited veteran consistency and mic record"),
"Heather By Elegance":("Distinctive character presentation and current momentum","Technical wrestling behind specialist peers"),
"Kiera Hogan":("Energetic offense and tag-team timing","Still developing marquee singles aura"),
"Elayna Black":("Confident character and promo-driven segments","No established elite match portfolio"),
"Bandido":("Explosive lucha offense and champion-level match craft","Mic-focused promo strength is secondary"),
"Lee Moriarty":("Elite technical counterwrestling technique","Audience notoriety and mic presence lower"),
"Dalton Castle":("Extremely distinctive character and mic charisma","Raw pace and current athleticism below top specialists"),
"Shane Taylor":("Power offense and intimidation through presence","Agility and aerial timing limited"),
"Angelico":("Fluid technical submission combinations","Low current headline momentum"),
"Carlie Bravo":("Growing athletic timing and personality","Early development level, not a proven star"),
"Komander":("Spectacular rope-running and flying sequences","Promo delivery and selling behind elite all-rounders"),
"Tony Nese":("Athletic conditioning and reliable ring fundamentals","Limited mainstream character connection"),
"AR Fox":("Experienced aerial instructor and ring innovation","Character promo reach more limited"),
"Lee Johnson":("Developing clean mechanics and agile movement","Top-tier promo and headlining proof limited"),
"Griff Garrison":("Physical upside and role-player utility","Ring complexity and mic range remain early"),
"Serpentico":("Creative comedy selling and spirited wrestling","Not positioned as a headlining character"),
"Athena":("Dominant ROH reign, strong character and match execution","Mainstream reach differs from larger TV platforms"),
"Red Velvet":("Athletic movement and improved competitive standing","Promo and technical ceiling not yet elite"),
"Deonna Purrazzo":("Strong submission technique and ring psychology","Explosive aerial range is limited"),
"Billie Starkz":("Remarkable young match creativity and potential","Still building major-title experience and promo force"),
"Diamante":("Tough character work and efficient offense","Not a top-end high-flying specialist"),
"Trish Adora":("Creative holds and recognizable technical identity","Audience scale and promo history modest"),
"Robyn Renegade":("Useful all-round athletic prospect","Lacks proven headline-level ring and mic output"),
"Rachael Ellering":("Dependable veteran fundamentals and power offense","Limited recent singles momentum"),
}
if set(SCOUTING_NOTES)!=set(PROFILES):
    raise AssertionError("Every individual scouting profile must have strengths and limitations")

EVIDENCE={
    "pwi_500_2026":"https://www.cagematch.net/en/?id=97&nr=583",
    "pwi_womens_250_2026":"https://www.fightful.com/wrestling/stephanie-vaquer-tops-2026-pwi-womens-250/",
    "weekly_pwi":"https://pwi-online.com/pwi-ratings/",
    "wwe":"https://www.wwe.com/superstars",
    "aew":"https://www.allelitewrestling.com/aew-roster",
    "tna":"https://tnawrestling.com/roster",
    "roh":"https://www.ringofhonor.com/roster",
}
REVIEWED_ON="2026-11-21"
MODEL_VERSION="editorial_2026_11_v2"
