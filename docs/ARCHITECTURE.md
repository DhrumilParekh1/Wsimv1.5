# RINGSIDE V0.4 architecture

Web UI (`web/index.html` + `assets/app.js`) → FastAPI (`api.py`) → game orchestration (`game.py`) → match, segment, creative, management and progression engines. Every successful mutation goes through the `GameService` lock, then saves atomically to JSON (`storage.py`).

- `models.py`: validated wrestler/segment/storyline/company/game data; divisions and personality added in V0.4.
- `weights.py`, `ratings.py`: canonical raw 0–25 attributes, weighted composites 0–100.
- `simulation.py`, `match_engine.py`: stat-sensitive segment evaluations; deterministic seeded uncertainty; text highlights in chronological order.
- `game.py`, `progression.py`: validate entire booked card, simulate persistent consequences, update stamina and financial state, advance weeks only after a completed show.
- `scenes.py` and `management.py`: branching creative choices, writer quality, locked promises, action queue, staff market, media requests and owner relationships.
- `decisions.py`: persistent inbox decisions, backstage disputes, sponsor choice consequences.
- `storage.py`: supports older saves with injected missing fields and starter women's division/storyline migration.

`/ui/state` sends the current promotion view; POST endpoints carry actual player choices. The client validates bookings for immediate feedback, **but the Python API enforces the authoritative booking restrictions**. The frontend's live recap is a replay of the saved show result, not a different simulator.

Limitation: JSON saves and in-process locks suit one local user. Multiplayer/cloud operation would require a database and transaction isolation.
