# Applicant lists: coverage note (T2.5a)

Snapshot date 2026-11-18. Details and code: `notebooks/03_applicant_lists_profile.ipynb`;
files, checksums and row counts: `data/manifest.csv` (rows with `"task":"T2.5a"`). Pacific =
CA/OR/WA, by the applicant's state (OpenFEMA: the subapplicant's state). No harbor
linking here; that is T2.5b.

How the files were obtained: OpenFEMA by script (`harborfund.ingest.openfema`). The DOT and
MARAD sites returned HTTP 403 to every scripted request on 2026-11-18, so those 13 files were
saved by hand in a browser and registered with `harborfund.ingest.applicants --import-dir`
(manifest notes say `"method": "browser"`). PIDP and TIGER–BUILD are byte-identical to the
files T0.4 checked on 2026-11-17.

Rounds vs fiscal years: DOT/MARAD label rounds by appropriation year ("PIDP 2019",
"INFRA FY2023-24"). The notebook's `round_fy` is the first year in the label. It is not
necessarily the federal fiscal year of application or obligation; T2.5b/T2.2 should use
`harborfund.config.fiscal_year()` on dates when joining awards.

## MARAD PIDP

| Item | Value |
| --- | --- |
| Years | PIDP 2019 – PIDP 2026 (8 rounds) |
| Unit | Eligible applications (ineligible ones not listed) |
| Rows | 1,040 (2019: 58 … 2025: 186, 2026: 174) |
| Identifiers | Applicant name, state. **No** UEI, city, county or applicant type |
| Amounts | PIDP request, project cost (no blanks) |
| Outcome | **Not in the list.** Join from MARAD award lists / USAspending 20.823 (T1.1 classifies by FON) |
| Pacific | CA 76, OR 32, WA 86 = 194 applications ($3.04B requested) |
| Quirks | Row 1 (PIDP 2019) has applicant and project swapped ("Agricultural Maritime Export Facility" / "City of Milwaukee"). Header `Applicant Name ` has a trailing space. 2019–23 = 522 applications vs the ICR's 511 (definitions may differ; not resolved). A few project names are just the applicant's name (e.g. City of Antioch 2019) |
| File | `FY19-26 PIDP Eligible Applicants.xlsx`, sha256 `6d910c1c…df4191`, unchanged since T0.4 |

## DOT TIGER – BUILD – RAISE

| Item | Value |
| --- | --- |
| Years | TIGER 2009 – BUILD 2025 (Round 2), 18 rounds |
| Unit | Eligible applications |
| Rows | 14,621 |
| Identifiers | Applicant name, city (22 blank), state, applicant type (19 blank), urban/rural. **No** UEI or county |
| Amounts | Funding request, project cost |
| Outcome | **Not in the list.** "Project of Merit" (601 rows, RAISE 2022–24 and BUILD 2025 R2 only) is a review rating, not an award. Join awards from DOT announcements / USAspending 20.933 |
| Pacific | CA 1,542, OR 286, WA 636 = 2,464; project type "Maritime": 164 Pacific of 948 national |
| Quirks | Applicant-type labels change: 2009–12 use short labels ("Local Govt.", "Port Authority", "Tribal Govt."); 2013+ use lettered federal categories ("C: City or Township Government") with no port category; 36 distinct labels. Project-type spellings vary ("Bicycle and Pedestrian" / "Bicycle-Pedestrian" / "BicyclePedestrian", "road"). Every BUILD 2018 `State` value has a leading space |
| File | `TIGER 2009 - BUILD 2025 Eligible Applications.xlsx`, sha256 `70ec6e0e…ff6bc9`, unchanged since T0.4 |

## DOT INFRA FY2022+ (spreadsheets)

| Item | Value |
| --- | --- |
| Years | FY2022, FY2023–24, FY2025–26, FY2026 (new file, page updated 2026-10-23) |
| Unit | Applications to the combined MPDG notice (INFRA, Mega, Rural). FY2022 and FY2026 files include applications marked "Not eligible" (78 and 6) |
| Rows | 329 + 191 + 174 + 88 = 782. The FY2022 all-programs list's INFRA sheet (251 rows) equals the eligible rows of the FY22 file (all 251 found) |
| Identifiers | Applicant organization, state, urban/rural; `GrantTrackingNumber` (Grants.gov) in FY2022 and FY2026 only. **No** UEI, city, county or applicant type |
| Amounts | Total funds requested, future eligible project cost |
| Outcome | **In the list:** `Awarded` (INFRA / Mega / Rural / both) and `AwardedAmount`. Awarded: 38, 41, 51, 26 |
| Pacific | CA 111, OR 14, WA 12 = 137 (7 not eligible); 18 awarded |
| Quirks | Award labels vary in spacing ("Yes - INFRA", "Yes- INFRA"); FY2026 says only "Yes". 4 applications appear in both the FY2025–26 and FY2026 files. Sheet named "query" (FY23–24) and "25-25 INFRA Applications" (FY25–26) |
| Files | sha256 FY22 `c51d5da7…`, FY23–24 `5945c75f…`, FY25–26 `16259a34…`, FY26 `f3ed2b5d…`, FY2022 all-programs `4783fb2c…` (all match the browser check earlier the same day) |

## DOT FASTLANE / INFRA FY2016–2021 (PDFs)

| Item | Value |
| --- | --- |
| Years | FASTLANE FY2016, FY2017; INFRA FY2017–18, FY2019, FY2020, FY2021 (DOT page "INFRA – Project Applications") |
| Unit | "Project Applications". Whether ineligible ones are included isn't stated |
| Rows | 212 + 195 + 234 + 193 + 173 + 157 = 1,164 (each equals the file's last row number) |
| Identifiers | Project name, applicant organization, state. **No** UEI, city, county, applicant type or ID |
| Amounts | Request plus one or two cost columns (total cost; federal funding or non-federal funding; future eligible cost; columns differ by year) |
| Outcome | **Not in the list** |
| Pacific | CA 174, OR 21, WA 74 = 269; 47 Pacific rows mention port/harbor/marine/terminal/maritime |
| Quirks | PDFs printed from Excel; names wrap over several lines. `harborfund.ingest.infra_pdfs` reads state and amounts reliably, but project and applicant names come out together and wrapped lines can land on a neighbouring row. Check Pacific names by eye before linking |

## OpenFEMA HMA Subapplications v2: BRIC

| Item | Value |
| --- | --- |
| Years | FY2020–2025 (FY2024: 97 rows; FY2024+ right-censored for H4) |
| Unit | Subapplications submitted to FEMA, all statuses. Subapplications that states screened out and never forwarded are absent (FEMA FOIA Part B) |
| Rows | 4,871 (`program` = "Building Resilient Infrastructure and Communities") |
| Identifiers | Subapplicant UEI (97%), name, city, ZIP, type, benefiting counties (100%); title 80% |
| Amounts | Total and federal-share requested (100%); obligated (28%) and paid (18%) once accepted |
| Outcome | **In the list:** `status` (incl. Ineligible 1,339, Not Selected 597) and FY2020–23 `selectionStatus` (Identified for Further Review / Not Selected / Did Not Meet HMA Requirements) |
| Pacific | CA 154, OR 96, WA 181 = 431; 285 list a coastal county; UEI 428; title 359 |
| Quirks | `benefitingCounties` has names without states and stray out-of-state names on Pacific rows (e.g. "St. Louis"); the coastal flag matches only within the subapplicant's state. FEMA says the dollar fields are not from its official financial systems |

## OpenFEMA HMA Subapplications v2: PDM

| Item | Value |
| --- | --- |
| Years | Competitive FY2000–2019; earmarks FY2022–24 and FY2026; legacy LPDM earmarks FY2008–10 |
| Unit | Subapplications submitted to FEMA |
| Rows | Competitive FY2010–19: 4,292 (all years: 7,780). Earmarks: 319 (FY2022–24) + 142 (FY2026). LPDM: 414 |
| Identifiers | Competitive FY2010–19: name, city, ZIP, type 100%; counties 79%; **no** UEI or title. FY2026 earmarks carry UEIs |
| Amounts | Requested 100%; obligated 62% |
| Outcome | **In the list:** `status` (Closed / Obligated vs Not Selected 383 and Not Approved/Denied 1,225 in FY2010–19). No `selectionStatus` |
| Pacific | Competitive FY2010–19: CA 285, OR 53, WA 159 = 497 (261 coastal-county). Earmarks FY2022+: 67 |
| Linkability (FY2010–19) | **Partly linkable**: applicant name + city/ZIP + county identify the entity (310 distinct Pacific names), so applicant-level matching to an owner/UEI crosswalk is feasible. Project content can't be matched: no titles, only a coarse `primaryActivity` ("Flood control", "Utility and infrastructure protection"), so harbor projects can't be picked out without FOIA titles (T0.4's narrow PDM request) |
| Quirks | `subapplicantCity` sometimes holds a street address. FY2026 earmarks use the plain "Pre-Disaster Mitigation" string (separate them by fiscal year / ID code `PD`) and ALN 97.143 |

## Early Gate 3 read

Gate 3 rule: applicant data usable for at least one program → T3.3. On public data alone it
looks **likely to pass**, pending T2.5b's harbor linking:

| Program | Apply → win usable? | Still lacks |
| --- | --- | --- |
| BRIC | **Yes, best candidate.** Applicants and outcomes in one table, UEIs for crosswalk matching, titles for harbor relevance; 285 Pacific coastal-county subapplications | State-screened subapplications (FOIA Part B); FY2024–25 outcomes still pending (right-censored); linking to harbors (T2.5b) |
| PIDP | **Yes, after an outcome join.** Every applicant is maritime; 194 Pacific applications | Outcomes (join MARAD award lists / USAspending 20.823); UEI; applicant type; ineligible applications |
| INFRA FY2022+ | Yes, but small: outcomes in the list, 137 Pacific applications, few harbor projects | UEI, applicant type, city/county; ineligible applications for FY2023–25 |
| TIGER–RAISE | Possible for the maritime subset (164 Pacific) after an outcome join | Outcomes; UEI; county; consistent applicant types |
| FASTLANE/INFRA FY2016–21 | Only after an outcome join and cleaning PDF names | Outcomes, UEI, applicant type, city/county |
| PDM FY2010–19 | Applicant-level only (who applied, who got funded), not project-level | Titles/UEI (FOIA) to judge harbor relevance |

## Implication for the unsubmitted DOT INFRA FOIA request

`docs/foia/dot_infra_request.md` Part A says FY2016–21 is "not public". It is partly public:
the six PDFs give applicant name, project title, state, request and cost for every round
(fields 1, 5, 6 and 7). Part A could be narrowed to UEI/DUNS, applicant type, city/county,
outcome (awards are also announced publicly) and any internal ID. In Part B, the FY2022
request amount and the outcome for FY2022+ are already public in DOT's per-round INFRA files,
and FY2022 and FY2026 list ineligible applications. Part B could be narrowed to UEI, applicant
type, city/county, and ineligible applications for FY2023–25. Editing the request is
T0.4's/the user's call; not changed here.
