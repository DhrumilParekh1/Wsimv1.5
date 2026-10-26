"""Fictional sponsor contract choices; all economy effects stay server authoritative."""
from __future__ import annotations
import random
from .models import GameState, clamp

BRANDS = [('Northstar Gear', 'Sports apparel'), ('Moonbeam Mobile', 'Consumer electronics'),
          ('Harbour Coffee', 'Coffeehouse chain'), ('Summit Hydration', 'Sports beverages')]


def sponsor_offers(state: GameState) -> list[dict]:
    # One offer per week, subject to a ten-partner limit.
    active = [x for x in state.sponsor_deals.values() if x['weeks_left'] > 0]
    if len(active) >= 10:
        return []
    key = f'sponsor-{state.year}-{state.week}'
    if key in state.sponsor_responses:
        return []
    brand, sector = BRANDS[(state.week + state.seed) % len(BRANDS)]
    rng = random.Random(f'sponsor:{state.seed}:{state.year}:{state.week}')
    weekly = int(900 + state.player_company.sponsor_interest * 45 + rng.randint(0, 850))
    return [{'id': key, 'name': brand, 'sector': sector, 'weekly_payment': weekly,
             'weeks': 4 + (state.week % 3) * 4,
             'minimum_crowd': round(clamp(48 + state.player_company.popularity * .22, 45, 78),1),
             'description': 'A fictional brand proposes a partnership with an audience-performance target.'}]


def respond_sponsor(state: GameState, offer_id: str, action: str, counter_amount: int = 0) -> dict:
    offer = next((o for o in sponsor_offers(state) if o['id'] == offer_id), None)
    if not offer:
        raise ValueError('Sponsor offer expired, was already resolved, or no partnership slot is open')
    if action not in ('accept', 'counter', 'reject'):
        raise ValueError('Choose accept, counter, or reject')
    if action == 'counter' and not (offer['weekly_payment'] < counter_amount <= offer['weekly_payment'] * 2):
        raise ValueError('Counter must be above the opening offer and no more than twice that amount')
    accepted = action == 'accept'
    if action == 'counter':
        rng = random.Random(f'{state.seed}:{offer_id}:{counter_amount}')
        leverage = state.player_company.popularity * .0015 + state.player_company.sponsor_interest * .002
        premium = counter_amount / offer['weekly_payment'] - 1
        accepted = rng.random() < clamp(.72 + leverage - premium * .95, .08, .92)
    weekly = counter_amount if action == 'counter' else offer['weekly_payment']
    result = {'offer_id': offer_id, 'name': offer['name'], 'action': action,
              'accepted': accepted, 'weekly_payment': weekly if accepted else 0,
              'narrative': (f"{offer['name']} signed for ${weekly:,} per show."
                            if accepted else f"{offer['name']} declined your counteroffer."
                            if action == 'counter' else f"You passed on {offer['name']}.")}
    if accepted:
        state.sponsor_deals[offer_id] = {'id': offer_id, 'name': offer['name'],
            'weekly_payment': weekly, 'weeks_left': offer['weeks'],
            'minimum_crowd': offer['minimum_crowd'], 'misses': 0}
        state.player_company.sponsor_interest = clamp(state.player_company.sponsor_interest + .3)
    state.sponsor_responses[offer_id] = result
    state.news.append(result['narrative'])
    return result


def settle_show_sponsors(state: GameState, finances: dict, crowd: float, quality: float) -> None:
    payment = 0
    for key, deal in state.sponsor_deals.items():
        if deal['weeks_left'] <= 0: continue
        if crowd < deal['minimum_crowd']:
            deal['misses'] += 1
            state.player_company.sponsor_interest = clamp(state.player_company.sponsor_interest - .4)
            paid = int(deal['weekly_payment'] * .7)
        else:
            paid = deal['weekly_payment']
        payment += paid
        deal['weeks_left'] -= 1
        if deal['weeks_left'] == 0:
            state.news.append(f"{deal['name']} partnership has reached its scheduled end.")
    state.player_company.money += payment
    finances['contract_sponsors'] = payment
    finances['sponsors'] += payment
    finances['event_net'] += payment


def terminate_sponsor(state: GameState, deal_id: str) -> dict:
    deal=state.sponsor_deals.get(deal_id)
    if deal is None or deal.get('weeks_left',0)<=0:
        raise ValueError('Active sponsor agreement not found')
    # The brand is owed a cancellation payment; cannot silently drop a contract.
    penalty=int(deal['weekly_payment']*min(4,deal['weeks_left'])*0.5)
    if state.player_company.money<penalty:
        raise ValueError('Insufficient funds for the early termination payment')
    state.player_company.money-=penalty
    state.player_company.sponsor_interest=clamp(state.player_company.sponsor_interest-2.0)
    deal['weeks_left']=0
    deal['termination_penalty']=penalty
    state.news.append(f"{deal['name']} partnership ended early, costing ${penalty:,}.")
    return {'terminated':True,'fee':penalty,'sponsor':deal['name']}
