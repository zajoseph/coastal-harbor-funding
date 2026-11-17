# FOIA request: Federal Emergency Management Agency (FEMA) — Pre-Disaster Mitigation (FY2010–2019) and BRIC: fields missing from OpenFEMA

| | |
| --- | --- |
| Program ID (inventory) | pdm_competitive; bric |
| Status | Drafted 2026-11-17, not submitted |
| Submit via | DHS FOIA portal (select FEMA) or FOIA.gov → Department of Homeland Security → FEMA; questions to fema-foia@fema.dhs.gov |
| Addressed to | FEMA Disclosure Branch |
| Priority (kickoff T0.4) | 3 (supplementary) |
| Postal address | Only needed if mailing; verify on the agency FOIA page first (portal/email submission is preferred) |

> Fill in the bracketed placeholders **outside the repo** (in the portal form or a local copy). This repository is public: never commit your name, address, email or phone.

---

FOIA Officer, Disclosure Branch
Federal Emergency Management Agency
500 C Street SW, Mail Stop 3172
Washington, DC 20472-3172
fema-foia@fema.dhs.gov

**Re: Freedom of Information Act request — Hazard Mitigation Assistance subapplication fields not published in OpenFEMA (PDM FY2010–2019; BRIC subapplications not submitted to FEMA)**

Dear FOIA Officer:

Under the Freedom of Information Act, 5 U.S.C. § 552, and the Department of Homeland Security's FOIA regulations at 6 C.F.R. part 5, I request the following records.

## Records requested

OpenFEMA's "HMA Subapplications" dataset (v2, https://www.fema.gov/api/open/v2/HmaSubapplications) already publishes subapplicant name, type, city, state, federal share requested and status. I am **not** asking for those fields again.

**Part A: PDM competitive subapplications, FY2010–FY2019.** In OpenFEMA, the 4,292 "Pre-Disaster Mitigation" subapplications for program fiscal years 2010–2019 have a blank `subapplicationTitle` and blank `subapplicantUei`. For each of these subapplications, I request, keyed by the OpenFEMA `subapplicationIdentifier` (or the eGrants/NEMIS subapplication number):

1. Subapplication (project) title, or the short project description if no title is held
2. Subapplicant DUNS number (or UEI), if held
3. Benefiting county or counties, if held
4. Subapplication type (project, plan, management cost) and primary activity type, if held

Where a title contains personal information about private individuals, please redact only that information.

**Part B: subapplications never submitted to FEMA (PDM in eGrants; BRIC in FEMA GO).** Every BRIC record in OpenFEMA has a `dateSubmittedToFema`, so subapplications that subapplicants created but the applicant (state, territory or tribe) did not forward to FEMA appear to be excluded. For PDM (FY2010–2019, eGrants) and BRIC (FY2020 to present, FEMA GO), I request a list of subapplications that were created or submitted by a subapplicant but **not submitted to FEMA**, with: program and fiscal year, subapplicant name, subapplicant type, city, county and state, applicant (state/territory/tribe) name, title, federal share requested, and system status (e.g. returned, withdrawn, not forwarded). If FEMA does not hold such records, a statement to that effect fully answers Part B.

## Format

Please provide the records electronically, in a machine-readable format (CSV or Excel; a database export or report from the grants management system is fine), as 5 U.S.C. § 552(a)(3)(B) provides when records are readily reproducible in that form. I am asking for a **list or data extract of the fields above, not copies of the applications themselves.** Producing an extract from an existing electronic database by running a query or report is a search, not the creation of a new record.

If a field is not held, please release the remaining fields rather than delaying the response. If any field or record is withheld, please release all reasonably segregable portions and cite the specific exemption for each withholding. I am happy to receive records on a rolling basis.

## Fee category, fee waiver and fee limit

I am an independent researcher, so I fall in the "all other requesters" fee category. I understand this entitles me to the first two hours of search time and the first 100 pages (or equivalent) free.

I request a waiver of all fees under 5 U.S.C. § 552(a)(4)(A)(iii) and 6 C.F.R. part 5, because disclosure is in the public interest and is not primarily in my commercial interest:

- **Subject:** the records concern identifiable operations of the federal government: how FEMA receives and selects applications for competitive grants under the Pre-Disaster Mitigation (PDM) and Building Resilient Infrastructure and Communities (BRIC) programs.
- **Informative value:** OpenFEMA omits project titles and identifiers for pre-2020 PDM subapplications, without which harbor and port projects cannot be identified, and it omits subapplications that states screened out before submission to FEMA.
- **Contribution to public understanding:** I am building an open, documented dataset of federal harbor and coastal infrastructure funding, which tests whether competitive funding follows community need or capacity to apply. I will publish the cleaned data and documentation in a public repository under a Creative Commons Attribution (CC BY 4.0) license, archive a release with a DOI, and report the findings in a research paper and a short public policy brief. The data will be usable by researchers, journalists, ports and local governments.
- **Significance:** knowing who applied, not only who won, is what makes it possible to tell whether low-capacity communities are absent from these programs or are applying and losing. Award-only data cannot answer that question.
- **No commercial interest:** I have no commercial interest in the records and will not sell them or use them for any commercial purpose.

If the fee waiver is denied, I agree to pay fees up to **$25**. Please contact me before incurring any fees above that amount.

## Contact

If anything in this request is unclear or would be costly to process, please contact me by email; I would much rather narrow the request than have it delayed.

Thank you for your help.

Sincerely,

[REQUESTER FULL NAME]
[MAILING ADDRESS]
[EMAIL]
[PHONE]
