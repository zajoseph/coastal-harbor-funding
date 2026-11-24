# award_harbor_overrides.csv: notes

Owner: T1.3, built 2026-11-22. Hand-built. These are manual corrections to automatic award → harbor matching (`harborfund.link.crosswalk_match`). They are applied after matching, with `apply_overrides()`, and **never count toward the auto-match rate** (decisions log, 2026-11-18).

## Columns

| Column | Meaning |
|---|---|
| `award_id`, `award_source` | Same key as `award_harbor_truth_pilot.csv` (`prime` FAIN; `subaward` = prime FAIN\|subaward number\|SAM report id) |
| `harbor_id` | Harbor to assign (blank for `unassign`) |
| `action` | `assign`: set the harbor. `unassign`: remove an automatic assignment. **This column is added to the kickoff's list** because most corrections remove a wrong auto-match rather than add one |
| `reason` | Why, in one line. Rows that depend on the site rule start with `SITE RULE:` |
| `evidence_url` | USAspending permalink from T1.1's files, plus any other source used |
| `added_by_task` | Task that added the row |

## Rows (13)

- **assign (3):**
  - 693JF72444090: Redwood Marine Terminal, under Port of Grays Harbor's UEI → CA-humboldt-bay.
  - 070107315: AltaSea, a tenant not in the crosswalk → CA-los-angeles-long-beach.
  - LBCT LLC subaward: pass-through of POLB PIDP; same dollars as the prime, so count one of the two.
- **unassign, not harbor-related (7):** two City of Long Beach (flood control; CARES revolving loan fund), Port of Skagit business park, three Trinidad Rancheria hazard-mitigation awards, Quileute plan.
- **unassign under the site rule (3):** Coos Bay Rail Line, Grays Harbor Terminal 4, Newport International Terminal. These stay if the user picks the owner-level rule (see the truth-set notes). Delete these three rows in that case.

## Not in this table

- **Swinomish FY2022 PIDP** (693JF72344040): outside the pilot universe (coded to Superior, WI), and its harbor has no harbor ID yet. T2.1 adds the tribal port first; then an `assign` row can follow.
- **Coquille PIDP 693JF72444079:** correctly unmatched (not a pilot harbor). The mis-joined description is recorded in the truth-set notes.

## Corrections log

| Date | award_id | Column | Old | New | Source |
| --- | --- | --- | --- | --- | --- |
