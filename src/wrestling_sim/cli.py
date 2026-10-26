"""Interactive text-mode player interface and short reproducible demonstration."""
from __future__ import annotations
import argparse
from .game import advance_week, book_show, brief_state, create_storyline, offer_contract, simulate_show
from .models import Segment
from .ratings import rating_breakdown
from .service import GameService


def cash(value: int) -> str:
    return f'${value:,}'


def roster_text(state) -> str:
    workers = [w for w in state.wrestlers.values() if w.company_id == state.player_company_id]
    lines = ['\nYOUR ROSTER (CA/PA/MV out of 100)']
    for w in sorted(workers, key=lambda w: rating_breakdown(w)['current_ability'], reverse=True):
        r = rating_breakdown(w)
        lines.append(f'  {w.id:<10} {w.name:<19} {w.role:<8} {r["current_ability"]:>5.1f} / {r["potential_ability"]:>5.1f} / {r["market_value"]:>5.1f}  contract {w.contract_weeks}w')
    return '\n'.join(lines)


def print_report(result: dict) -> None:
    print(f'\n=== {result["name"]} — {result["year"]}, Week {result["week"]} ===')
    for seg in result['segments']:
        print(f'\n{seg["title"]} | {seg["kind"]} | {seg["duration"]}m')
        print(seg['narrative'])
        print(f'  Quality {seg["quality"]:.1f}  Crowd {seg["crowd"]:.1f}  Story hype {seg["hype_delta"]:+.1f}  RNG {seg["rng_adjustment"]:+.1f}')
    print(f'\nSHOW: quality {result["quality"]:.1f}/100, crowd {result["crowd"]:.1f}/100')
    print(f'ATTENDANCE: {result["finances"]["attendance"]:,}')
    print(f'EVENT NET: {cash(result["finances"]["event_net"])} (weekly overhead comes separately)')


def demo(service: GameService) -> None:
    with service.lock:
        state = service.state
        print('\n=== 2026: AURORA PRO WRESTLING ===')
        print(f'Week {state.week} | Bank {cash(state.player_company.money)}')
        print(roster_text(state))
        if any(show.week == state.week for show in state.shows.values()):
            print('\nAn event is already booked/simulated this week; use play to inspect your save.')
            return
        # The full 110-minute sample obeys V0.4's mandatory division/story rules.
        segments = [
            Segment('match', ['steel', 'phoenix'], 20, 'The Veteran vs The Prodigy',
                    storyline_id='steel-phoenix', planned_winner_id='phoenix'),
            Segment('match', ['vale', 'collins'], 20, 'The Crown and the Challenger',
                    storyline_id='vale-collins', planned_winner_id='collins'),
            Segment('promo', ['steel','phoenix'], 15, 'A Public Challenge',
                    storyline_id='steel-phoenix', creative_direction='escalate'),
            Segment('confrontation', ['vale','collins'], 15, 'The Rivals Confront Each Other',
                    storyline_id='vale-collins', promo_brawl=True),
            Segment('interview', ['knox'], 10, 'Orion Knox Interview'),
            Segment('interview', ['cruz'], 10, 'Nova Cruz Interview'),
            Segment('backstage', ['steel'], 10, 'The Veteran Speaks'),
            Segment('return', ['phoenix'], 10, 'Phoenix Makes an Appearance'),
        ]
        show = book_show(state, 'Aurora: First Light', segments)
        report = simulate_show(state, show.id)
        service.save()
        print_report(report)
        story = state.storylines['steel-phoenix']
        print(f'\nSTORYLINE: {story.title} | hype {story.hype:.1f}/100 | investment {story.fan_investment:.1f}/100')
        print(f'COMPANY CASH: {cash(state.player_company.money)}')
        print('\nSave written. Continue with: wrestling-sim play')


def ask_number(question: str, default: int) -> int:
    text = input(f'{question} [{default}]: ').strip()
    return int(text) if text else default


def prompt_show(state) -> tuple[str, list[Segment]]:
    print('\nBook 100-120 minutes; include men and women storylines (max 2 slots each). Available segment types: match, promo, confrontation, backstage, betrayal, interview, contract_signing, return')
    print(roster_text(state))
    print('Storylines: ' + ', '.join(f'{s.id} ({s.title})' for s in state.storylines.values()))
    name = input('Show title [Aurora Weekly]: ').strip() or 'Aurora Weekly'
    n = ask_number('Number of segments', 8)
    if not 1 <= n <= 12:
        raise ValueError('Choose 1..12 segments')
    segments = []
    for i in range(n):
        print(f'\nSegment {i+1} of {n}')
        kind = (input('Type [promo]: ').strip() or 'promo').lower()
        ids = input('Participants (comma-separated wrestler IDs): ').strip()
        participants = [x.strip() for x in ids.split(',') if x.strip()]
        duration = ask_number('Duration in minutes', 7 if kind != 'match' else 15)
        title = input('Segment title: ').strip() or f'{kind.title()} {i+1}'
        story_id = input('Storyline ID (optional): ').strip() or None
        direction = input('Creative direction [advance/slow_burn/escalate/resolve/swerve] (default advance): ').strip() or 'advance'
        winner = input('Planned winner ID (matches only; optional): ').strip() or None
        quality = ask_number('Booking preparation quality 0..25', 17)
        segments.append(Segment(kind, participants, duration, title, story_id,
                                quality, winner, direction))
    return name, segments


def interactive(service: GameService) -> None:
    print('\n=== WRESTLING PROMOTION SIMULATOR | TEXT MODE ===')
    print('All names/companies in this starter save are fictional.')
    while True:
        s = service.state
        print(f'\n{ s.player_company.name } — {s.year} W{s.week} | Cash {cash(s.player_company.money)}')
        print('1 Roster / ratings  2 Storylines  3 Book show  4 Run show  5 Advance week')
        print('6 Negotiate contract  7 News / finances  8 Start fresh game  0 Exit')
        choice = input('Choose: ').strip()
        try:
            with service.lock:
                if choice == '0':
                    service.save()
                    break
                elif choice == '1':
                    print(roster_text(s))
                    wid = input('Enter wrestler ID for full stats (or Enter): ').strip()
                    if wid:
                        w = s.wrestlers[wid]
                        print(f'{w.name}: {w.attributes}')
                        print(rating_breakdown(w))
                elif choice == '2':
                    for story in s.storylines.values():
                        print(f'{story.id}: {story.title} | hype {story.hype:.1f}, fan investment {story.fan_investment:.1f}, history {len(story.history)} segments')
                    if input('Create new storyline? (y/N): ').strip().lower() == 'y':
                        title = input('Title: ')
                        ids = [x.strip() for x in input('Wrestler IDs, comma-separated: ').split(',')]
                        story = create_storyline(s, title, ids)
                        print(f'Created: {story.id}')
                        service.save()
                elif choice == '3':
                    name, card = prompt_show(s)
                    show = book_show(s, name, card)
                    print(f'Booked {show.name} ({show.id}), {len(card)} segments.')
                    service.save()
                elif choice == '4':
                    pending = [show for show in s.shows.values() if not show.simulated and show.week == s.week]
                    if not pending:
                        print('No booked show this week.')
                    else:
                        print_report(simulate_show(s, pending[0].id))
                        service.save()
                elif choice == '5':
                    report = advance_week(s)
                    print(f'Advanced to {report["year"]} W{report["week"]}. Payroll {cash(report["payroll"])}; fixed costs {cash(report["fixed_costs"])}.')
                    for event in report['events']:
                        print('  ' + event)
                    service.save()
                elif choice == '6':
                    print('Free agents: ' + ', '.join(f'{w.id} ({w.name})' for w in s.wrestlers.values() if w.company_id is None))
                    wid = input('Wrestler ID (or current roster member for renewal): ').strip()
                    salary = ask_number('Weekly pay in $', 2500)
                    weeks = ask_number('Contract weeks', 52)
                    bonus = ask_number('Signing bonus in $', 1000)
                    result = offer_contract(s, wid, salary, weeks, bonus)
                    print('ACCEPTED' if result['accepted'] else 'DECLINED', result)
                    service.save()
                elif choice == '7':
                    print('\nLatest news:')
                    for line in s.news[-10:]:
                        print(' • ' + line)
                    print('\nLatest ledger:')
                    for line in s.financial_history[-5:]:
                        print(' • ', line)
                elif choice == '8':
                    if input('Overwrite your saved world? Type RESET: ').strip() == 'RESET':
                        service.reset()
                        print('New fictional 2026 save started.')
                else:
                    print('Invalid selection.')
        except (ValueError, KeyError) as exc:
            print(f'Cannot complete action: {exc}')
        except (KeyboardInterrupt, EOFError):
            print('\nExiting; saving game.')
            service.save()
            break


def main() -> None:
    parser = argparse.ArgumentParser(description='2026 wrestling promotion simulation')
    parser.add_argument('--save', default='saves/game.json', help='Save game JSON path')
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('play', help='Launch interactive game')
    commands.add_parser('demo', help='Book and simulate a ready-made first show')
    commands.add_parser('roster', help='Print roster rating breakdown')
    commands.add_parser('reset', help='Reset the save to the 2026 start (destructive)')
    web = commands.add_parser('web', help='Launch playable browser frontend and backend')
    web.add_argument('--port', type=int, default=8000, help='Local web server port')
    web.add_argument('--no-browser', action='store_true', help='Do not auto-open the browser')
    args = parser.parse_args()
    if args.command == 'web':
        import os
        import threading
        import webbrowser
        import uvicorn
        os.environ['WRESTLING_SIM_SAVE'] = args.save
        url = f'http://127.0.0.1:{args.port}/'
        print(f'Ringside web app: {url}')
        print('Press Ctrl+C to stop the server. Your game autosaves after actions.')
        if not args.no_browser:
            timer = threading.Timer(2.0, lambda: webbrowser.open(url))
            timer.daemon = True
            timer.start()
        uvicorn.run('wrestling_sim.api:app', host='127.0.0.1', port=args.port)
        return
    service = GameService(args.save)
    if args.command == 'demo':
        demo(service)
    elif args.command == 'roster':
        print(roster_text(service.state))
    elif args.command == 'reset':
        service.reset()
        print(f'New world saved to {service.path}')
    else:
        interactive(service)


if __name__ == '__main__':
    main()
