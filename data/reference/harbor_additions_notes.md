# harbor_additions.csv: notes

Owner: T2.1 (2026-11-23). Hand-built. Every candidate harbor considered for the universe is listed, including rejected and deferred ones, with the decision, reason and evidence. Edit by hand; record changes to decided rows in a Corrections log at the end of this file.

## Approved addition rule (user, 2026-11-23)

T2.1 proposed the rule in writing before anything was added. The user decided two points: **any public harbor** (not only fishing harbors), and **separate owners only**.

1. **What counts as a harbor:** an improved in-water facility (basin, marina, wharf/pier, dock, hoist or launch) in one of the 42 NOAA coastal counties (`coastal_counties.csv`). Its owner or operator must be a public, special-district or tribal entity. Use is not restricted: cargo, fishing and recreational harbors all qualify.
2. **Separate owners only:** a candidate is added only if its owner has **no inventory harbor**. An inventory owner's other facilities (e.g. Port of Grays Harbor Terminal 4, Port of Seattle Terminal 5) stay `none` in `harbor_facilities.csv`, as the site rule says. They are not new harbors.
3. **Site rule first:** a facility inside a bay or harbor complex the inventory names belongs to that harbor and is not an addition.
4. **Minimum evidence (both):**
   - (a) the facility and its location in a coastal county, from a primary or agency source;
   - (b) the owner or operator, from an owner, agency or government record.

   A federal award alone is not evidence of a facility.
5. **Outside the 42 counties:** flag to the user; never added by changing the county list. No candidate so far is outside.
6. **IDs:** `<ST>-add-<slug>` (e.g. `WA-add-swinomish`). No inventory `port_id` contains `-add-`, so the two can't collide.
7. **Inventory fields filled:** `port_id`, `port_name`, `state`, `county`, `lat`, `lon`, `coord_source`, `in_round1` (= `N`), `context_notes`. The port inventory repo is not edited.

## Candidate sources searched (kickoff scope)

- **Tribal ports:** Swinomish first, then the Coquille Ko'Kwel Wharf (a T1.1 PIDP recipient). Ten more tribes were screened by name only and are **deferred**: their owner and facility evidence was not gathered in T2.1.
- **Port or harbor entities among T1.1's in-scope recipients** (primes `in_scope & in_fy_window`, plus in-scope subawards; staged from the user's Mac, mtimes 1795014122562 / 1795014122677) that no inventory harbor maps to.
- **State-agency check.** No inventory harbor is state-owned (T1.2). T2.1 checked the state agencies that appear in the T1.1 data or own the underlying lands: CA State Lands Commission, CA State Parks/DBW, CDFW, WA DNR, Oregon State Marine Board and WSDOT. **No state-agency-owned harbor was found.** WSDOT's Washington State Ferries terminals meet the letter of the rule; they are deferred with a proposed reject, for the user to confirm. This was not a systematic search of state facility registers.

## Columns

| Column | Meaning |
|---|---|
| `candidate` | Candidate harbor or entity |
| `candidate_source` | `tribal`, `t1.1_recipient`, `state_agency_check`, `tribal_screen`, `facilities_review` |
| `decision` | `added`, `rejected`, `deferred` |
| `port_id` … `context_notes` | Inventory fields, filled for added harbors |
| `in_coastal_counties` | Whether the county is one of the 42 |
| `added_via_award` | `yes` if the candidate surfaced because it received a federal award (see the caution below) |
| `reason`, `evidence_urls` | Why, and where from |
| `decided_date` | Date of the decision |

## Result

- **Added (5):** WA-add-swinomish, OR-add-kokwel-wharf, CA-add-oakland, WA-add-tacoma, WA-add-olympia. Each has crosswalk rows; coordinates are blank (no primary-source point opened).
- **Rejected (14):** Port of Shelton (its marina is now privately owned), Port of Seattle's Elliott Bay terminals and inventory owners' other terminals (separate-owners rule), NWSA as a harbor (operator row instead), SSA Terminals, AltaSeads Conservancy, Port Angeles Waterfront Center, Noyo Center for Marine Science, Mithihkwuh EDC (operator row instead), and five state agencies.
- **Deferred (11):** WSDOT ferry terminals (user to confirm) and 10 tribes (proposed for T2.1b).

## Caution: additions select on the outcome

All five added harbors surfaced because they won federal awards (`added_via_award = yes`). Harbors that never won an award can't surface through these sources. Adding only award winners therefore pushes up the share of harbors with awards, and biases H1 toward finding that capacity predicts awards. T3 should estimate with and without the added harbors (filter `harbor_id` containing `-add-`), or add harbors from a source independent of awards (e.g. a state public-port list) before T2.8.
