# award_harbor_truth_pilot.csv: notes

Owner: T1.3 (match-rate assessment), built 2026-11-22. This is a hand-coded truth set: each label was decided by reading the award's recipient, location and description, plus the OpenFEMA title or a web source where needed. The labels were typed into a build script; nothing is generated from raw data. Edit by hand and record changes in the Corrections log below.

It is the denominator for the Gate 1 match rate. Notebook 04 scores automatic UEI/DUNS matching (`harborfund.link.crosswalk_match`) against it, before any override.

## Review universe

- **Prime awards:** every prime award in T1.1's `prime_awards.csv` with `in_scope & in_fy_window`, whose recipient county or place-of-performance county is the county of one of the 20 pilot harbors.
- **Subawards:** every in-scope FFATA subaward in `subawards.csv` with the same county rule. Exact repeat reports (same prime, subaward number, subawardee, amount and date) are dropped; there were none in the universe.
- **Counties:** the 17 distinct `county_fips` values in `harbor_entity_crosswalk.csv`.
- **Result:** 241 awards (183 primes, $613.5M; 58 subawards, $168.7M; nominal). Every award was reviewed, not only those with `harbor_kw_flag`.
- **Key:** `award_id` is the FAIN for primes (URI when there is no FAIN), and `prime FAIN|subaward number|SAM report id` for subawards. Together with `award_source` (`prime` / `subaward`) it is unique.
- **Source files staged from the user's Mac:** `prime_awards.csv` (mtime 1795014122562), `subawards.csv` (1795014122677) and `bric_pacific_subapplicants.csv` (1795018774126), all dated 2026-11-18.

## Labels

| `label` | Meaning |
|---|---|
| `sample_harbor` | The project is at one of the 20 pilot harbors, as the inventory names it. `harbor_id` gives the harbor |
| `other_harbor` | Harbor-related (port, harbor, marina, wharf, pier, navigation, or port-owned terminal/rail), but not at a pilot harbor. This includes a pilot owner's other facilities |
| `not_harbor` | Not harbor-related. Examples: city flood control, revolving loan funds, hazard-mitigation plans, workforce programs, business parks, tourism, fish processing away from harbor infrastructure |
| `unclear` | Can't be decided from the record and one lookup. Counted separately and excluded from recall and precision |

## The site rule: what counts as "at" a pilot harbor

- **When the inventory name is a bay or harbor complex** ("San Diego Bay", "Humboldt Bay", "Los Angeles / Long Beach Harbor"), any harbor facility in that water body counts. Examples: Port of LA and Long Beach terminals and rail, National City Marine Terminal, Redwood Marine Terminal.
- **When the inventory name is one facility** ("Port of Coos Bay Charleston Marina", "Port of Grays Harbor Westport Marina", "Port of Newport commercial marina", "Port of Skagit La Conner Marina", "Fishermen's Terminal"), only that facility counts. The same owner's cargo terminals, rail lines, airports and business parks do not.
  - A harbor-related one is labelled `other_harbor` with scope `sample_owner_other_facility`.
  - A non-harbor one is labelled `not_harbor` with scope `sample_owner_non_harbor`.
- **The owner-level view is a sensitivity check.** `owner_harbor_id` records the owner's harbor, so notebook 04 can re-score with the owner's harbor-related other facilities counted as hits. Under the site rule, 3 awards are affected: Coos Bay Rail Line, Grays Harbor Terminal 4, Newport International Terminal.

## Columns

| Column | Meaning |
|---|---|
| `award_id`, `award_source`, `program_id` | As in notebook 04 / `review_universe.csv`; `program_id` from T1.1 |
| `label`, `harbor_id` | As above. `harbor_id` is filled only for `sample_harbor` |
| `scope` | `at_sample_harbor`; `sample_owner_other_facility` (harbor-related, a pilot owner's other facility); `sample_owner_non_harbor` (a pilot owner's or crosswalk entity's non-harbor award); `other_entity` |
| `owner_harbor_id` | For the two `sample_owner_*` scopes: the pilot harbor the owning entity belongs to |
| `reason` | Why, in one line |
| `evidence` | What the label rests on: USAspending description, FFATA subaward description, OpenFEMA title (by subapplication or award ID), or a URL |
| `label_method` | `desc` (record text alone, 207), `fema` (OpenFEMA title join, 29), `web` (one web lookup, 5) |
| `passthrough_of_prime` | For subawards whose prime is also in the universe: the prime FAIN. The dollars double-count the prime |
| `recipient_name`, `amount_nominal` | Copied for readability (nominal $) |
| `added_by_task` | T1.3 |

## Hard cases

- **693JF72444090** (Redwood Marine Terminal, Eureka; Port of Grays Harbor's UEI): `sample_harbor`, CA-humboldt-bay. Auto-matching flags it on location, so it is a recall miss, not a misassignment. An override assigns it.
- **Coquille Indian Tribe PIDP 693JF72444079:** its USAspending description (40,000 ft of rail, 50-acre brownfield) is copied from Port of Grays Harbor's Terminal 4 award 693JF72344028. The real project is Ko'Kwel Wharf in North Bend (Coos Bay), per press coverage of the FY2023 round. Labelled `other_harbor`. **Descriptions can be wrong.**
- **Long Beach.** UEI DBSHZ2LVFAE6, which the crosswalk lists as the Harbor Department's, also carries the City's CARES Act revolving loan fund. The City's general UEI carries citywide flood control. Both are `not_harbor` and both are auto-assigned.
- **AltaSea at the Port of LA** (City Dock No. 1) and **LBCT LLC** (Middle Harbor, a pass-through of POLB's PIDP) are at the harbor. Neither recipient is in the crosswalk.
- **Northwest Seaport Alliance, Husky Terminal (Tacoma):** in the universe only because its place of performance is coded Aberdeen (Grays Harbor County). `other_harbor`.
- **Swinomish FY2022 PIDP** (693JF72344040): not in the universe. It is coded to Superior, WI, and T1.1 dropped it as out of scope. Its harbor (the Swinomish tribal port) isn't in the inventory (T2.1).
- **The 9 `PC` awards described as "BRIC":** 3 fall in the universe (Blue Lake Rancheria, Pauma, Makah). All 3 are hazard mitigation, `not_harbor`. Each award's amount equals one or more FY2018–19 PDMC subapplications in OpenFEMA: Blue Lake, generator + management costs ($562,355.70); Makah, plan update ($108,117); Pauma, utility and infrastructure protection ($126,000). That supports T1.1's `PC` = PDM competitive reading for these three; the "BRIC" descriptions are wrong. The label doesn't change the match rate.
- **Port of Newport EDA Public Works 070107523** ($1,195,563): Port Dock 5 pier for the commercial fishing fleet (EDA grant list, February 2020), so `sample_harbor`. The award carries the Port's UEI, and auto-matching gets it right. The recipient-profile total that T1.2 noted is a USAspending profile display issue, not a matching issue.

## Light review of BRIC/PDM subapplicants (`subapplicant_harbor_review_pilot.csv`)

- **Scope (user's choice, 2026-11-22):**
  - Auto-match all 441 FY2010+ subapplicants in the 17 counties.
  - Hand-label only those that match the crosswalk or whose title or applicant name has a harbor keyword: 18 rows.
  - PDM competitive rows have no UEI and no title, so they get no harbor label.
- **Result:**
  - 11 matched to an owner. None is a harbor project: Trinidad drought, slope stabilization, road and plans; Quileute plan; Douglas County seismic; two FY2025 rows with no title yet.
  - One harbor applicant among the keyword hits: Port of Port Angeles, PDM FY2019, not approved, not a pilot harbor.

## Effort (for sizing T2.1/T2.2)

Agent wall clock was about 12 minutes for all 241 labels, including the OpenFEMA join and 5 web lookups. That is not a person's pace. The person estimate below uses typical times for each method.

| Method | Awards | Minutes each (person) | Minutes |
|---|---|---|---|
| Record text alone | 207 | 0.5 | 104 |
| OpenFEMA title join | 29 | 2 | 58 |
| Web lookup | 5 | 8 | 40 |
| **Total** | **241** | **~0.85** | **~202** |

## Corrections log

| Date | award_id | Column | Old | New | Source |
| --- | --- | --- | --- | --- | --- |
