# V1.6 management and narration integration

This branch complements the earlier mandatory press, contextual complaint, stable highlight scrolling and local Ollama test fixes.

## Changes
- Fan post rewriting preserves canonical simulator sentiment and avoids publishing exact or whitespace-normalized duplicate Ollama comments within each show. When a rewrite duplicates another, the engine retains the existing deterministic post.
- Creative Room strategy now prefills Show Booker direction on committed tasks. A conflicting direction displays an explicit confirmation prompt. The user's manual override is still permitted.
- Recruitment report Inbox action navigates to Talent Market and locates the relevant wrestler's correspondence when present.

## Known limitations / acceptance testing
- Full rich multi-round manager meetings, enhanced long-term narrative and economically calibrated multi-season balancing are not comprehensively reworked by these edits and should not be represented as completed.
- The creative direction override confirmation is a client-side workflow safeguard; backend scoring already uses segment creative_direction and commitment fulfillment but does not yet enforce a new server-side override audit trail.
- Recruitment eligibility and buyouts still follow existing V1.5 rules.
- The live Windows Ollama model and browser scroll interactions need practical verification. Run pytest and actual show simulation before merging.
