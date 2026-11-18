# docs/foia/ — applicant-data requests (task T0.4)

Goal: applicant-level data (who applied, not just who won) for H3 and Gate 3. Public lists come first; FOIA only for what isn't public.

**This repo is public.** Requests here carry `[REQUESTER FULL NAME]`, `[MAILING ADDRESS]`, `[EMAIL]`, `[PHONE]` placeholders. Fill them in only in the agency portal or a local copy, never in git. `foia_log.csv` has no personal details.

FOIA returns go to `data/raw/foia/<agency>/` (not tracked) and get a row in `data/manifest.csv`. Check them before anything derived from them reaches `data/reference/` (see `data/README.md`). Analysis of returns belongs to T2.5.

## Public-availability checks (2026-11-17)

| Program | Public list? | Where | Rows / coverage | Fields present | Missing (requested) |
| --- | --- | --- | --- | --- | --- |
| PIDP (MARAD) | **Yes** | https://www.maritime.dot.gov/grants-finances/federal-grant-assistance/pidp-applicant-list → `FY19-26 PIDP Eligible Applicants.xlsx` (https://www.maritime.dot.gov/sites/marad.dot.gov/files/2026-10/FY19-26%20PIDP%20Eligible%20Applicants.xlsx; page updated 2026-10-27; 75,694 bytes; sha256 `6d910c1c8a1200ad6319aab2c0b734533d3e496bca1e2838a307d9e982df4191`) | 1,040 eligible applications: 2019 58, 2020 63, 2021 107, 2022 141, 2023 153, 2024 158, 2025 186, 2026 174. CA 76, OR 32, WA 86 | Round, Applicant Name, Project Name, State, PIDP Request, Project Cost (no blanks) | UEI, applicant type, city/county, outcome, ineligible applications → `marad_pidp_request.md` (optional) |
| TIGER/BUILD/RAISE (DOT OST) | **Yes** | https://www.transportation.gov/policy-initiatives/tiger/tiger-application-list → `TIGER 2009 - BUILD 2025 Eligible Applications.xlsx` (page updated 2025-07-16; 1,275,598 bytes; sha256 `70ec6e0efd0999b287aa97572f36baadb9bcb3cee7975a1047545d49cfff6bc9`) | 14,621 eligible applications, TIGER 2009 – BUILD 2025 Round 2; 948 typed "Maritime" | Round, Project Name, Applicant Name, State, City, Project Type, Urban/Rural, Funding Request, Project Cost, Applicant Type, Project of Merit (601 "Yes") | Outcome, UEI, county, ineligible applications → `dot_raise_build_tiger_request.md` |
| INFRA (DOT OST) | **Yes** (rechecked 2026-11-18, T2.5a) | FY2016–21: DOT "INFRA – Project Applications" PDFs (FASTLANE FY2016, FY2017; INFRA FY2017–18, FY2019, FY2020, FY2021). FY2022+: https://www.transportation.gov/grants/dot-navigator/eligible-applicants-previous-rounds-iija-grant-funding and DOT's INFRA pages (`INFRA FY22 Applications.xlsx`, `INFRA FY23-24 Applications.xlsx`, `INFRA Applications 25-26.xlsx`, `INFRA FY26 Applications.xlsx`). URLs and sha256 in `data/manifest.csv` | FY2016–21: 1,164 applications (CA/OR/WA 269). FY2022+: 782 applications (CA/OR/WA 137) | FY2016–21: project, applicant, state, request, cost; no outcome. FY2022+: applicant, state, urban/rural, request, eligible cost, `Awarded`/`AwardedAmount`; ineligible applications in FY2022 and FY2026; Grants.gov tracking number in FY2022 and FY2026 | UEI/DUNS, applicant type, city/county (all years); FY2016–21 outcomes; IDs and ineligible applications for FY2016–21 and FY2023–25 → `dot_infra_request.md` (narrowed 2026-11-18) |
| BRIC (FEMA) | **Yes** | OpenFEMA HMA Subapplications v2, https://www.fema.gov/api/open/v2/HmaSubapplications (catalog lastRefresh 2026-07-27) | 4,871 BRIC subapplications FY2020–2025 (FY2024 97, FY2025 954, mostly still "Submitted to FEMA"). CA 154, OR 96, WA 181. 288 "Special Governmental District" | Subapplicant name, UEI, type, city, state, ZIP, benefiting counties, title, federal share, status, selectionStatus (Identified for Further Review 2,017; Not Selected 1,083; Did Not Meet HMA Requirements 712), BCA fields | Subapplications never submitted to FEMA (0 records lack `dateSubmittedToFema`) → Part B of `fema_pdm_competitive_request.md` |
| PDM competitive (FEMA) | **Yes** (new finding) | Same OpenFEMA dataset now carries "Pre-Disaster Mitigation" FY2000–2019 (the older HMA Projects v4 dataset is no longer in the OpenFEMA catalog) | FY2010–19: 4,292 subapplications. Status: Closed 2,536; Not Approved/Denied 1,225; Not Selected 383; Obligated 142; other 6. 497 in CA/OR/WA | Subapplicant name, type, city, state, federal share, date submitted, status | Title and UEI/DUNS blank → Part A of `fema_pdm_competitive_request.md` |
| EDA 11.300 / 11.307 | No | NOFO says EDA "may publish any applications it receives"; none found (T0.3, rechecked) | — | — | Full list → `eda_public_works_eaa_request.md` |
| NOAA OCM resilience (CRRC) | No | https://coast.noaa.gov/funding/ira/resilience-challenge/ publishes counts only (~870 LOIs, 120 invited, 19 selected per Commerce release) | — | — | Full list → `noaa_ocm_resilience_request.md` |
| NCRF (NFWF/NOAA) | No | NFWF "is not an agency or establishment of the United States" (16 U.S.C. 3701(a)), so FOIA does not reach NFWF | — | — | NOAA-held lists → `noaa_ncrf_request.md` |
| USACE CAP §107 | No | Not published | — | — | Pacific districts → `usace_cap107_request.md` |
| FWS BIG | No | Funded Tier 2 summaries and funding by state only (fws.gov BIG library) | — | — | Full list → `fws_big_request.md` |
| EPA Clean Ports | No | https://www.epa.gov/ports-initiative/clean-ports-program-selections lists the 55 selections only | — | — | Full list → `epa_clean_ports_request.md` |
| FEMA PSGP | Not checked further | Robustness-only; investment justifications are security-sensitive | — | — | Not requested |
| Sea Grant | — | Skipped per kickoff | — | — | — |

Row counts above exclude header rows and were computed in-browser from the files on 2026-11-17. The files themselves aren't downloaded into `data/raw/` yet (T2.5's job). Check the sha256 values when they are.

**Data-quality notes for T2.5:**
- PIDP list row 1 (PIDP 2019) has applicant and project swapped ("Agricultural Maritime Export Facility" / "City of Milwaukee").
- The PIDP list has 522 applications for 2019–23, but OMB ICR 202308-2133-001 says MARAD's internal list had 511 for those years. The two lists may be defined differently.
- DOT applicant-type labels change across rounds (e.g. "Local Govt." vs "C: City or Township Government", "Port Authority" vs "D: Special District Government"), so they need a crosswalk.

## Where to submit

| File | Agency | Channel |
| --- | --- | --- |
| `marad_pidp_request.md` | MARAD | FOIA.gov → DOT → MARAD, or foia.marad@dot.gov |
| `dot_raise_build_tiger_request.md` | DOT OST | FOIA.gov → DOT → OST, or ost.foia@dot.gov |
| `dot_infra_request.md` | DOT OST | same as above |
| `fema_pdm_competitive_request.md` | FEMA | DHS FOIA portal (choose FEMA) or FOIA.gov → DHS → FEMA |
| `eda_public_works_eaa_request.md` | EDA | Commerce FOIAXpress Public Access Link, FOIA.gov → Commerce → EDA, or email (https://eda.gov/foia/) |
| `noaa_ocm_resilience_request.md` | NOAA | Commerce FOIAXpress Public Access Link or FOIA.gov → Commerce → NOAA |
| `noaa_ncrf_request.md` | NOAA | same as above |
| `usace_cap107_request.md` | USACE SPL, SPN, NWP, NWS | Email each district FOIA office (one copy each) or FOIA.gov → Army → USACE |
| `fws_big_request.md` | FWS | FOIA.gov → Interior → FWS |
| `epa_clean_ports_request.md` | EPA | FOIA.gov → EPA |

DOT's own portal (securefoia.dot.gov) currently points requesters to FOIA.gov. Channels for Commerce, Interior and EPA were taken from agency pages or general knowledge and weren't tested. Use whichever the portal offers.

## Common terms in every request

- Requester category: **all other** (independent researcher): 2 hours of search and 100 pages free.
- Public-interest **fee waiver** requested; the argument is an open dataset (CC BY 4.0), a paper and a policy brief.
- Fee limit **$25** if the waiver is denied; contact before going higher.
- **National** scope: same effort as Pacific-only, and it supports the optional national extension. USACE is the exception: districts hold their own records, so only the Pacific districts are asked.
- Electronic, machine-readable extract, not the applications themselves. Standard fields: applicant name, UEI/DUNS, applicant type, city/county/state, project title, amount requested, FY/round, outcome, internal ID.

## Log conventions (`foia_log.csv`)

- One row per program per channel. A "public download" row records a located list; a "portal/email" row records a request. A request covering two programs lists both IDs separated by `; `.
- `status`: `public list located` · `partly public` · `drafted, not submitted` · `submitted` · `acknowledged` · `fee/clarification pending` · `partial release` · `complete` · `denied/appealed` · `not requested`.
- `expected_response` = 20 business days after the agency receives the request (5 U.S.C. 552(a)(6)(A)); `next_followup` = the next business day after that. Current dates are provisional and assume submission by 2026-11-20. Recompute from the acknowledgement date.
- USACE: record each district's tracking number in `tracking_number` as `SPL:…; SPN:…; NWP:…; NWS:…`.
