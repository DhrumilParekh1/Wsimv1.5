# V1.4: Backstage decisions and live commentary polish

- New backstage incidents offer **category-specific** choices rather than a generic disciplinary set. This applies to mentoring, collaboration, disputes, media, equipment, contracts, etc.
- Choice outcomes are resolved in the Python rules engine using seeded RNG, wrestler personality, relationships, and severity. In addition to morale and relations, some cases affect finances, momentum, technique, chemistry, or trust.
- Successful approved or trial mentorships become persistent `mentorships` entries. Approved/trial arrangements last 6/2 game weeks and give small technique and sequencing development through weekly advancement; these are intentionally conservative prototype values.
- Resolutions are stored in incident records, news and long-term memories and appear in the dashboard's recap.
- Live highlight navigation now preserves the outer modal scroll position and follows the newest highlight within the scrollable feed.
- Creative direction on prefills selected from the Creative Room is carried into the booking form and explained as a narrative choice.

## Compatibility and limitations

Existing V1.3 JSON/SQLite campaigns can be restored with an empty mentorship list. Unresolved legacy incidents receive updated context-aware options on load. Prior incident results remain untouched.

The event outcomes are **not a fully simulated multi-step backstage scene**. The V1.4 build introduces category-specific player actions and persistent mentorships, but deeper follow-up commitments, personality-specific dialogue text, distinct negotiation rooms for all backstage events, creative-plan override enforcement, and real-time Ollama narration should still be validated or expanded later.

Run `python -m pytest -q` to verify the game logic. Live Chromium UI and local Ollama integration were not tested in this environment.
