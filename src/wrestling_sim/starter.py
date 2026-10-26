"""Fictional 2026 starter universe; no real-wrestler data or likeness rights."""
from __future__ import annotations
from .models import Company, GameState, Storyline, Wrestler
from .weights import ALL_ATTRIBUTES


def make_wrestler(id: str, name: str, age: int, company_id: str | None,
                 role: str, changes: dict[str, float], salary: int = 0,
                 contract_weeks: int = 0, growth: float = .55,
                 runway: float = .50, availability: float = 100,
                 division: str = "men", personality: str = "balanced") -> Wrestler:
    attrs = dict.fromkeys(ALL_ATTRIBUTES, 15.0)
    attrs.update({"popularity": 12.0, "relevance": 12.0, "momentum": 12.0,
                  "fan_connection": 13.0, "controversy_risk": 5.0, "loyalty": 15.0,
                  "face": 14.0, "heel": 14.0, "tweener": 14.0, "injury_proneness": 9.0})
    attrs.update(changes)
    from .traits import starting_profile
    height, weight, traits=starting_profile(id, changes, age)
    return Wrestler(id=id, name=name, age=age, company_id=company_id,
                   height_cm=height, weight_kg=weight, traits=traits,
                   attributes=attrs, role=role, salary_weekly=salary,
                   contract_weeks=contract_weeks, growth_aptitude=growth,
                   development_runway=runway, availability=availability,
                   division=division, personality=personality)


def new_game(seed: int = 2026) -> GameState:
    companies = {
        "player": Company("player", "Aurora Pro Wrestling", money=850_000,
                          popularity=36, fan_trust=58, sponsor_interest=42,
                          weekly_fixed_costs=5_000, venue_capacity=1200,
                          ticket_price=35, roster_limit=12),
        "rival": Company("rival", "Titan Wrestling Alliance", money=1_500_000,
                         popularity=65, fan_trust=61, sponsor_interest=70,
                         weekly_fixed_costs=12_000, venue_capacity=3200,
                         ticket_price=45, roster_limit=20),
        "circuit": Company("circuit", "Rising Sun Circuit", money=950_000,
                          popularity=49, fan_trust=74, sponsor_interest=47,
                          weekly_fixed_costs=7500, venue_capacity=2000,
                          ticket_price=38, roster_limit=14, brand="technical"),
        "royal": Company("royal", "Crown Combat Network", money=1_100_000,
                        popularity=53, fan_trust=52, sponsor_interest=65,
                        weekly_fixed_costs=9800, venue_capacity=2400,
                        ticket_price=42, roster_limit=16, brand="entertainment"),
    }
    workers = [
        make_wrestler("steel", "Marcus Steel", 37, "player", "heel", {
            "charisma": 21, "mic_skills": 20, "character_work": 22, "presence": 23,
            "workrate": 20, "stamina": 16, "athleticism": 17,
            "experience": 23, "popularity": 21, "relevance": 20, "momentum": 16,
            "fan_connection": 20, "heel": 24, "tweener": 20, "ambition": 22,
        }, salary=3500, contract_weeks=22, growth=.35, runway=.28),
        make_wrestler("phoenix", "Alex Phoenix", 26, "player", "face", {
            "mic_skills": 19, "charisma": 21, "character_work": 19,
            "workrate": 20, "athleticism": 23, "agility": 22, "stamina": 22,
            "popularity": 15, "relevance": 16, "momentum": 20,
            "fan_connection": 21, "face": 23, "ambition": 21,
        }, salary=2100, contract_weeks=36, growth=.90, runway=.85),
        make_wrestler("vale", "Ember Vale", 31, "player", "heel", {
            "mic_skills": 23, "charisma": 22, "character_work": 24,
            "presence": 21, "selling": 20, "workrate": 18,
            "popularity": 18, "fan_connection": 19, "heel": 24,
        }, salary=2800, contract_weeks=44, growth=.60, runway=.57, division="women", personality="independent"),
        make_wrestler("cruz", "Nova Cruz", 27, "player", "tweener", {
            "workrate": 23, "technique": 22, "moves": 22, "sequences": 23,
            "athleticism": 21, "agility": 22, "selling": 21,
            "mic_skills": 13, "popularity": 12, "tweener": 22,
        }, salary=1850, contract_weeks=48, growth=.83, runway=.82, division="women", personality="ambitious"),
        make_wrestler("collins", "Vega Collins", 29, "player", "face", {
            "charisma": 20, "selling": 22, "stamina": 22, "workrate": 21,
            "fan_connection": 21, "face": 22, "momentum": 17,
        }, salary=1900, contract_weeks=34, growth=.72, runway=.65, division="women", personality="cooperative"),
        make_wrestler("knox", "Orion Knox", 32, "player", "heel", {
            "presence": 23, "athleticism": 22, "moves": 21,
            "mic_skills": 16, "popularity": 17, "heel": 23,
        }, salary=2250, contract_weeks=28, growth=.52, runway=.52),
        make_wrestler("storm", "Rafael Storm", 34, "rival", "heel", {
            "presence": 24, "popularity": 24, "mic_skills": 22,
            "charisma": 23, "heel": 24, "workrate": 19,
        }, salary=7500, contract_weeks=60, growth=.48, runway=.42),
        make_wrestler("haze", "Sienna Haze", 28, "rival", "face", {
            "workrate": 24, "agility": 23, "athleticism": 23,
            "fan_connection": 22, "popularity": 19, "face": 23,
        }, salary=4900, contract_weeks=52, growth=.76, runway=.72, division="women"),
        make_wrestler("ryder", "Miles Ryder", 35, "rival", "tweener", {
            "mic_skills": 23, "character_work": 23, "experience": 23,
            "popularity": 22, "tweener": 24,
        }, salary=5800, contract_weeks=43, growth=.35, runway=.32),
        make_wrestler("sora", "Akira Sora", 31, "circuit", "face", {
            "technique":24,"workrate":23,"selling":22,"popularity":18,"agility":21
        },salary=3700,contract_weeks=60,division="men",personality="cooperative"),
        make_wrestler("mizuki", "Mizuki Lane", 27, "circuit", "heel", {
            "agility":23,"workrate":22,"popularity":17,"mic_skills":21,"heel":22
        },salary=3200,contract_weeks=44,division="women",personality="independent"),
        make_wrestler("arden", "Arden Fox", 34, "royal", "heel", {
            "charisma":24,"mic_skills":24,"presence":22,"popularity":22,"heel":24
        },salary=5100,contract_weeks=39,division="men",personality="ambitious"),
        make_wrestler("lyra", "Lyra Ash", 29, "royal", "face", {
            "fan_connection":22,"popularity":19,"charisma":22,"face":22,"workrate":20
        },salary=3700,contract_weeks=56,division="women",personality="balanced"),
        make_wrestler("orbit", "Jade Orbit", 24, None, "face", {
            "workrate": 20, "athleticism": 22, "agility": 23,
            "popularity": 8, "fan_connection": 12, "face": 20,
        }, growth=.92, runway=.91, division="women"),
        make_wrestler("crowe", "Damien Crowe", 30, None, "heel", {
            "charisma": 21, "mic_skills": 22, "character_work": 22,
            "popularity": 10, "heel": 23,
        }, growth=.65, runway=.62),
    ]
    # Assign starting-card status based on creative position, not only current ability.
    tiers={'steel':'main_event','phoenix':'upper_mid_card','vale':'main_event',
           'cruz':'upper_mid_card','collins':'mid_card','knox':'mid_card',
           'storm':'main_event','haze':'main_event','ryder':'upper_mid_card'}
    for member in workers:
        member.card_tier=tiers.get(member.id,'lower_mid_card')
    # Give every rival meaningful men’s and women’s matches on weekly cards.
    workers.extend([
        make_wrestler('eden','Eden South',27,'rival','heel',{'selling':21,'charisma':19,'workrate':20,'popularity':16},salary=3250,contract_weeks=44,division='women'),
        make_wrestler('pike','Orson Pike',30,'circuit','heel',{'technique':22,'workrate':21,'popularity':15},salary=3100,contract_weeks=56),
        make_wrestler('talia','Talia Finch',26,'circuit','face',{'workrate':23,'selling':21,'popularity':13},salary=2400,contract_weeks=50,division='women'),
        make_wrestler('thorn','Gideon Thorn',32,'royal','face',{'workrate':20,'charisma':20,'popularity':18},salary=3300,contract_weeks=48),
        make_wrestler('aria','Aria Nova',25,'royal','heel',{'mic_skills':22,'presence':22,'popularity':14},salary=2900,contract_weeks=36,division='women'),
    ])
    world = GameState(seed=seed, year=2026, week=1,
                      player_company_id="player", companies=companies,
                      wrestlers={w.id: w for w in workers})
    from .championships import ensure_championships
    belts=ensure_championships(world)
    for belt_id,holder in [('men_world','steel'),('men_intercontinental','phoenix'),('women_world','vale')]:
        belts[belt_id]['holder_id']=holder
        belts[belt_id]['lineage'].append({'week':1,'winner_id':holder,'previous_holder_id':None,
                                         'change':True,'match_title':'Inaugural champion'})
    # International and independent talent provides actual scouting targets.
    for w in [
        make_wrestler('solis','Marisol Vega',25,None,'face',{'agility':22,'workrate':21,'popularity':8,'momentum':15},growth=.91,runway=.86,division='women',personality='ambitious'),
        make_wrestler('hart','Elias Hart',23,None,'tweener',{'technique':22,'workrate':21,'popularity':7},growth=.93,runway=.92,personality='independent'),
        make_wrestler('blaze','Kira Blaze',30,None,'heel',{'mic_skills':21,'charisma':23,'popularity':13},growth=.66,runway=.55,division='women',personality='volatile'),
        make_wrestler('finn','Theo Finn',28,None,'face',{'selling':22,'stamina':23,'popularity':10},growth=.80,runway=.76,personality='cooperative'),
    ]:
        w.discovery_tier = {'solis':'regional','hart':'national','blaze':'global','finn':'regional'}.get(w.id, 'known')
        world.wrestlers[w.id]=w
    world.storylines["steel-phoenix"] = Storyline(
        id="steel-phoenix", title="The Veteran and the Prodigy",
        wrestler_ids=["steel", "phoenix"], hype=47,
        fan_investment=51, coherence=78,
    )
    world.storylines["vale-collins"] = Storyline(
        id="vale-collins", title="The Crown and the Challenger",
        wrestler_ids=["vale", "collins"], hype=45, fan_investment=49, coherence=76,
    )
    from .world import bootstrap_world
    from .audience import ensure_expectations
    for story in world.storylines.values():
        ensure_expectations(world,story)
    bootstrap_world(world)
    from .press_and_incidents import ensure_incidents
    ensure_incidents(world)
    world.news.append("Welcome to 2026. Book your first Aurora Pro Wrestling show!")
    return world
