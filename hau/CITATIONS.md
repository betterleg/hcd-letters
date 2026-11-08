# Statute citations in the letters (HAU)

Parsed from the letter text by `scripts/parse_citations.py`: 20,708 letter–citation rows from 1,333 letters with text. Data: [`citations.csv`](citations.csv). Counts are letters citing each, not mentions.

Format: `65915(o)(8)` for the Government Code; other codes are prefixed, e.g. `HSC 17021.5`.

## Check against HCD's Statutory Reference tags

HCD gave the 1,304 tagged letters with text 5,194 section tags. For each tag:

| Result | Tags | Share |
|---|---|---|
| Found by the parser | 2,458 | 47% |
| Covered by a range the letter cites (e.g. §§ 66310–66342) | 1,108 | 21% |
| **Number appears in the text but the parser missed it** | 35 | 1% |
| Not in the letter text at all (HCD tags the topic, not only what the letter cites) | 1,593 | 31% |

The parser also found 7,205 cited sections HCD didn't tag.

### Parser misses to fix

Tags whose number is in the text but wasn't read as a citation, most frequent first, with one example each (task number and the words around it):

| Section | Letters | Example |
|---|---|---|
| `66312` | 8 | CSTASK0024806: …ious Government Code Sections Article 1. General Provisions 66310 65852.150 (a) 66311 65852.150 (b) 66312 65852.150 (c) 66313 General Definition Section 65852.2… |
| `66310` | 8 | CSTASK0024806: …ble New Government Code Sections Previous Government Code Sections Article 1. General Provisions 66310 65852.150 (a) 66311 65852.150 (b) 66312 65852.150 (c)… |
| `21064.3` | 3 | CSTASK0026391: …of the Tiburon Ferry Terminal, a major transit stop as defined under Public Resources Code section 21064.3, subdivision (b) and therefore potentially eligible… |
| `21080.66` | 2 | CSTASK0027076: …tar.com/Calendar.aspx#docaccess-eaa2524360b48dbf634bac57ae37e000, PDF page 112. 5 Pub. Res. Code, § 21080.66. 6 PL25-0067 (SA) and PL25-0068 (TTM 20794) Chino P… |
| `50053` | 2 | CSTASK0022013: …for the lower income density bonus units shall be set at an affordable rent, as defined in Section 50053 of the Health and Safety Code.” 3 Health and Safety C… |
| `50093` | 2 | CSTASK0019603: …for the fractional unit.” 5 Gov. Code, § 65915, subd. (b)(1). 6 HSC, § 50079.5, subd. (a). 7 HSC, § 50093. 8 HSC, § 50093, subd. (b). Lee Butler, Director of Pl… |
| `17958.7` | 1 | CSTASK0025588: …wed the five homes to be developed at this property. 61 Cal. Health & Saf. Code, §§ 17958, 17958.5, 17958.7. 62 Group Home TA at p. 30 (discussing state occupan… |
| `66322` | 1 | CSTASK0025477: …ing guidance on the combination of units allowable under Government Code sections 66311.7 (formerly 66322) and 66323. Since the issuance of that letter, the Cit… |
| `50675.2` | 1 | CSTASK0020516: …cifically Government Code section 65650, subdivision (b), references Health and Safety Code section 50675.2 in defining supportive housing. Specifically, Health… |
| `66316` | 1 | CSTASK0024796: …ssory Dwelling Unit Approvals 66314 65852.2(a)(1)(A), (D)(i)-(xii), (a)(4)-(5) 66315 65852.2 (a)(8) 66316 65852.2 (a)(6) 66317 65852.2 (a)(3), (a)(7) 66318 6585… |
| `798` | 1 | CSTASK0018075: …eholds within the local jurisdiction.” 10 In addition, the legislative body “may 4 Civil Code, § 798 et seq. and Gov. Code §§ 65863.7, 65863.8. 5 Gov. Code,… |
| `798.56` | 1 | CSTASK0018075: …Code, § 798 et seq. and Gov. Code §§ 65863.7, 65863.8. 5 Gov. Code, § 66300 et seq. 6 Civil Code, § 798.56, subds. (g), (h). 7 Gov. Code, § 65863.8. 8 Gov. Code… |
| `66330` | 1 | CSTASK0024293: …852.2 (f) 66325 65852.2 (g) 66326 65852.2 (h) 66327 65852.2 (i) 66328 65852.2 (k) 66329 65852.2 (l) 66330 65852.2 (m) 66331 65852.2 (n) 66332 65852.23. Article… |
| `21155` | 1 | CSTASK0018323: …assistance provided in the previous letter. As you are aware, Public Resources Code (PRC) section 21155, subdivision (b) – which serves as the basis for the d… |
| `50079.5` | 1 | CSTASK0010701: …its for moderate-income, lower income, very low income, or ELI households, as specified in Sections 50079.5, 50093, 50105, and 50106 of the Health and Safety Co… |
| `17929` | 1 | CSTASK0018834: …onsolidated on one floor or area on a specific floor. (AB 491, sec. 1, adding Health & Saf. Code, § 17929, subd. (a)(2).) Further, it is unclear if the structur… |

## Most-cited sections

| Citation | Letters |
|---|---|
| `65585` | 675 |
| `65589.5` | 519 |
| `65580` | 441 |
| `66323` | 350 |
| `66314` | 347 |
| `65583` | 317 |
| `66321` | 312 |
| `65583.2` | 307 |
| `66326` | 303 |
| `66333` | 297 |
| `66317` | 292 |
| `66315` | 280 |
| `66313` | 278 |
| `65588` | 261 |
| `66332` | 237 |
| `66316` | 226 |
| `65852.2` | 206 |
| `66340` | 200 |
| `66334` | 175 |
| `65915` | 173 |
| `65852.22` | 164 |
| `66341` | 158 |
| `66311.5` | 150 |
| `66310` | 148 |
| `66329` | 146 |
| `66328` | 145 |
| `CIV 714.3` | 143 |
| `66333.5` | 141 |
| `17556` | 141 |
| `66324` | 134 |
| `66335` | 134 |
| `66331` | 125 |
| `CIV 4751` | 124 |
| `17980.12` | 123 |
| `66320` | 123 |
| `CIV 4740` | 120 |
| `CIV 4741` | 120 |
| `65852.26` | 119 |
| `66322` | 78 |
| `65583.4` | 69 |

## Most-cited subdivisions

| Citation | Letters |
|---|---|
| `65585(j)` | 617 |
| `65589.5(d)` | 445 |
| `65585(l)` | 382 |
| `65585(i)` | 360 |
| `66323(a)` | 326 |
| `66321(b)` | 310 |
| `66314(d)` | 296 |
| `65583.2(c)` | 263 |
| `65588(e)` | 255 |
| `66317(a)` | 250 |
| `65589.5(h)` | 249 |
| `66323(b)` | 242 |
| `65583(c)` | 216 |
| `66332(a)` | 209 |
| `66313(e)` | 199 |
| `66314(b)` | 190 |
| `66333(b)` | 179 |
| `66317(c)` | 177 |
| `66334(a)` | 171 |
| `66326(b)` | 160 |
| `66333(d)` | 159 |
| `66313(d)` | 156 |
| `66326(c)` | 154 |
| `66323(d)` | 152 |
| `66317(d)` | 146 |
| `66333(g)` | 144 |
| `66314(a)` | 142 |
| `66329(a)` | 142 |
| `66326(d)` | 141 |
| `66311.5(a)` | 141 |
| `CIV 714.3(b)` | 141 |
| `66326(a)` | 139 |
| `66324(c)` | 126 |
| `65585(b)` | 125 |
| `66313(b)` | 124 |
| `66313(m)` | 122 |
| `66335(2)` | 120 |
| `CIV 4740(a)` | 120 |
| `CIV 4741(a)` | 120 |
| `65852.2(e)` | 93 |

## Most-cited full citations

| Citation | Letters |
|---|---|
| `65585(l)(1)` | 373 |
| `66323(a)(4)(A)(ii)` | 215 |
| `66314(d)(11)` | 208 |
| `66323(a)(3)(A)` | 204 |
| `66321(b)(3)` | 203 |
| `65589.5(h)(3)` | 180 |
| `66314(b)(1)` | 174 |
| `66323(a)(1)` | 172 |
| `65589.5(d)(6)` | 159 |
| `66326(c)(1)` | 149 |
| `66317(a)(2)(A)` | 147 |
| `66326(b)(2)(A)` | 145 |
| `66326(b)(2)(B)` | 144 |
| `66317(a)(2)(B)` | 143 |
| `66321(b)(2)(A)` | 142 |
| `65589.5(d)(5)` | 142 |
| `66317(d)(1)` | 142 |
| `66321(b)(2)(B)` | 141 |
| `66326(b)(1)` | 134 |
| `66321(b)(2)` | 134 |
| `66323(a)(1)(A)` | 132 |
| `65583(c)(1)(A)` | 126 |
| `66324(c)(1)` | 124 |
| `65585(i)(1)(A)` | 102 |
| `65588(e)(4)(C)(iii)` | 81 |
| `65585(i)(1)` | 76 |
| `65588(e)(3)` | 73 |
| `65852.2(h)(2)(B)` | 62 |
| `65852.2(h)(3)(A)` | 62 |
| `65585(i)(1)(B)` | 56 |
| `66321(b)(4)` | 51 |
| `65589.5(f)(6)` | 49 |
| `65852.2(e)(1)` | 45 |
| `65852.2(c)(2)(C)` | 45 |
| `66323(a)(4)` | 45 |
| `65588(e)(4)(C)` | 44 |
| `66323(a)(3)` | 40 |
| `66314(d)(12)` | 40 |
| `65588(e)(4)(C)(i)` | 38 |
| `65852.2(e)(1)(A)` | 38 |
