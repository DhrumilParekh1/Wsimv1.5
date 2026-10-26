# RINGSIDE V1.5 — Negotiation, Correspondence & Fan Social Repair

## Changes implemented

1. Sponsor cap increased to 10 active contracts. Partnerships can now be terminated through the Sponsorships screen. Cancellation costs 50% of the next up to four weekly payments and reduces sponsor interest by two points. Both rules are enforced by the API.
2. A stated contract counteroffer is binding when the player offers at least its quoted weekly salary, contract duration, and signing bonus. The owner and wrestler can still walk away before agreement. Previous conversation history is retained.
3. Roster-status complaints open the private two-round wrestler meeting screen, replacing the instant inbox decision. Choices update morale and relationship; completing the meeting resolves the linked concern and records its outcome. The existing personality and RNG logic remains active.
4. Recruitment correspondence remains accessible after acknowledgement. Cards offer a link to the relevant buyout/contract interface with the wrestler selected. Report read status is separate from recruitment eligibility, and contract restrictions still apply.
5. Fan-post validation extracts only `text` from valid JSON, rejects malformed or truncated outputs, rejects an incompatible declared sentiment, and validates posts in both the legacy rewrite and active asynchronous narration paths. Previously saved malformed posts are safely hidden in the UI instead of showing raw JSON.
6. Prior V1.4 creative-decision handoff, context-sensitive backstage events, and highlight-scrolling adjustments are retained.

## Technical limitations and further testing

- The browser and API integration must still be validated with a running local Ollama instance; mocked tests alone do not prove acceptable generated dialogue.
- The sponsorship market still offers up to one new opportunity per week; the cap of ten is an allowed maximum, not ten offers simultaneously.
- Wrestler meetings still use the established two-round dialogue and simplified personalities. A fully granular multi-issue promise negotiation system is a future expansion.
- Pre-contract talks still follow the eligibility and buyout rules of V1.4. Correspondence links make them accessible but do not override exclusive contracts.
- Matching a formal counteroffer guarantees acceptance, but initial salary negotiations may still probabilistically reject an opening offer.
- Browser syntax and Python tests are validated; full real-browser responsive testing remains necessary on the user's Windows computer.

## Windows installation

Back up your existing `saves/game.db` and/or `saves/game.json`. Extract into a new folder. Copy the save to `saves/` before starting, then launch `start_game.bat` and open http://127.0.0.1:8000/ . Stop the old running server before starting the new one.
