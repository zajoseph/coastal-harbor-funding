# harbor_entity_crosswalk.csv: notes

Owners: T1.2 (20-harbor pilot, 2026-11-18); **T2.1 (full harbor universe, 2026-11-23)**. Hand-built: every row was typed from the sources below, and nothing is generated from raw data. Edit by hand and record changes to existing rows in the Corrections log below. The `sam_*` columns are filled by `harborfund.ingest.sam apply` (a documented script), not by hand.

## What it is

The crosswalk for the **whole harbor universe: 63 harbors**. That is the 58 harbors of the fishing-port access-gaps inventory (`data/processed/ports.csv`, zajoseph/fishing-port-access-gaps at commit `53778aeb5b6326a7aad0cae25091e0387c189525`, the same commit T1.2 used), plus 5 harbors added in T2.1 under the approved addition rule (`harbor_additions.csv` and its notes). Each harbor is linked to:
- the entities that own or operate it (and, where relevant, its parent government and tenants or terminal operators with harbor awards), and
- the federal recipient identifiers (UEI and legacy DUNS) those entities use, plus their SAM.gov registration status.

It has **81 rows**: 66 owner, 8 operator, 5 parent_government, 2 tenant_operator. Confidence: high 46, medium 18, low 17. Per the decisions log, this table is the only harbor↔entity link. Facilities of multi-facility owners, and which harbor each belongs to under the site rule, are in `harbor_facilities.csv`.

**54 of 63 harbors have at least one owner UEI.** The 9 without one are listed under "No UEI found" below; 8 of them are owned by special districts with no USAspending profile, which the SAM.gov script looks up by name.

## T2.1 method (2026-11-23)

- **Kept T1.2's 29 rows.** T1.3's problem list was checked. One change: the Long Beach Harbor Department row (see Corrections log). The County of Orange row stays without a UEI until the SAM.gov lookup runs.
- **38 new inventory harbors** (CA 20, OR 8, WA 10). Owners were taken from the inventory's harbor names and its `facilities.csv` operator column, then checked on owner or agency pages where the owner was not obvious (Shelter Cove, Port of Chinook, Port of Peninsula). Identifiers were looked up through the USAspending public API from a browser on usaspending.gov:
  - `POST /api/v2/recipient/` (keyword search) and `GET /api/v2/recipient/{id}/?year=all` (profile: UEI, DUNS, address, alternate names, totals);
  - `POST /api/v2/autocomplete/recipient/` for names the keyword search missed;
  - `POST /api/v2/search/spending_by_award/` with award keywords (e.g. "Port of San Francisco", "Marina del Rey") to find the registration a harbor's own awards went to.
- **Big governments** (cities, counties, City and County of SF) follow T1.2's rule: the harbor's own department registration if one exists (Port of SF at Pier 1), otherwise the city- or county-wide registration with `medium`, and the general registration as `parent_government` (`low`). Where no registration could be tied to the harbor beyond one award (County of LA for Marina del Rey; City of San Diego for Mission Bay), the row is `low`.
- **Tenants and terminal operators** (`tenant_operator`): only T1.1 recipients with awards for work at a harbor in the universe. AltaSea (Port of LA) and LBCT LLC (Long Beach). SSA Terminals (Seattle) was not given a row because its work is at Terminal 5, outside WA-seattle under the site rule. The Coquille Tribe's corporation (Mithihkwuh EDC) is the **operator** of the added Ko'Kwel Wharf.
- **Added harbors**: 5 rows of owners plus their operators/parents, after the user approved the addition rule (2026-11-23).
- **Checks** (by script, 2026-11-23): every inventory harbor_id has at least one row; every `county_fips` is in `coastal_counties.csv`; harbor names, states and counties match the inventory; no duplicate harbor × entity × role; every owner UEI in `harbor_facilities.csv` is in the crosswalk. `harborfund.link.crosswalk_match` still runs on the new table (pandas 3.0.5); 38 of 38 tests pass.

### Notes for T2.2 (matching against this table)
- **`tenant_operator` rows are not used by `crosswalk_match`'s four versions**, which filter on owner/operator/parent roles. T2.2 should add a version that includes them (T1.3 code not edited, per the kickoff).
- **Owners with more than one harbor share a UEI**, so their awards come back `flagged_multi`: Humboldt Bay Harbor District (CA-humboldt-bay, CA-shelter-cove), Port of Willapa Harbor (WA-bay-center, WA-tokeland), Port of Bellingham (WA-bellingham, WA-blaine). Resolve with place of performance and `harbor_facilities.csv`.
- **Rerunning T1.3's pilot scoring on this table changes its numbers.** `sample_counties()` takes the counties from the crosswalk, so the review universe grows from 241 to 403 awards. To reproduce T1.3, use the crosswalk at PR #9's merge commit (`f9e942f`).
- More T1.1 data issues found: the Port of Port Townsend FY2022 EDA record carries Port Angeles' Marine Trades Industrial Park description; `recipient_is_state_gov` is True for most port districts' PIDP awards (not only Newport).

## Pilot sample selection rule (T1.2; agreed with the user 2026-11-18 before research)

1. **Universe:** the 58 inventory harbors (CA 30, OR 12, WA 16), all inside the 42 NOAA coastal counties.
2. **Size:** about 20 harbors, roughly in proportion to state counts: **CA 10, OR 5, WA 5**.
3. **Owner type:** cover every type present in the inventory: port/harbor district, city (including city port departments), county, tribal, private/marina, and mixed public/private.
   - **State-agency gap:** no inventory harbor appeared to be owned by a state agency, and research found none. The sample therefore has no state-agency owner, and none was added from outside the inventory (user's decision).
   - The California State Lands Commission does show up as the underlying owner of leased sovereign land at Huntington Harbour. It gets no row, because awards would not go to it.
4. **Size of harbor:** include large cargo ports (San Diego Bay, LA/Long Beach, Seattle, Coos Bay/Charleston, Humboldt Bay) and small fishing harbors (e.g. Depoe Bay, Bay Center, La Push).
5. **Award overlap:** recipient names in T1.1's in-scope prime awards (`in_scope & in_fy_window`) and subawards were read before selection. The sample was then split between:
   - harbors whose owner appeared to have USAspending awards (11 expected), and
   - harbors whose owner appeared to have none (9 expected).
   T1.3 can then measure both matches and misses. After research, 10 harbors have at least one crosswalk UEI among T1.1's in-scope recipients (see the summary below). Seattle moved to "no" because only the Northwest Seaport Alliance, not the Port of Seattle, appears in T1.1.
6. **T1.1 hard cases are included:**
   - CA-humboldt-bay and WA-westport cover the Eureka award that carries Port of Grays Harbor's UEI.
   - WA-la-conner, the inventory harbor nearest the Swinomish award, covers the Swinomish case.
7. **Deliberate traps:**
   - CA-santa-cruz: the City of Santa Cruz has awards, but the harbor belongs to an independent port district.
   - OR-charleston: another entity has an award in the same place.
   - WA-seattle: a joint-venture recipient.
   - CA-dana-point and CA-channel-islands: counties that register by department.

| harbor_id | State | Owner type (sample stratum) | Size | Picked because |
|---|---|---|---|---|
| CA-humboldt-bay | CA | mixed (harbor district + city) | large | Hard case: wrong UEI on the Eureka award; city and district both own facilities |
| CA-crescent-city | CA | harbor district | small | Small harbor that won PIDP |
| CA-trinidad | CA | tribal | small | Tribal owner; awards may not be harbor projects |
| CA-san-diego-bay | CA | port district | large | Large port, several UEIs |
| CA-los-angeles-long-beach | CA | city port departments | large | Awards go to city-named registrations |
| CA-morro-bay | CA | city | small | City harbor with no award |
| CA-santa-cruz | CA | port district | medium | Wrong-entity trap (City of Santa Cruz) |
| CA-channel-islands | CA | county | medium | County owner with no separate harbor registration |
| CA-dana-point | CA | county owner + private operator | medium | Public-private master lease |
| CA-huntington-harbour | CA | private/mixed | small | Private marinas |
| OR-newport | OR | port district | medium | Port with PIDP and EDA |
| OR-charleston | OR | port district | large | Coquille Tribe award in the same place |
| OR-winchester-bay | OR | county | small | County owner; marina division has its own no-UEI profile |
| OR-depoe-bay | OR | city | small | Very small city harbor |
| OR-warrenton | OR | city | small | City harbor; shares a PacFIN code with Astoria |
| WA-westport | WA | port district | medium | Other side of the Eureka UEI case |
| WA-la-conner | WA | port district | small | Nearest harbor to the Swinomish award |
| WA-la-push | WA | tribal | small | Tribal owner plus tribal enterprise operator |
| WA-seattle | WA | port district | large | Joint-venture recipient (NWSA) |
| WA-bay-center | WA | port district | small | Tiny port district with no award |

## Columns

| Column | Meaning |
|---|---|
| `harbor_id` | `port_id` from the port inventory, or a T2.1 addition ID `<ST>-add-<slug>` (rule in `harbor_additions_notes.md`) |
| `harbor_name` | `port_name` from the port inventory, unchanged (for additions: `port_name` in `harbor_additions.csv`) |
| `state` | USPS code |
| `county_fips` | 5-digit county GEOID of the harbor's inventory county. All values are in `coastal_counties.csv`, and the county names match the inventory (checked by script, 2026-11-18) |
| `entity_name` | Entity name in plain form. The registered name can differ (e.g. "LOS ANGELES, CITY OF" for the Harbor Department); see `notes` |
| `entity_role` | `owner`: owns the harbor or its main public facilities, or holds the tidelands grant under them. `operator`: runs the harbor or marina under the owner (lessee, enterprise, county division). `parent_government`: the general government to which awards may go instead of the owning department (secondary in matching). `tenant_operator` (T2.1): a tenant or terminal operator that received a T1.1 award for work at the harbor; only T1.1 recipients are included |
| `entity_type` | `harbor_district`, `port_district`, `city`, `city_department`, `county`, `county_department`, `tribal_government`, `tribal_enterprise`, `private` |
| `uei` | UEI(s), primary first, separated by `;`. Empty = none found or none could be assigned (see `notes`) |
| `legacy_duns` | 9-digit DUNS, separated by `;`. Includes DUNS from DUNS-only profiles that have no UEI. Leading zeros kept (read as string) |
| `id_source` | `usaspending_recipient <profile URL>` for the primary profile; `other (…)` when no profile applies |
| `match_confidence` | Confidence that the listed identifiers belong to this entity's role at this harbor. `high`: single clear registration at the right address or with harbor alternate names. `medium`: the right government, but a government-wide registration, or a profile with no UEI. `low`: several candidate registrations and none clearly the harbor's, or unidentified private entities |
| `source_urls` | Sources for ownership and role, plus extra profile URLs; separated by ` ; ` |
| `unverified_fields` | Columns not confirmed by a primary source, separated by `;` |
| `notes` | Evidence, alternate IDs, same-name traps, and flags for T1.3/T2.2 |
| `sam_status` (T2.1) | SAM.gov registration status of the row's primary UEI: `active`, `expired`, other SAM status in lower case (e.g. `inactive`), or `none_found` (not returned by the default query nor by the expired re-check). Rows without a UEI: `none_found` if the SAM name lookup returned nothing, `name_candidates_review` if it returned candidates (pick by hand; never assign by name). `not_checked` until `harborfund.ingest.sam apply` has run |
| `sam_checked_date` (T2.1) | Date (UTC) of the SAM.gov response the status came from |
| `sam_source` (T2.1) | `SAM Entity API v3 <raw response file>`; statuses of secondary UEIs when they differ; or the name query used |

## How identifiers were found

- **Source:** USAspending public API, 2026-11-18, run from a browser on usaspending.gov:
  - `POST /api/v2/recipient/` (keyword search) and `GET /api/v2/recipient/{id}/?year=all` (profile: UEI, DUNS, address, alternate names, all-years totals);
  - `POST /api/v2/search/spending_by_award/` for the two hard-case awards.
- Profile URLs (`https://www.usaspending.gov/recipient/<id>/latest`) are recorded so every identifier can be rechecked.
- **SAM.gov was not used:** its pages render in JavaScript, as in T0.3. One case needs a SAM.gov entity search (County of Orange, CA; see open items).
- **Ownership** comes from owner or agency pages, State Lands Commission records, county releases, and the inventory's own names, listed per row in `source_urls`.
- **Legacy DUNS** is what USAspending shows on the profile. USAspending back-fills UEIs onto old awards, so a DUNS-only profile (no UEI) usually means pre-2022 awards that were never linked to a UEI. These DUNS are recorded so T1.3 can match older awards.

## Hard cases and how they were resolved

1. **Eureka award with Port of Grays Harbor's UEI** (T1.1 open issue).
   - Award 693JF72444090, $8,672,986, funds design and permitting for a heavy-lift offshore-wind terminal at the **Redwood Marine Terminal**, which the Humboldt Bay Harbor District owns.
   - The Port of Grays Harbor profile (KC4CLTVG4HR8) lists "HUMBOLDT BAY HARBOR RECREATION CONSERVATION DISTRICT" among its alternate names. The UEI was misapplied to Humboldt's award.
   - **Resolution:** the crosswalk keeps each UEI with its true owner. T1.3 should override this award to CA-humboldt-bay. A UEI-only match would put it at WA-westport.
2. **Swinomish FY2022-round PIDP** (award 693JF72344040, $11,073,627).
   - Funds a Swinomish Port Authority master plan, boat ramp, commercial-pier design and mooring float **on tribal lands**. The place of performance is coded WI54880 (Superior, WI).
   - It is not a La Conner Marina (Port of Skagit) project, so the Swinomish Indian Tribal Community (UEI M4EWJ7AWAD17) gets no row.
   - **Resolution:** recorded as a harbor missing from the inventory, for T2.1 to decide.
3. **Big cities register their port departments under the city name.**
   - Port of Los Angeles = "LOS ANGELES, CITY OF" (TYUJZWJ8N568, San Pedro address).
   - Port of Long Beach = "CITY OF LONG BEACH" (DBSHZ2LVFAE6, 415 W Ocean Blvd).
   - **Resolution:** chosen by registration address and harbor alternate names. General-city UEIs are recorded as `parent_government` with `low` confidence, because each city has many department UEIs.
4. **Counties registering by department.**
   - County of Ventura: no Harbor Department registration found, so the county-wide UEI is given (`medium`).
   - County of Orange, CA: **no UEI assigned**. None of 8+ CA registrations is the harbor's. Candidates are listed in `notes`.
5. **Operators with USAspending profiles but no UEI or DUNS:** Dana Point Harbor Partners, Salmon Harbor Marina, Quileute Tribal Enterprises. Recorded as "No UEI found" with the profile URL.
6. **Same-name recipients in other states.** Every match must use UEI, never name alone:
   - City of Eureka (SD, KS, IL); City of Long Beach (WA, NY, MS); City of Trinidad (CO); City of Warrenton (MO); County of Douglas (12 other states); County of Orange (NY, VA, TX, IN).
7. **Bad alternate names in recipient profiles**, a data-quality signal:
   - Trinidad Rancheria → "CHEROKEE NATION"
   - Quileute → "LAC DU FLAMBEAU BAND…"
   - Port of LA → "TOWN OF STONINGTON"
   - Port of Grays Harbor → "MIAMI-DADE COUNTY"

## No UEI found (kept, not dropped)

| harbor_id | Entity | Where searched |
|---|---|---|
| CA-dana-point | County of Orange (OC Community Resources / Dana Point Harbor) | USAspending recipients "County of Orange", "Orange County", "Dana Point Harbor": 8+ CA department UEIs, none the harbor's |
| CA-dana-point | Dana Point Harbor Partners, LLC | USAspending recipient "Dana Point Harbor Partners": profile without UEI/DUNS |
| CA-huntington-harbour | Private marina lessees | USAspending recipients "PG Marina Investors", "Peters Landing", "Huntington Harbour": none |
| OR-winchester-bay | Salmon Harbor Marina | USAspending recipient "Salmon Harbor": profile without UEI/DUNS |
| WA-la-push | Quileute Tribal Enterprises | USAspending recipient "Quileute Tribal Enterprises": profile without UEI/DUNS |

Every harbor has at least one entity with a UEI, except **CA-dana-point** (19 of 20).

T2.1 additions (searched 2026-11-23 with recipient keyword search, recipient autocomplete and award-keyword search; all queued for a SAM.gov name lookup):

| harbor_id | Entity | Where searched |
|---|---|---|
| CA-noyo-harbor | Noyo Harbor District | Recipients "Noyo", "Noyo Harbor District", "Harbor District"; autocomplete; awards "Noyo Harbor" (only USACE contractors and Caltrans) |
| CA-pillar-point | San Mateo County Harbor District | Recipients "San Mateo County Harbor", "Mateo Harbor", "Mateo Co"; autocomplete; awards "San Mateo County Harbor District", "Pillar Point Harbor" |
| CA-moss-landing | Moss Landing Harbor District | Recipients "Moss Landing", "Moss Landing Harbor", "Landing Harbor"; autocomplete; awards "Moss Landing Harbor (District)" (USACE contractors only) |
| CA-port-san-luis | Port San Luis Harbor District | Recipients "Port San Luis", "San Luis Harbor", "Luis Harbor"; autocomplete; awards "Port San Luis (Harbor District)" |
| CA-oceanside | Oceanside Small Craft Harbor District | Recipients "Oceanside Small Craft", "Small Craft Harbor"; awards "Oceanside Small Craft Harbor", "Oceanside Harbor" |
| CA-shelter-cove | Shelter Cove Fishing Preservation, Inc. | Recipients "Shelter Cove" (23 unrelated businesses) |
| OR-florence | Port of Siuslaw | Profile exists without UEI/DUNS; awards "Port of Siuslaw" (two 2008 ODOT awards) |
| WA-chinook | Port of Chinook | Recipients "Chinook", "Port of Chinook", "Chinook Port"; autocomplete; awards "Port of Chinook" |
| WA-nahcotta | Port of Peninsula | Recipients "Peninsula", "Port of Peninsula", "Peninsula Port", "Port of Pen"; autocomplete; awards "Port of Peninsula" |

Harbors with no owner UEI after T2.1: **9 of 63** (CA-dana-point plus the eight district harbors above other than Shelter Cove, whose owner is the Humboldt Bay district).

## Minutes per harbor

### T2.1 (38 inventory harbors + 5 additions)
- **Agent time (wall clock, kept separate from a person's):** the 38 inventory harbors took about 20 minutes, from the first batched recipient search (about 18:03 PT) to the last profile check (about 18:22 PT). That is about **0.5 minutes per harbor**, with 20–50 lookups per browser call. Writing the rows, the facilities table and the additions table took about 15 minutes more.
- **Person estimate (not timed; my estimate of doing the same steps by hand on usaspending.gov):**
  - port/harbor district with one registration (about 20 harbors): **5 min** each;
  - city or county owner with several registrations (about 11): **15 min** each;
  - district with no USAspending profile (8): **10 min** each to rule out, plus the SAM lookup;
  - added harbor (5, incl. evidence for the rule): **20–30 min** each.

  About **7–8 person-hours** for T2.1's crosswalk rows, excluding the facilities table (about 1–2 hours) and the SAM run.

### T1.2 (20 pilot harbors)

- **Wall clock:** about 22 minutes from staging T1.1's tables (10:48 ET) to the finished CSV (about 11:10 ET), for 20 harbors. That is roughly 1 minute per harbor.
- This includes batched API lookups (many harbors per call) and about 15 web searches to confirm ownership. It excludes sample selection and the coastal-county check.
- **Caution:** this is the pace of an agent batching API calls, not of a person. Time went mostly to the hard cases: big cities, department-registered counties, private or mixed harbors, and the two T1.1 awards. Port and harbor districts with one registration took seconds.
- **For T2.1:** expect about 1–2 minutes per simple district harbor and 5–15 minutes per mixed, county or private harbor, done the same way. The remaining 38 harbors are mostly WA/OR port districts, so a T2.1 crosswalk is a single-session task. Verifying the "low" rows in SAM.gov will need the user to run API calls on the Mac.

## Open items

- **SAM.gov:** run `harborfund.ingest.sam` on the Mac (20 requests: 7 UEI batches, 13 name lookups, plus up to 2 expired re-checks). With a 10-requests-per-day key this takes 2–3 days. County of Orange, CA is among the name lookups. Name hits go to `data/processed/sam/sam_name_candidates.csv` for a hand decision, recorded here.
- Port of Newport: T1.1 has an EDA Public Works award under K5ZVUGL5VE53, but the profile's all-years total shows only the PIDP amount. Not resolved.
- Ownership for the port-district harbors (Crescent City, San Diego, Newport, Charleston, Westport) rests on the inventory names and recipient profiles. No separate ownership page was opened for them.
- **T2.1 ownership not confirmed on an owner page:** Redondo Beach, Newport Beach, Vallejo, Berkeley, Monterey, Point Arena, Moss Landing (district name only), Oceanside (the Small Craft Harbor District is believed to hold the harbor), Blaine (Port of Bellingham, from the inventory name). Recorded in `unverified_fields`.
- **Coordinates for the 5 added harbors** are blank in `harbor_additions.csv` (no primary-source point opened). Fill before T2.6.

## Corrections log

| Date | Row | Column | Old | New | Source |
| --- | --- | --- | --- | --- | --- |
| 2026-11-23 | CA-los-angeles-long-beach / City of Long Beach Harbor Department (DBSHZ2LVFAE6) | `match_confidence` | high | medium | T1.3 truth set rows 40–41: this UEI also carries City of Long Beach flood-control and CARES Act loan-fund awards |
| 2026-11-23 | same row | `notes` | (T1.2 text) | T1.2 text + "CORRECTION (T2.1, 2026-11-23): …" sentence on the City's non-port awards | T1.3 handoff, open issues |
| 2026-11-23 | all 29 T1.2 rows | new columns `sam_status`, `sam_checked_date`, `sam_source` | (none) | `not_checked`, blank, blank | T2.1 kickoff (column addition, not a value change) |
