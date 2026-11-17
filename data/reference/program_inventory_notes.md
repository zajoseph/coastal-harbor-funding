# Program inventory: notes and sources

Companion to `program_inventory.csv` (task T0.3). Every source URL was accessed 2026-11-17.

## Columns

| Column | Meaning |
|---|---|
| `program_id` | Stable short key for joins (T1.1, T2.2, T0.4). Never reuse or rename. |
| `program_name`, `agency`, `sub_agency` | Agency names as of 2026. |
| `assistance_listing` | ALN (formerly CFDA). Blank for USACE work and earmarks; the row's `notes` say why. |
| `channel` | `competitive` / `appropriated` / `earmark` (decisions log 2026-11-17). |
| `fy_start` | Integer federal fiscal year: the first year the row's funding appears inside the study window. Programs that predate the window get `2010`. |
| `fy_start_before_window` | `true` if the program existed before FY2010 (so `fy_start = 2010` is the window edge, not the program's real start; exact start dates weren't researched), else `false`. |
| `fy_end` | Integer federal fiscal year of the last funding round, or **blank if the program is still active** (running in FY2026). |
| `eligible_recipients` | As the program's own notice states them; the notice is named in the cell. |
| `award_data_source` | One of `usaspending_assistance`, `usaspending_contracts`, `erdc_dis`, `approps_statement`, `agency_list`, `none`. |
| `award_data_query` | The concrete pull key for that source. |
| `applicant_data_known` | `yes` / `no` / `unknown`, followed by where the data is held or would be requested. Feeds T0.4. |
| `harbor_relevance_filter` | How to separate harbor awards from the rest, or `all`. |
| `source_urls` | Semicolon-separated. |
| `unverified_fields` | Fields not confirmed against an official source (SAM.gov, agency page, NOFO), and why. Empty = all fields checked. |
| `notes` | Anything else. |

Three columns were added beyond the kickoff list: `program_id` (kept from the T0.1 placeholder header), `fy_start_before_window` (see above) and `unverified_fields`, the machine-readable version of the "mark every unverified field" requirement.

The keyword regex used in several filters is `harbor|port|marina|wharf|pier|dock|moorage|boat launch|breakwater|jetty|seawall|bulkhead|waterfront|fishing|seafood|dredg`. It's a starting point for T1.1/T2.2. "port" will over-match (e.g. "support"), so match on word boundaries and review the hits by hand.

## Findings that affect other tasks

1. **ALN 97.047 holds three different things.** Legacy competitive PDM (to FY2019), BRIC (FY2020+) and, from FY2022, PDM used as an earmark vehicle. A pull on 97.047 alone mixes the competitive and earmark channels. Separate them with OpenFEMA `programArea` / `program` and `programFy`.
2. **ALN 20.823 (PIDP) also carries earmarks, now its own row `pidp_cpf`.** Earmarked PIDP money appears in FY2024 (about $70.46M: $120,460,124 appropriated, $50M offered competitively) and FY2026 ($64,702,000 of the $103,330,000 annual appropriation, per MARAD's FY2026 small-ports webinar). `cpf_cds_fy2022` already listed PIDP as a host account, but only as a cross-agency catch-all with no ALN, so a 20.823 pull would have mixed channels. `pidp_cpf` mirrors `pdm_cpf`: tag 20.823 awards that match THUD CPF/CDS tables and move them out of `pidp`. FY2022, FY2023 and FY2025 earmarks not checked; FY2023's appropriation was all offered competitively.
3. **Applicant lists are public for five programs** (T0.4 checks, 2026-11-17; `applicant_data_known` refreshed on 2026-11-17): PIDP (MARAD eligible-applicant workbook FY2019–26), TIGER–BUILD–RAISE (DOT workbook 2009–2025), INFRA FY2022+ (DOT lists), BRIC (OpenFEMA HmaSubapplications v2, FY2020–25, incl. Not Selected/Ineligible) and PDM FY2010–19 (same OpenFEMA dataset, but titles and UEI blank). None of the lists gives outcome and UEI together, so award matching is still needed. OpenFEMA can't contain subapplications that states never forwarded to FEMA.
4. **The old OpenFEMA HMA Projects v4 dataset is gone from the catalog** (T0.4). The `award_data_query` cells for `bric`, `pdm_competitive` and `pdm_cpf` still name it; T1.1/T2.2 should use HmaSubapplications v2 (or its successor) instead. Not changed in this table yet.
5. **The ERDC "DIG" dredging extracts end in 2000.** The page named in the plan (dots.el.erdc.dren.mil/dig.html) has Chief's-report data for 1908–2000 only, so FY2010–2026 dredging has to come from USACE DIS reports (and the NDC "Actual Dredging Cost Data 1963–2018" series). This doesn't reopen the settled decision, which already names DIS, but T2.3 should know before it starts. I haven't checked whether DIS's past-year reports go back to FY2010.
6. **Earmarks have structural zeros.** Earmarks existed in FY2010, were barred FY2011–FY2021, and returned in FY2022. H2 models need to treat FY2011–2021 as "channel closed", not as zero demand.
7. **Sea Grant isn't harbor infrastructure funding.** Its awards go to university Sea Grant programs. The row is kept because the plan names it, but I recommend leaving it out of harbor dollar totals (possibly as an extension-capacity covariate instead). PM decision.
8. **Several prime awards go to states, not harbor owners** (BRIC, PDM, BIG). Harbor linking needs the subapplicant- or facility-level lists (OpenFEMA, FWS award lists), not USAspending prime recipients. This is relevant to the Gate 1 match rate.

## Corrections log

| Date | Row | Column | Old value | New value | Source |
|---|---|---|---|---|---|
| 2026-11-17 | `pidp` | `notes` (FY2026 small-ports reserve) | $112.5M (25% of $450M IIJA funds, from the January 2026 NOFO issued before the FY2026 annual appropriation) | $122,157,000 (25% of $488.628M, after $38.628M of the FY2026 annual appropriation was added to the competition) | MARAD FY2026 SPSP webinar, slide 9; DOT press release 2026-03-26 (both in `pidp.source_urls`) |
| 2026-11-17 | `pidp`, `raise_build_tiger`, `infra`, `bric`, `pdm_competitive` | `applicant_data_known`, `source_urls` | no / unknown, or FOIA-only | yes (public lists; see finding 3); list URLs added | T0.4 handoff (`claude/handoffs/T0.4_2026-11-17.md`), Findings table |

## Programs considered and excluded

| Program | Agency | Reason excluded | Revisit? |
|---|---|---|---|
| Flood Mitigation Assistance (ALN 97.029) | FEMA | Mitigates NFIP-insured structures, not harbor infrastructure. Same OpenFEMA tables as BRIC, so it's cheap to add later | Maybe |
| Hazard Mitigation Grant Program (ALN 97.039) | FEMA | Post-disaster, allocated by disaster declaration and state priority, not a national competition | Robustness only |
| Mega and Rural Surface Transportation (MPDG, with INFRA) | DOT | Not checked in detail; small harbors unlikely to fit project-size or rural-road criteria | Maybe |
| U.S. Marine Highway Program | MARAD | Funds designated marine highway services and projects; few small fishing harbors expected (unverified) | Maybe |
| Small Shipyard Grants | MARAD | Grants to private shipyards, not harbor infrastructure | No |
| Coastal Zone Management grants to states, incl. Section 306A | NOAA | State-administered; project choice happens at state level. Belongs in the state phase | State phase |
| Saltonstall-Kennedy grants | NOAA Fisheries | Fisheries research and development, not infrastructure | No |
| Habitat restoration / Transformational Habitat Restoration and Coastal Resilience (ALN 11.463) | NOAA Fisheries | Habitat projects, not harbors. Note the FY2017 Coastal Resilience Grants program was run jointly with NMFS | No |
| Fishery disaster assistance | NOAA Fisheries | Disaster relief to states and Tribes; spending choices made by states. Some infrastructure use possible | Maybe |
| Clean Vessel Act grants; Sport Fish Restoration boating access | FWS | Formula or small pump-out grants. Located at harbors, but small dollars | Maybe (Clean Vessel Act) |
| Diesel Emissions Reduction Act grants (ALN 66.039) | EPA | Diesel retrofits; overlaps Clean Ports; equipment, not harbor works | No |
| Passenger Ferry Grant Program; Ferry Boat Program | FTA / FHWA | Transit ferry systems; Ferry Boat Program is formula | No |
| Community Development Block Grant | HUD | Formula; local use not traceable to harbors at scale | No |
| Community Facilities grants | USDA Rural Development | Could fund rural harbor facilities; not checked | Maybe |
| Denali Commission | Denali Commission | Alaska only, outside San Diego–Bellingham scope | No |
| Transit Security Grant Program | FEMA | Transit security, not ports | No |
| Loans and credit (MARAD Title XI, TIFIA, CWIFP, NOAA Fisheries Finance) | various | Loans, not grants; a different capacity mechanism | No |

ALNs are given above only where I confirmed them. Other excluded programs' ALNs weren't looked up.

## Source quality

- **Official, checked:** NOFOs on maritime.dot.gov, transportation.gov, epa.gov, grants.gov / simpler.grants.gov; fpi.omb.gov program pages; OpenFEMA dataset pages; coast.noaa.gov; federalregister.gov / govinfo.gov; appropriations.house.gov; gao.gov; sam.gov (Sea Grant).
- **Official documents on non-agency hosts (flagged in `unverified_fields`):** FEMA PDM/BRIC NOFOs hosted by state emergency agencies; OMB ICR documents via omb.report; CRS reports via everycrsreport.com; archived pages via webarchive.library.unt.edu and Wayback.
- **Secondary only (flagged):** CRRC eligible applicants (floods.org), NCRF eligibility summaries, the TIGER II ALN (third-party grants listing).
- SAM.gov Assistance Listing pages render in JavaScript and mostly couldn't be read with my tools, so fpi.omb.gov (OMB's Federal Program Inventory, which draws on SAM.gov) and the NOFOs stood in for them.
