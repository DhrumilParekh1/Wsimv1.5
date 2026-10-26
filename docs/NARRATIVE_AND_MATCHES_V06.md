# V0.6 Implementation Notes

## Authority boundaries

- `simulation.py` + `match_engine.py` own ratings, audience reception, finishes, highlight actions, probabilities and storyline impacts.
- `game.py` + `sponsors.py` own budget, sponsor payouts, weekly progression and hard inbox checks.
- `social.py` creates deterministic simulated fan reactions from saved show reports.
- `narrative.py` may rewrite fan-post **text** or generate optional display-only recaps. It cannot change stored scores, crowds, wrestler attributes, sentiment labels or finishes. On failure the original feed remains readable.
- No interactive player input is directly sent as a trusted system instruction. Context is supplied as JSON data and handled as untrusted text. Local Ollama is opt-in, with a timeout and strict JSON response shape. The language model's creative descriptions are flavour text, not game-state authority.

## Configure Ollama on Windows

1. Install and start Ollama separately. Ensure it is listening on `http://127.0.0.1:11434`.
2. In PowerShell, run `ollama pull llama3.2` once (requires network and free disk space). You may choose any installed model instead.
3. Launch `start_with_ollama.bat`, or in the same PowerShell terminal:

```powershell
$env:RINGSIDE_OLLAMA_ENABLED="1"
$env:RINGSIDE_OLLAMA_MODEL="llama3.2"
.\start_game.bat
```

4. Open **Fan Social** → **Check Ollama** to verify connectivity, then click **Generate fan posts with Ollama** after running a show. Open a show report and select **Ollama narrative recap** for text commentary.

If Ollama is absent, disabled, or loading times out, default simulated fan posts and regular match highlights still work. The Ollama generator calls the local `/api/chat` endpoint with `stream: false`, a JSON schema and limited token budget. **No hosted API keys or cloud services are required.** `.env.example` is documentation, not an auto-loaded environment file.

## Match combinations

The Show Booker now requires two distinct styles, optionally a third:

- **Two** styles: primary 65%, secondary 35%.
- **Three** styles: primary 55%, secondary 30%, third 15%.

Available styles are `balanced`, `technical`, `high_flying`, `power`, `brawl`, and `storytelling`. Each contributes its own skill-weight vector. The blend changes `style_fit` as well as the fundamental performance score: 55% established match ability and **45% blended style fit**, before psychology, fatigue, stipulations, crowd context, finish credibility, and bounded RNG. The ordered combination changes the move-pool in match highlights. Historical segments with the old `match_style` and no `match_styles` array automatically run in legacy mode.

## Inbox block rules

Weeks cannot advance until:

1. A complete weekly card was booked and simulated.
2. All weekly owner decisions are answered.
3. The promotional-media request was assigned or explicitly declined.
4. Sponsor enquiries were accepted, rejected, or countered.
5. Every open creative promise was fulfilled by a correctly matching segment or explicitly cancelled at a fan-trust penalty.

The backend independently computes these blockers; the browser displays the count. Creative promises that cannot be fulfilled after a show can be cancelled, so old campaigns cannot get permanently stuck on the same week.

## Sponsor economy

One new fictional sponsor proposal can appear per week if fewer than two partnerships are active. Sponsor deals offer recurring payments, a duration and a minimum crowd rating. If a show falls below the negotiated threshold, that week's payment is reduced to 70% and sponsor interest suffers. Sponsors can also reject a requested increase. Sponsor funds are appended to the event ledger only once per completed show. These are fictional game values, not real sponsorship pricing.

## Browser navigation

The left sidebar now scrolls independently, preserving access to its lower items. A full section selector is available in the topbar even on small phones; the mobile bottom bar still offers five common destinations. Storylines no longer references an undefined `p` variable in its creation form. No switch to React or Node.js was required.

## Known limits

- V0.6 has no remote LLM provider support and does not ship an Ollama model. Real local generation depends on your own installed Ollama service and available machine resources. In-container testing validates its JSON contract with a mock, not an actual installed model.
- Sponsor negotiation is one round per offer (accept / reject / one counter). More elaborate negotiation meetings can come later.
- Match highlights are a precomputed replay rather than frame-by-frame physics. Matches still rely on the weighted backend and player-booked results.
- Private meeting dialogue continues to use authored choice text. Future work can add validated Ollama phrasing to those existing dialogue state machines.
