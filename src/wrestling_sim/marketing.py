"""Cash-based, saturating promotional reach. Legacy 0-25 saves remain readable."""
from __future__ import annotations
import math
from .models import clamp


def segment_spend(segment) -> int:
    if segment.promotion_budget is not None:
        return max(0, int(segment.promotion_budget))
    effort = segment.promotion_effort if segment.promotion_effort is not None else segment.booking_quality
    return round(45 * effort ** 1.25)  # backward compatibility with older saves


def marketing_impact(state, segment) -> float:
    """Audience uplift in rating points. Scales against company's actual reach."""
    spend = segment_spend(segment)
    reference = max(4000, min(140000, state.player_company.viewership * .035))
    # Campaigns cover general publicity; segment spend adds targeted incremental reach.
    broad=campaign_visibility(state)
    narrow=2.6*math.log1p(spend/reference)
    return round(clamp(broad+narrow*(1-broad/10),0,8),3)


def purchase_campaign(state,scope: str, amount: int):
    """Broad weekly/PPV promotion is booked and charged once per campaign."""
    if scope not in ('weekly','ppv'):raise ValueError('Choose a weekly or PPV campaign')
    if amount<0 or amount>state.player_company.money:raise ValueError('Campaign exceeds available company funds')
    if amount==0:raise ValueError('Campaign spend must be positive')
    if scope=='ppv' and state.week not in state.player_company.ppv_weeks:
        raise ValueError('PPV advertising requires a scheduled PPV this week')
    key=f'{state.year}:{state.week}:{scope}'
    if any(x['key']==key for x in state.campaigns):raise ValueError('Campaign already bought this week')
    state.player_company.money-=amount
    campaign={'key':key,'year':state.year,'week':state.week,'scope':scope,'amount':amount}
    state.campaigns.append(campaign)
    state.financial_history.append({'year':state.year,'week':state.week,'reason':'campaign',
                                    'net':-amount,'advertising':amount})
    return campaign


def campaign_visibility(state):
    spent=sum(x['amount'] for x in state.campaigns if x['year']==state.year and x['week']==state.week)
    if not spent:return 0.0
    reference=max(10000,state.player_company.viewership*.09)
    return round(clamp(2.4*math.log1p(spent/reference),0,4.0),3)
