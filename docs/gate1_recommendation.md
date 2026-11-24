# Gate 1 recommendation: can awards be tied to harbors cheaply?

T1.3, 2026-11-22. Evidence: `notebooks/04_match_rate.ipynb`, `data/reference/award_harbor_truth_pilot.csv`, `data/reference/award_harbor_overrides.csv`. **The user makes the call.** Dollars are nominal.

## Recommendation

**Build the harbor-level panel**, which is the default rule's outcome. Automatic matching finds about 81–87% of pilot-harbor awards by count and 84–95% by dollars, above the ~70% threshold in every crosswalk version. The pass comes with three conditions, each a build step for T2.1/T2.2 rather than a reason to fall back to county level:

1. **Keep the location check as a gate, and add a harbor-relatedness check.** Entity matching on its own over-assigns: 10 of 23 auto-assigned awards are not at the harbor. Auto-assign only entity matches that pass the location check and carry the harbor keyword flag. Everything else that matches, or is flagged, goes to a short manual-review queue: 12% of awards in the pilot.
2. **Decide site vs owner attribution for multi-facility ports.** The choice moves precision from 59% to 73% (count) and decides whether Coos Bay rail, Grays Harbor Terminal 4 and Newport's cargo terminal count toward the fishing harbors. A choice for the user (below).
3. **Count each dollar once.** Drop pass-through subawards whose prime is already counted. In the pilot, one $30.1M subaward duplicates its prime.

## How the match rate was measured (settled definition)

- **Denominator:** a hand-coded truth set, not the share of all in-scope awards. The pilot crosswalk covers only 20 of 58 harbors, so a share of all awards would be low simply because the sample is small.
- **Review universe:** every in-scope prime award (`in_scope & in_fy_window`) and in-scope subaward whose recipient or place-of-performance county is one of the 20 pilot harbors' 17 counties: **241 awards**, 183 primes ($613.5M) and 58 subawards ($168.7M). All were reviewed, not only keyword-flagged ones.
- **Labels:**

| Label | Awards |
|---|---|
| (a) at a named pilot harbor | **16** |
| (b) harbor-related elsewhere | 20 |
| (c) not harbor-related | 204 |
| unclear (excluded) | 1 |

- **What counts as "at" a harbor (site rule):** when the inventory names a bay or harbor complex (San Diego Bay, Humboldt Bay, LA/Long Beach Harbor), any facility in it counts. When it names one marina or terminal (Charleston Marina, Westport Marina, Newport commercial marina, La Conner Marina, Fishermen's Terminal), only that facility counts.
- **Matching:**
  1. UEI.
  2. Legacy DUNS, only if the UEI misses.
  3. The matched harbor's county must equal the award's recipient or place-of-performance county.

  Disagreements are flagged, never auto-assigned.
- **Recall** = share of (a) assigned to the correct harbor with no manual step. **Precision** = share of auto-assigned awards on the correct harbor. Both are measured before overrides.

## Headline numbers (site rule)

| Version | Recall (count) | Recall ($) | Precision (count) | Precision ($) |
|---|---|---|---|---|
| Owner/operator rows | 13/16 = 81% | 84% | 13/22 = 59% | 83% |
| … without `low` rows | 81% | 84% | 59% | 83% |
| + `parent_government` rows | 81% | 84% | 13/23 = 57% | 81% |
| + parent, without `low` | 81% | 84% | 59% | 83% |
| Owner/operator, pass-through subaward dropped | 13/15 = 87% | 95% | 59% | 83% |
| Owner-level rule (owner's other harbor facilities count) | 16/19 = 84% | 86% | 16/22 = 73% | 98% |

- **Uncertainty:** the 95% Wilson interval for 13/16 recall is 57%–93%, so the lower bound is below 70%. This is a small sample: 16 positives in 6 harbors, 9 of them at LA/Long Beach.
- **By program:**

| Program | Recall | Precision |
|---|---|---|
| PIDP | 10/12 (84% of $) | 77% |
| EDA Public Works | 1/2 | 1/1 |
| EDA EAA | 1/1 | 1/4 |
| PIDP marine highway (`other_20823`) | 1/1 | 1/1 |
| BRIC, PDM | no pilot-harbor awards | 0/4 (all tribal-owner hazard mitigation) |

- **PIDP earmark-candidate years (FY2024+):** recall 8/10 (81% of $), precision 73%, vs 5/6 in other years.
- **By owner type:**

| Owner type | Recall | Precision |
|---|---|---|
| Port/harbor districts | 6/6 | 6/10 |
| Cities (incl. port departments) | 6/8 | 6/8 |
| Mixed (Humboldt Bay) | 1/2 | 1/1 |
| Tribal | no harbor awards | 0/4 |

- **Coverage:** only 6 of the 20 pilot harbors have any harbor award in these programs (LA/LB, San Diego, Crescent City, Humboldt Bay, Newport, Westport). The panel will be mostly zeros, which is what the plan's hurdle models expect.

## Main failure causes

| Cause | Cases | Effect | Fix in T2.1/T2.2 |
|---|---|---|---|
| Owner's non-harbor award (tribal hazard plans, Port of Skagit business park) | 5 ($3.6M) | misassignment | harbor-relatedness check (keyword + review) |
| Owner's other facility (Coos Bay rail, Grays Harbor T4, Newport terminal) | 3 ($38.8M) | misassignment under the site rule | facility field in T2.1, or owner-level rule |
| City UEIs: parent-government UEI (Long Beach flood control); "Harbor Department" UEI also used for a city revolving loan fund | 2 ($10.4M) | misassignment | drop `parent_government` rows from auto-matching; check big-city UEIs |
| Entity not in crosswalk (AltaSea tenant; LBCT pass-through) | 2 ($33.1M) | miss | add harbor tenants only where they hold harbor awards; de-duplicate pass-throughs |
| Wrong UEI (Redwood Marine Terminal under Port of Grays Harbor's UEI) | 1 ($8.7M) | miss, but flagged by the location check, not misassigned | keep the location gate; review flags |

- **Description quality:** the Coquille PIDP description is copied from Grays Harbor's Terminal 4 award, and the NWSA Husky Terminal (Tacoma) is coded to Aberdeen. Descriptions and locations are evidence, not ground truth.
- **Keyword flag** (`harbor_kw_flag`): it catches 33 of 36 harbor-related awards (98% of their dollars) while flagging 16% of awards. Outside PIDP, where the flag is always on, it catches 9 of 12 with 6 false hits. **Use it as a pre-filter for review, not as a filter that drops awards:** it missed the San Diego marine-highway berth award ($5.6M), a Port Angeles facility renovation and the Santa Cruz Wharf master plan.

## Effort estimate for T2.1 / T2.2

- **Labelling time:** about **0.85 person-minutes per award** in the pilot (241 awards ≈ 200 minutes). That is 0.5 minutes from the record text alone, 2 with an OpenFEMA title join, and 8 with a web lookup. 5 of 241 needed a web lookup. Agent time was about 12 minutes.
- **Manual-review share:** under the workflow in condition 1, about **12% of awards** go to manual review: 30 of 241. All 16 pilot-harbor awards end up either auto-assigned correctly or in that queue.
- **At 42-county scale:** for the same four programs that is about 55 of the 443 in-scope awards, roughly 2 hours. Programs T2.2 adds (NOAA, NCRF, BUILD/RAISE, INFRA, FWS BIG) will scale this; the effort grows with the number of matched and keyword-flagged awards, not with the total award count.
- **T2.1** should budget extra time on multi-facility port owners (the facility field) and on big-city and county department UEIs.

## Sensitivity

- **Crosswalk version:** recall doesn't move (81% in all four). `low`-confidence and `parent_government` rows add no correct match and one false one, so the recommendation doesn't depend on them.
- **Location gate:** recall is unchanged with or without it. It prevents one misassignment ($8.7M Redwood Marine Terminal → Westport).
- **Site vs owner rule:** recall 81% → 84%, precision 59% → 73%. The pass doesn't depend on this choice, but the panel's meaning does.
- **Small sample:** recall depends on 16 awards. One more miss gives 75%; three more give 62%, below the threshold. The pilot universe includes two hard cases on purpose (Humboldt/Grays Harbor, AltaSea-type tenants). The recall *lower bound* is the reason to keep the review queue, not to drop to county level.
- **Not tested:** programs beyond PIDP/EDA/BRIC/PDM; years before PIDP's FY2020 base; the 38 harbors outside the pilot (mostly WA/OR port districts, which matched 6/6 here).

## Choices for the user at the gate

1. **Gate 1 outcome:** harbor-level panel (recommended) or harbor-level subset plus county-level.
2. **Attribution rule:** site (projects at the named harbor; needs a facility field in T2.1) or owner (all of an owner's harbor-related awards count for its harbor). T1.3 used the site rule as primary. The three `SITE RULE` rows in the overrides table go if you pick the owner rule.
