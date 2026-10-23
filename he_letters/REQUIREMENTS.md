# What HCD requires: 6th-cycle housing element review letters

From 2,012 6th-cycle review letters with text (1,212 Out, 764 In), by `scripts/letter_requirements.py`. Each finding is filed under the statutory requirement HCD quotes above it and tagged with HCD's topic label. *Round* is the letter's place among the jurisdiction's 6th-cycle reviews, counting every review on the dashboard. Data: [`requirements.csv`](requirements.csv) (one row per finding), [`letter_outcomes.csv`](letter_outcomes.csv) (one row per letter), [`programs.csv`](programs.csv). The CSVs also cover 43 7th-cycle letters; this report waits until the 7th cycle has enough letters to compare.

## How many reviews it takes

498 of 542 jurisdictions have an In letter in the 6th cycle. The review on which the first In letter came (6 = sixth or later):

| Review | Jurisdictions | Share |
|---|---|---|
| 1 | 24 | 5% |
| 2 | 103 | 21% |
| 3 | 184 | 37% |
| 4 | 113 | 23% |
| 5 | 43 | 9% |
| 6 | 31 | 6% |

## What kind of letter each round brings

Share of all letters in each round, grouped by HCD's finding. "Revisions needed" letters carry the appendix of findings; the AB 1398 letters find the element meets the law but hold compliance until rezoning is done.

| Kind of letter | 1st (512) | 2nd (516) | 3rd (447) | 4th+ (537) |
|---|---|---|---|---|
| **In compliance** | **5%** | **24%** | **52%** | **72%** |
| &nbsp;&nbsp;&nbsp;Adopted, substantial compliance | 1% | 11% | 23% | 51% |
| &nbsp;&nbsp;&nbsp;Adopted, full compliance | 0% | 7% | 16% | 11% |
| &nbsp;&nbsp;&nbsp;Draft meets requirements (adopt next) | 0% | 3% | 11% | 7% |
| &nbsp;&nbsp;&nbsp;Other | 4% | 3% | 2% | 3% |
| **Out of compliance** | **95%** | **73%** | **45%** | **27%** |
| &nbsp;&nbsp;&nbsp;Revisions needed | 92% | 71% | 36% | 11% |
| &nbsp;&nbsp;&nbsp;Meets requirements, rezoning not done (AB 1398) | 0% | 2% | 7% | 11% |
| &nbsp;&nbsp;&nbsp;Compliance revoked | 0% | 0% | 1% | 2% |
| &nbsp;&nbsp;&nbsp;Rezoning ordinance reviewed, still short | 0% | 0% | 1% | 1% |
| &nbsp;&nbsp;&nbsp;Other | 3% | 0% | 0% | 1% |
| **No finding** | **1%** | **3%** | **2%** | **1%** |
| &nbsp;&nbsp;&nbsp;Other | 1% | 3% | 2% | 1% |

## Requirements HCD finds unmet, by round

Share of "revisions needed" letters in each round where HCD wrote at least 25 words of its own (not standard sentences that appear in 25+ letters) under the requirement. The requirement is the statute HCD quotes as the heading of each finding.

| Requirement | Code | 1st (469) | 2nd (365) | 3rd (160) | 4th+ (60) |
|---|---|---|---|---|---|
| Program: adequate sites / rezoning | 65583(c)(1) | 79% | 73% | 70% | 70% |
| Affirmatively furthering fair housing (programs) | 65583(c)(5) | 68% | 74% | 71% | 72% |
| Sites inventory and analysis | 65583(a)(3) | 89% | 61% | 40% | 20% |
| Affirmatively furthering fair housing (assessment) | 65583(c)(10) | 85% | 57% | 39% | 17% |
| Governmental constraints | 65583(a)(5) | 86% | 53% | 28% | 10% |
| Public participation | 65583(c)(9) | 67% | 35% | 21% | 15% |
| Program: remove governmental and nongovernmental constraints | 65583(c)(3) | 41% | 52% | 48% | 37% |
| Programs: schedule of actions, timelines and objectives | 65583(c) | 62% | 33% | 16% | 13% |
| Program: assist housing for lower- and moderate-income households | 65583(c)(2) | 60% | 35% | 15% | 8% |
| Special housing needs | 65583(a)(7) | 60% | 17% | 9% | 2% |
| Review and revision of the prior element | 65588 | 55% | 16% | 10% | 0% |
| Nongovernmental constraints | 65583(a)(6) | 50% | 21% | 10% | 2% |
| Quantified objectives | 65583(b) | 44% | 15% | 9% | 2% |
| Program: ADUs affordable to lower-income households | 65583(c)(7) | 39% | 16% | 6% | 5% |
| Household characteristics (overpayment, overcrowding, conditions) | 65583(a)(2) | 40% | 12% | 3% | 0% |
| At-risk assisted housing | 65583(a)(9) | 27% | 7% | 4% | 5% |
| Program: preserve at-risk housing | 65583(c)(6) | 25% | 9% | 3% | 2% |
| Population, employment and housing needs (incl. ELI) | 65583(a)(1) | 23% | 7% | 1% | 0% |
| Program: conserve and improve existing housing | 65583(c)(4) | 7% | 4% | 1% | 0% |
| Energy conservation | 65583(a)(8) | 4% | 1% | 0% | 0% |

## Issues HCD raises, by round

HCD's topic labels within the findings, counted when HCD wrote 25+ words of its own on the topic, as a share of "revisions needed" letters in each round. *Staying power* is the share in 3rd-and-later letters divided by the share in 1st letters: near 1 or above means the issue keeps coming back.

| Issue | 1st | 2nd | 3rd | 4th+ | Staying power |
|---|---|---|---|---|---|
| Nonvacant sites | 65% | 56% | 49% | 48% | 0.75 |
| Realistic capacity | 70% | 44% | 31% | 18% | 0.40 |
| Specific programs | 57% | 49% | 38% | 38% | 0.66 |
| Processing and permit procedures | 64% | 39% | 28% | 13% | 0.38 |
| Zoning for a variety of housing types / shelters | 67% | 33% | 24% | 22% | 0.35 |
| Land use controls | 59% | 35% | 22% | 13% | 0.33 |
| Housing for persons with disabilities | 51% | 33% | 19% | 8% | 0.31 |
| Small and large sites | 53% | 27% | 19% | 13% | 0.34 |
| Sites inventory / parcel listing | 50% | 28% | 17% | 12% | 0.31 |
| AFFH: goals, actions, metrics and milestones | 32% | 35% | 31% | 45% | 1.10 |
| AFFH: disproportionate needs and displacement | 48% | 25% | 13% | 12% | 0.26 |
| ADUs | 49% | 24% | 14% | 2% | 0.22 |
| AFFH: local data, knowledge and other factors | 42% | 25% | 12% | 7% | 0.26 |
| Environmental constraints | 45% | 18% | 12% | 8% | 0.24 |
| Infrastructure | 45% | 21% | 6% | 7% | 0.14 |
| AFFH: fair housing enforcement and outreach | 37% | 20% | 6% | 8% | 0.17 |
| AFFH: contributing factors | 31% | 23% | 12% | 12% | 0.38 |
| Progress in meeting the RHNA | 30% | 18% | 11% | 2% | 0.27 |
| Extremely low-income households | 39% | 9% | 2% | 0% | 0.03 |
| AFFH: access to opportunity | 30% | 16% | 8% | 3% | 0.21 |
| Fees and exactions | 33% | 13% | 4% | 2% | 0.11 |
| AFFH: R/ECAPs and areas of affluence | 24% | 15% | 7% | 8% | 0.30 |
| Programs (general) | 7% | 21% | 28% | 27% | 3.82 |
| AFFH: integration and segregation | 24% | 13% | 4% | 5% | 0.19 |
| Electronic sites inventory | 10% | 15% | 22% | 20% | 2.18 |
| Publicly owned sites | 19% | 11% | 7% | 10% | 0.41 |
| Housing Conditions | 22% | 6% | 3% | 0% | 0.11 |
| Identified Sites and Affirmatively Furthering Fair Housing (AFFH) | 14% | 12% | 7% | 10% | 0.55 |
| On/off-site improvements | 21% | 6% | 1% | 0% | 0.04 |
| Zoning and fees transparency | 22% | 4% | 0% | 0% | 0.00 |
| Employee Housing | 21% | 3% | 1% | 0% | 0.02 |
| Special Housing Needs | 16% | 5% | 2% | 0% | 0.12 |
| Farmworkers | 18% | 2% | 0% | 0% | 0.00 |
| Transitional and Supportive Housing | 13% | 5% | 1% | 0% | 0.07 |
| Sites identified in prior planning periods | 14% | 4% | 1% | 0% | 0.06 |
| Reasonable Accommodation | 13% | 5% | 2% | 0% | 0.10 |
| Design Review | 10% | 7% | 4% | 5% | 0.42 |
| Zoning for Lower-Income Households | 11% | 5% | 4% | 2% | 0.28 |
| Replacement housing | 15% | 2% | 0% | 0% | 0.00 |

## The last hurdles before compliance

For the 452 jurisdictions that reached an In letter after at least one "revisions needed" letter: what HCD still raised in that last letter before the In.

| Requirement | Share of last letters |
|---|---|
| Affirmatively furthering fair housing (programs) (65583(c)(5)) | 75% |
| Program: adequate sites / rezoning (65583(c)(1)) | 68% |
| Program: remove governmental and nongovernmental constraints (65583(c)(3)) | 49% |
| Sites inventory and analysis (65583(a)(3)) | 46% |
| Affirmatively furthering fair housing (assessment) (65583(c)(10)) | 43% |
| Governmental constraints (65583(a)(5)) | 38% |
| Program: assist housing for lower- and moderate-income households (65583(c)(2)) | 26% |
| Public participation (65583(c)(9)) | 26% |
| Programs: schedule of actions, timelines and objectives (65583(c)) | 26% |
| Special housing needs (65583(a)(7)) | 16% |

| Issue | Share of last letters |
|---|---|
| Nonvacant sites | 47% |
| Specific programs | 44% |
| AFFH: goals, actions, metrics and milestones | 35% |
| Realistic capacity | 34% |
| Processing and permit procedures | 33% |
| Land use controls | 30% |
| Programs (general) | 26% |
| Zoning for a variety of housing types / shelters | 25% |
| Small and large sites | 24% |
| Housing for persons with disabilities | 23% |
| AFFH: local data, knowledge and other factors | 20% |
| Sites inventory / parcel listing | 19% |
| AFFH: disproportionate needs and displacement | 19% |
| AFFH: contributing factors | 18% |
| ADUs | 16% |

## Program commitments HCD asks for

Share of "revisions needed" letters whose findings mention each commitment (keyword match). *Written for the letter* counts only sentences HCD wrote for that jurisdiction, leaving out standard sentences that appear in 25+ letters; it is the better measure of what HCD actually asked that city or county to do. The round columns use it.

| Commitment | Any mention | Written for the letter | 1st | 2nd | 3rd | 4th+ |
|---|---|---|---|---|---|---|
| AFFH: geographic targeting, metrics and milestones | 85% | 69% | 62% | 76% | 73% | 62% |
| AFFH: anti-displacement / tenant protections | 75% | 68% | 77% | 65% | 57% | 40% |
| Specific timelines (dates, not 'ongoing') | 71% | 66% | 72% | 64% | 56% | 53% |
| AFFH: housing mobility / higher-opportunity areas | 72% | 60% | 58% | 61% | 62% | 60% |
| Rezone to meet the RHNA shortfall by a date | 84% | 58% | 68% | 47% | 56% | 60% |
| AFFH: place-based revitalization | 70% | 57% | 58% | 62% | 50% | 37% |
| Emergency shelters: zoning, capacity, standards (§ 65583(a)(4)) | 59% | 56% | 75% | 43% | 38% | 27% |
| Group homes / residential care for 7+ persons | 48% | 48% | 67% | 39% | 24% | 13% |
| Parking standards | 44% | 43% | 55% | 38% | 25% | 15% |
| Permit processing / streamlining (incl. SB 35) | 42% | 39% | 55% | 30% | 24% | 13% |
| Reasonable accommodation procedures | 39% | 36% | 52% | 30% | 13% | 10% |
| By-right approval for 20% lower-income projects (§ 65583.2(h)-(i)) | 37% | 35% | 49% | 26% | 19% | 18% |
| Density bonus law update (§ 65915) | 36% | 33% | 50% | 22% | 18% | 13% |
| Objective standards / design review changes | 32% | 30% | 40% | 25% | 19% | 10% |
| Extremely low-income housing actions | 43% | 29% | 45% | 20% | 11% | 3% |
| Surplus Land Act / publicly owned sites | 29% | 26% | 31% | 22% | 18% | 37% |
| Lot consolidation / small sites incentives | 26% | 26% | 33% | 24% | 14% | 8% |
| Employee and farmworker housing (HSC 17021.5, 17021.6) | 24% | 23% | 43% | 9% | 4% | 3% |
| Fees: analysis, reduction or deferral | 25% | 23% | 40% | 9% | 11% | 8% |
| Zoning, fee and standards transparency online (§ 65940.1) | 24% | 19% | 36% | 8% | 1% | 2% |
| Replacement housing on sites with existing units | 15% | 14% | 26% | 6% | 1% | 2% |
| Supportive housing by right (§ 65651) | 19% | 13% | 18% | 10% | 8% | 2% |
| No net loss monitoring (§ 65863) | 12% | 11% | 16% | 9% | 8% | 3% |
| Low barrier navigation centers (§ 65660) | 13% | 9% | 14% | 7% | 4% | 5% |
| Transitional and supportive housing as a residential use | 11% | 9% | 13% | 6% | 4% | 3% |
| ADU monitoring and alternative actions if targets missed | 8% | 8% | 13% | 4% | 5% | 0% |
| Mid-cycle review of sites / nonvacant assumptions | 7% | 7% | 9% | 5% | 7% | 10% |
| Water and sewer priority for affordable housing (§ 65589.7) | 16% | 6% | 11% | 4% | 1% | 0% |
| Large sites: lot splits, phasing, specific plans | 2% | 2% | 3% | 1% | 1% | 2% |

## How much HCD writes

| Round | Revisions-needed letters | Median words of findings | Median words written for the letter |
|---|---|---|---|
| 1st | 469 | 2,875 | 2,264 |
| 2nd | 365 | 1,380 | 1,101 |
| 3rd | 160 | 1,004 | 812 |
| 4th+ | 60 | 740 | 596 |

## Programs HCD names when it finds compliance

In 397 In letters HCD lists programs the jurisdiction "must continue timely and effective implementation" of: 4,840 program mentions, grouped by keywords in the program name.

| Category | Programs named | Share |
|---|---|---|
| Other | 815 | 17% |
| Special needs, homelessness and shelters | 748 | 15% |
| Affordable housing assistance and incentives | 675 | 14% |
| Fair housing, mobility and anti-displacement | 557 | 12% |
| Rezoning and adequate sites | 512 | 11% |
| Remove constraints and streamline | 420 | 9% |
| Zoning code amendments and housing types | 363 | 8% |
| ADUs | 352 | 7% |
| Conserve, rehabilitate and preserve | 155 | 3% |
| Infrastructure, water and sewer | 106 | 2% |
| Monitoring and reporting | 74 | 2% |
| Outreach, education and collaboration | 63 | 1% |

| Most common program names | Letters |
|---|---|
| accessory dwelling units | 117 |
| affirmatively furthering fair housing | 65 |
| reasonable accommodation | 50 |
| objective design standards | 44 |
| zoning code amendments | 43 |
| density bonus | 41 |
| lot consolidation | 33 |
| adequate sites | 32 |
| extremely low-income households | 27 |
| affordable housing incentives | 25 |
| emergency shelters | 24 |
| fair housing | 22 |
| affirmatively further fair housing | 22 |
| accessory dwelling units (adu | 21 |
| housing mobility | 19 |
| special needs housing | 19 |
| affordable housing development | 18 |
| residential care facilities | 17 |
| low barrier navigation centers | 16 |
| density bonus ordinance | 16 |
| housing rehabilitation | 16 |
| large sites | 15 |
| farmworker housing | 15 |
| zoning ordinance amendments | 15 |
| transitional and supportive housing | 14 |
| support funding for farmworker housing | 14 |
| group homes | 13 |
| homeless/unhoused needs | 13 |
| improve access to resources | 13 |
| zoning amendments | 12 |

## Programs HCD asks to revise

2,461 findings in Out letters address a specific program by name, grouped by keywords in the program name:

| Category | Findings |
|---|---|
| Other | 720 |
| Special needs, homelessness and shelters | 374 |
| Affordable housing assistance and incentives | 267 |
| Rezoning and adequate sites | 259 |
| Zoning code amendments and housing types | 160 |
| Remove constraints and streamline | 149 |
| ADUs | 149 |
| Fair housing, mobility and anti-displacement | 148 |
| Conserve, rehabilitate and preserve | 126 |
| Outreach, education and collaboration | 44 |
| Infrastructure, water and sewer | 39 |
| Monitoring and reporting | 26 |

## Language that appears only when an element is in compliance

Standard paragraphs (from `PATTERNS.md`) where 10% or fewer of the letters using them are Out findings.

- **507 letters, 1993–2026:** The <JTYPE> must monitor and report on the results of these and other programs through the annual progress report, required pursuant to Government Code section 65400. Please be aware, Government Code section 65585, subdivision (i) grants HCD authority to review any action or failure to act by a local government that it determines is inconsistent with an adopted housing element or housing element l…
- **211 letters, 2020–2026:** HCD is pleased to find the adopted housing element in substantial compliance with State Housing Element Law (Gov. Code, § 65580 et seq) as of the date of this letter. The adopted element was found to be substantially the same as the revised draft element that HCD’s <DATE> review determined met statutory requirements.
- **180 letters, 2020–2026:** The revised draft element meets the statutory requirements described in HCD’s <DATE> review. The housing element will substantially comply with State Housing Element Law (Gov. Code, § 65580 et seq) when it is adopted, submitted to, and approved by HCD, in accordance with Government Code section 65585.
- **169 letters, 2020–2026:** HCD is pleased to find the adopted housing element in full compliance with State Housing Element Law (Article <N> of the Gov. Code). The adopted element addresses the statutory requirements described in HCD’s <DATE> review.
- **39 letters, 2023–2026:** As a reminder, the <JTYPE> must continue timely and effective implementation of all programs including but not limited to the following:
