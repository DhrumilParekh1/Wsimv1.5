"""2026 wrestling broadcast audience benchmarks and separate GAME budgets.

Audience observations describe ONE publicly tracked television programme or
platform metric—not worldwide reach, company gross audience or revenue. WWE
Netflix Raw, for example, is measured differently from U.S. Nielsen SmackDown.
ROH streaming audience lacks a comparable public Nielsen number and is
explicitly modelled. All cash, sponsor values and prestige are fictional
economic/game-balance numbers, never reported corporate financials.
"""
from __future__ import annotations

# TV audience evidence, accessed November 2026:
# WWE SmackDown: YTD U.S. Nielsen P2+ programme average 1,236,689 (Nov 6)
# AEW Dynamite: YTD U.S. Nielsen P2+ programme average 661,378 (Nov 11)
# TNA Impact: observed Sep 3/10/17 2026: 184k,232k,207k (illustrative ~208k)
# ROH: streaming platform not comparable; fictional game calibration 50k.
# Sources are retained per row for traceability.
BENCHMARKS = {
    "player": {
        "name":"WWE","cash":50_000_000,"popularity":94,"fan_trust":84,
        "sponsor_interest":93,"viewership":1_236_689,"prestige_history":95,
        "weekly_fixed_costs":80_000,"venue_capacity":15000,"ticket_price":65,
        "audience_basis":"WWE SmackDown, 2026 YTD U.S. Nielsen P2+ per episode",
        "audience_source":"https://trnbckl.net/ratings/smackdown/",
        "audience_modelled":False,
    },
    "rival": {
        "name":"All Elite Wrestling","cash":28_000_000,"popularity":80,
        "fan_trust":77,"sponsor_interest":80,"viewership":661_378,
        "prestige_history":83,"weekly_fixed_costs":60_000,
        "venue_capacity":7500,"ticket_price":50,
        "audience_basis":"AEW Dynamite, 2026 YTD U.S. Nielsen P2+ per episode",
        "audience_source":"https://trnbckl.net/ratings/dynamite/",
        "audience_modelled":False,
    },
    "circuit": {
        "name":"TNA Wrestling","cash":6_000_000,"popularity":55,
        "fan_trust":68,"sponsor_interest":52,"viewership":208_000,
        "prestige_history":62,"weekly_fixed_costs":15_000,
        "venue_capacity":2200,"ticket_price":30,
        "audience_basis":"TNA Impact, approx. average of 3 September 2026 AMC broadcasts",
        "audience_source":"https://wrestlenomics.com/articles/2026/tna-impact-sep-10-on-amc-232000-viewers-0-03-p18-49-rating-tv-ratings-analysis/",
        "audience_modelled":True,
    },
    "royal": {
        "name":"Ring of Honor","cash":3_500_000,"popularity":47,
        "fan_trust":62,"sponsor_interest":43,"viewership":50_000,
        "prestige_history":58,"weekly_fixed_costs":9_000,
        "venue_capacity":1400,"ticket_price":26,
        "audience_basis":"Game-only streaming proxy; no comparable Nielsen baseline",
        "audience_source":"https://www.ringofhonor.com/",
        "audience_modelled":True,
    },
}

def apply_company_benchmark(company,company_id):
    row=BENCHMARKS[company_id]
    for game_key,field in {
        "cash":"money","popularity":"popularity","fan_trust":"fan_trust",
        "sponsor_interest":"sponsor_interest","viewership":"viewership",
        "prestige_history":"prestige_history",
        "weekly_fixed_costs":"weekly_fixed_costs",
        "venue_capacity":"venue_capacity","ticket_price":"ticket_price",
    }.items():
        setattr(company,field,row[game_key])
    return {
        "evidence_date":"2026-11",
        "audience_reference":row["audience_basis"],
        "audience_source":row["audience_source"],
        "audience_modelled":row["audience_modelled"],
        "viewership_baseline":row["viewership"],
        "company_cash_and_prestige_are_game_estimates":True,
        "not_comparable_to_full_global_reach":True,
    }
