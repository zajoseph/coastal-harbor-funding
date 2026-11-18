# coastal_counties.csv: sources and rules

Owner: T1.1 (USAspending pilot). Hand-built; edit by hand and record changes below.

## What it is

The county list that defines "coastal CA/OR/WA" for award pulls: 42 counties (CA 20, OR 7, WA 15).
The user approved it on 2026-11-17 (T1.1 chat): NOAA Coastal Shoreline Counties only, with no river or Delta port counties.

## Columns

| Column | Meaning |
| --- | --- |
| `state` | USPS code |
| `state_fips` | 2-digit state FIPS |
| `county_fips` | 5-digit county GEOID (state + county) |
| `county_name` | County name without "County" |
| `noaa_coastal_shoreline` | `true` if on NOAA's Coastal Shoreline Counties list (all rows today) |
| `port_inventory_harbors` | Number of harbors from the fishing-port access-gaps inventory in this county |
| `source` | Source key (below) |

## Sources

- **NOAA_CCD_2013**: NOAA Office for Coastal Management, "NOAA's Coastal County Definitions" (list extracted from NOAA STICS, December 2013; 2010 county boundaries). Coastal Shoreline Counties are the asterisked entries. I read the archived copy at https://webarchive.library.unt.edu/web/20161122131910id_/https://coast.noaa.gov/htdata/SocioEconomic/NOAA_CoastalCountyDefinitions.pdf on 2026-11-17. The PDF was read through a text-extraction tool, not opened page by page. The counts (CA 20, OR 7, WA 15) and county names match the extraction, but nobody has checked them against the PDF by eye. (Since checked by eye in T1.2; see below.)
- `port_inventory_harbors`: counted from `data/processed/ports.csv` in zajoseph/fishing-port-access-gaps at commit `53778aeb5b6326a7aad0cae25091e0387c189525` (58 harbors). All 58 sit in one of the 42 NOAA counties, so the "plus any county holding a harbor" rule adds no counties.

## Visual check against the source PDF (T1.2, 2026-11-18)

**Result: no errors. The CSV needs no changes, so T1.1's `process` step doesn't need re-running.**

- What was done: I opened the same archived PDF in a browser PDF viewer on 2026-11-18. The archive served the capture `20161122133938id_` of the same file, 12 pages. I read the "Summary of Coastal Counties (Year 2010)" table from on-screen images (screenshots and zoomed crops) row by row, comparing FIPS, county name and the Shoreline asterisk with every CA, OR and WA row in the CSV. No text-extraction tool was used.
- Where the rows are: CA on pp. 3–4 (6001 Alameda to 6113 Yolo); OR on p. 9 (41003 Benton to 41057 Tillamook); WA on pp. 10–11 (53009 Clallam and 53011 Clark at the end of p. 10; 53015 Cowlitz to 53073 Whatcom on p. 11).
- Asterisked counties seen in the PDF:
  - **CA (20):** 6001, 6013, 6015, 6023, 6037, 6041, 6045, 6053, 6055, 6059, 6073, 6075, 6079, 6081, 6083, 6085, 6087, 6095, 6097, 6111
  - **OR (7):** 41007, 41011, 41015, 41019, 41039, 41041, 41057
  - **WA (15):** 53009, 53027, 53029, 53031, 53033, 53035, 53045, 53049, 53053, 53055, 53057, 53061, 53067, 53069, 53073
- These match the CSV's 42 `county_fips` and `county_name` values exactly. The PDF lists FIPS without the leading zero for California (e.g. "6001"); the CSV's zero-padded 5-digit GEOIDs are correct.
- Listed in the PDF without an asterisk, so correctly left out of the CSV:
  - **CA:** Riverside, Sacramento, San Benito, San Bernardino, San Joaquin, Siskiyou, Sutter, Trinity, Yolo
  - **OR:** Benton, Clackamas, Columbia, Josephine, Multnomah
  - **WA:** Clark, Cowlitz, Lewis, Skamania
- Checked by: T1.2 task chat. Not checked: the `port_inventory_harbors` counts (out of scope for this check).

## Notes

- No county changes in CA, OR or WA since 2010 (from general knowledge, not checked against Census change notes), so 2010 GEOIDs equal current ones.
- Considered and excluded (user decision 2026-11-17): river and Delta port counties outside NOAA's list. These are OR Multnomah and Columbia, WA Clark and Cowlitz, and CA Sacramento, San Joaquin and Yolo.

## Corrections log

| Date | Row | Column | Old | New | Source |
| --- | --- | --- | --- | --- | --- |
