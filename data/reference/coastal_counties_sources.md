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

- **NOAA_CCD_2013**: NOAA Office for Coastal Management, "NOAA's Coastal County Definitions" (list extracted from NOAA STICS, December 2013; 2010 county boundaries). Coastal Shoreline Counties are the asterisked entries. I read the archived copy at https://webarchive.library.unt.edu/web/20161122131910id_/https://coast.noaa.gov/htdata/SocioEconomic/NOAA_CoastalCountyDefinitions.pdf on 2026-11-17. The PDF was read through a text-extraction tool, not opened page by page. The counts (CA 20, OR 7, WA 15) and county names match the extraction, but nobody has checked them against the PDF by eye.
- `port_inventory_harbors`: counted from `data/processed/ports.csv` in zajoseph/fishing-port-access-gaps at commit `53778aeb5b6326a7aad0cae25091e0387c189525` (58 harbors). All 58 sit in one of the 42 NOAA counties, so the "plus any county holding a harbor" rule adds no counties.

## Notes

- No county changes in CA, OR or WA since 2010 (from general knowledge, not checked against Census change notes), so 2010 GEOIDs equal current ones.
- Considered and excluded (user decision 2026-11-17): river and Delta port counties outside NOAA's list. These are OR Multnomah and Columbia, WA Clark and Cowlitz, and CA Sacramento, San Joaquin and Yolo.

## Corrections log

| Date | Row | Column | Old | New | Source |
| --- | --- | --- | --- | --- | --- |
