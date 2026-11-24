# harbor_facilities.csv: notes

Owner: T2.1 (2026-11-23). Hand-built from the sources in `source_urls`, T1.3's truth set and the port inventory's `facilities.csv`. Edit by hand; record changes to existing rows in a Corrections log at the end of this file.

## What it is

One row per facility of an owner in `harbor_entity_crosswalk.csv`, saying which harbor the facility belongs to under the **site rule** (decisions log, 2026-11-22), or `none`. It has 70 rows (31 of them `none`) for 28 owners; 19 owners have more than one facility. Reviewers in T2.2–T2.4 use it to decide whether an owner's award counts toward a harbor.

| Column | Meaning |
|---|---|
| `owner_entity` | Owner as named in the crosswalk |
| `owner_uei` | Owner UEI(s) from the crosswalk, `;`-separated (all are in the crosswalk; checked by script) |
| `facility_name` | Facility or group of facilities |
| `facility_type` | `marina`, `wharf`, `dock`, `launch`, `boatyard`, `cargo_terminal`, `ferry_terminal`, `harbor_complex`, `processing_service`, `rail`, `industrial_park`, `airport` |
| `harbor_id` | Harbor the facility belongs to, or `none` (outside every harbor in the universe) |
| `source_urls` | Where the facility or its harbor assignment comes from. `data/reference/award_harbor_truth_pilot.csv` means T1.3 labelled an award at this facility |
| `notes` | Reasons; rows marked "from general knowledge" have not been checked against an owner page |

Coverage: every owner with more than one facility that matters for awards, plus single-site owners where the harbor_id is not obvious from the name (Port Hueneme, Channel Islands, the added harbors). Owners whose only facility is the inventory harbor (most small ports) are not listed; their awards belong to that harbor once the award text confirms it is harbor work.

## How reviewers apply the site rule

1. **Find the facility.** Read the award text and place of performance; find the matching row for the recipient's owner.
2. **Bay or harbor complex named by the inventory** (Humboldt Bay, San Diego Bay, LA/Long Beach, Bodega Bay, the added Oakland, Tacoma and Olympia harbors): any facility of any crosswalk owner in that water body counts, including cargo terminals (e.g. Redwood Marine Terminal → CA-humboldt-bay).
3. **Marina, terminal or wharf named by the inventory** (Westport Marina, Charleston Marina, Port Angeles Boat Haven, Fishermen's Terminal, Fisherman's Wharf/Pier 45, Squalicum Harbor, Cap Sante, Astoria basins…): only that facility counts. Everything else the owner runs is `none`.
4. **`none` facilities** stay out of harbor dollars. Their awards can enter T2.7 as the owner's past awards (a capacity measure). The user decided on 2026-11-23 not to add inventory owners' other terminals as new harbors.
5. **One owner, two harbors** (Humboldt Bay district: Humboldt Bay / Shelter Cove; Port of Willapa Harbor: Bay Center / Tokeland; Port of Bellingham: Squalicum / Blaine): the UEI matches both harbors, so `crosswalk_match` flags the award `flagged_multi`. Assign by place of performance and award text.
6. **Not a facility of the port.** An award on a port's UEI that is not for any port facility (e.g. City of Long Beach flood control or CARES loan fund on the Harbor Department UEI) gets no harbor.
7. **Unclear**: when the text doesn't name a facility (e.g. Port Angeles "facility renovation"), leave it unassigned and note it in the review queue. Don't default to the inventory harbor.

## Known gaps

- Facilities "from general knowledge" (terminal names, airports, secondary marinas) were not checked on owner pages. They are listed so reviewers recognise them. A wrong name here cannot move dollars into a harbor, because every such row is `none`.
- Port of Astoria Pier 2 hosts seafood processors (inventory context). Under the site rule it is `none` because the inventory names the basins. Flag Pier 2 awards for the user if any appear.
- The Charleston Shipyard is assumed to be part of the Charleston Marina Complex (`OR-charleston`). Confirm before assigning an award.
