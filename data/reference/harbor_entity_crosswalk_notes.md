# harbor_entity_crosswalk.csv: notes

Owner: T1.2 (crosswalk pilot), built 2026-11-18. Hand-built: every row was typed from the sources below, and nothing is generated from raw data. Edit by hand and record changes in the Corrections log below.

## What it is

A pilot crosswalk for **20 harbors** from the fishing-port access-gaps inventory (`data/processed/ports.csv`, zajoseph/fishing-port-access-gaps at commit `53778aeb5b6326a7aad0cae25091e0387c189525`). Each harbor is linked to:
- the entities that own or operate it, and
- the federal recipient identifiers (UEI and legacy DUNS) those entities use.

It gives 29 rows: 23 owner, 4 operator and 2 parent_government. T1.3 uses it to measure how many T1.1 awards match automatically. Per the decisions log, this table is the only harbor↔entity link.

## Sample selection rule (agreed with the user 2026-11-18 before research)

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
| `harbor_id` | `port_id` from the port inventory |
| `harbor_name` | `port_name` from the port inventory, unchanged |
| `state` | USPS code |
| `county_fips` | 5-digit county GEOID of the harbor's inventory county. All values are in `coastal_counties.csv`, and the county names match the inventory (checked by script, 2026-11-18) |
| `entity_name` | Entity name in plain form. The registered name can differ (e.g. "LOS ANGELES, CITY OF" for the Harbor Department); see `notes` |
| `entity_role` | `owner`: owns the harbor or its main public facilities, or holds the tidelands grant under them. `operator`: runs the harbor or marina under the owner (lessee, enterprise, county division). `parent_government`: the general government to which awards may go instead of the owning department |
| `entity_type` | `harbor_district`, `port_district`, `city`, `city_department`, `county`, `county_department`, `tribal_government`, `tribal_enterprise`, `private` |
| `uei` | UEI(s), primary first, separated by `;`. Empty = none found or none could be assigned (see `notes`) |
| `legacy_duns` | 9-digit DUNS, separated by `;`. Includes DUNS from DUNS-only profiles that have no UEI. Leading zeros kept (read as string) |
| `id_source` | `usaspending_recipient <profile URL>` for the primary profile; `other (…)` when no profile applies |
| `match_confidence` | Confidence that the listed identifiers belong to this entity's role at this harbor. `high`: single clear registration at the right address or with harbor alternate names. `medium`: the right government, but a government-wide registration, or a profile with no UEI. `low`: several candidate registrations and none clearly the harbor's, or unidentified private entities |
| `source_urls` | Sources for ownership and role, plus extra profile URLs; separated by ` ; ` |
| `unverified_fields` | Columns not confirmed by a primary source, separated by `;` |
| `notes` | Evidence, alternate IDs, same-name traps, and flags for T1.3 |

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

## Minutes per harbor (for sizing T2.1)

- **Wall clock:** about 22 minutes from staging T1.1's tables (10:48 ET) to the finished CSV (about 11:10 ET), for 20 harbors. That is roughly 1 minute per harbor.
- This includes batched API lookups (many harbors per call) and about 15 web searches to confirm ownership. It excludes sample selection and the coastal-county check.
- **Caution:** this is the pace of an agent batching API calls, not of a person. Time went mostly to the hard cases: big cities, department-registered counties, private or mixed harbors, and the two T1.1 awards. Port and harbor districts with one registration took seconds.
- **For T2.1:** expect about 1–2 minutes per simple district harbor and 5–15 minutes per mixed, county or private harbor, done the same way. The remaining 38 harbors are mostly WA/OR port districts, so a T2.1 crosswalk is a single-session task. Verifying the "low" rows in SAM.gov will need the user to run API calls on the Mac.

## Open items

- County of Orange, CA: run a SAM.gov entity search for "County of Orange" with CAGE/POC details to find the OC Community Resources / Dana Point Harbor registration. A script for the user is in the T1.2 handoff.
- Port of Newport: T1.1 has an EDA Public Works award under K5ZVUGL5VE53, but the profile's all-years total shows only the PIDP amount. Not resolved.
- Ownership for the port-district harbors (Crescent City, San Diego, Newport, Charleston, Westport) rests on the inventory names and recipient profiles. No separate ownership page was opened for them.

## Corrections log

| Date | Row | Column | Old | New | Source |
| --- | --- | --- | --- | --- | --- |
