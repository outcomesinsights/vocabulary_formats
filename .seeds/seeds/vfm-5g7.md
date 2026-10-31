---
id: vfm-5g7
title: 'Non-conforming NDCs (21 CFR 207.33(a): an NDC is numeric): the three lower-case oxygen codes are excluded as worked examples; whether the other 36 follow is not ruled'
status: resolved
type: decision
created_at: 2026-10-31T14:00:02.452446+00:00
updated_at: 2026-10-31T14:17:08.544616+00:00
resolved_at: 2026-10-31T14:13:31.420459+00:00
resolution: Three lower-case oxygen codes excluded from NDC.ALPHANUM's target as non-conforming under 21 CFR 207.33(a) (commit 81f449a). The other 36 non-numeric NDC codes stay in the target (ruled 2026-10-31, vfm-39i).
tags:
  - ndc
  - cfr-207-33
  - non-conforming
  - alphanum
  - case
  - exclusion
  - validation-target
  - rxnav
  - dailymed
  - ryan
  - 2026-10-31
relationships:
  - target_id: vfm-39i
    rel_type: questioned-by
    created_at: 2026-10-31T14:00:11.481819+00:00
---

## The request (Ryan, 2026-10-31)

Ryan, verbatim: "capture this reasoning in a seed and exclude them or use them as examples of how
we filter out "bad" NDCs that donn't conform to CFR 207.33(a)".

"Them" means the three lower-case NDC concept_codes in Athena: `1549912340a`, `1549912340b` and
`5812800010a`. They came up under the case-exact ruling (vfm-8k1). Today they pass
`NDC.ALPHANUM` only because `\w` admits lower case. Before he ruled, Ryan asked: "verify they are
bad codes".

## The rule: an NDC is a numeric code

21 CFR 207.33(a), fetched from the eCFR API on 2026-10-31 (text as of 2026-09-01):

```
(a) What is the NDC for a drug and what products must have unique NDCs ? The NDC for a drug is a numeric code.
(i) The first segment of the NDC is the labeler code and consists of 4, 5, or 6 digits.
(ii) The second segment of the NDC is the product code and consists of 3 or 4 digits, ...
(iii) The third segment of the NDC is the package code and consists of 1 or 2 digits ...
```

So a concept_code that contains any letter does not conform. This repo calls such a code a
**non-conforming NDC**.

## How the three lower-case codes were checked

Each check below asked a different authority. All of them agree that the three codes are bad.

1. **Athena** (`CONCEPT.csv`, release 20260625). All three are "OXYGEN - oxygen gas", class
   "11-digit NDC", `invalid_reason` empty. They have no rows in `CONCEPT_RELATIONSHIP` and none in
   `CONCEPT_SYNONYM`. Each sits beside numeric codes of the same product:
   `15499123401`..`15499123409` and `58128000100`..`58128000109`.

2. **The source label.** DailyMed SPL setid `1df5a2d7-fb0f-49b1-981b-d019f436750c`, "OXYGEN
   (OXYGEN ) GAS [FIRST CHOICE MEDICAL EQUIPMENT INC.]", version 1, published 2010-07-19, never
   revised. Its package list, from the DailyMed `ndcs.json` service:

   ```
   15499-1234-1 ... 15499-1234-9, 15499-1234-a, 15499-1234-b
   ```

   The labeler used a 5-4-1 layout. The package segment has one digit, so it holds only 10
   packages. The labeler continued with letters after `9`. OHDSI padded the package segment to two
   characters, which gave `1549912340a`. `5812800010a` follows the same pattern after packages
   `-00` to `-09`. DailyMed has no SPL for `58128-0001` today, so that code is classified by the
   pattern, not by its own label.

3. **The regulation**, quoted above. A package code "consists of 1 or 2 digits".

4. **NLM RxNav `ndcstatus`.** All three return `UNKNOWN` with no source and no history. The
   numeric siblings return `ACTIVE` (`15499123401`, sources MTHSPL and RXNORM) or `OBSOLETE`
   (`58128000101`, sources MTHFDA, MTHSPL and RXNORM).

5. **The FDA NDC directory** (openFDA `drug/ndc`) has neither product today.

Logs (in the primary checkout's `claude_stuff/`, not committed):
`ndc-lowercase-20261031-065224.log`, `ndc-lowercase-rel-20261031-065322.log`,
`ndc-openfda-20261031-065251.log`, `ndc-spl-20261031-065351.log`,
`cfr-207-33-20261031-065424.log`, `ndc-rxnav-20261031-065439.log`.

Eliminated on the way: the DailyMed `spls.json?ndc_code=` parameter is silently ignored and
returns all 159,005 SPLs. The correct parameter is `ndc=`. The eCFR web page redirects a script to
a bot check. The eCFR versioner API works, but only with `curl --compressed`.

## RULED 2026-10-31: exclude the three, and keep them as worked examples

The three codes are excluded from `NDC.ALPHANUM`'s target in `checks/validation_targets.json`.
The exclusion's `why` cites 21 CFR 207.33(a) and this seed. They are the worked example of a
non-conforming NDC that the test does not protect. A row that rejects them has no false negative.

The exclusion changes no regexp. `NDC.ALPHANUM` still matches the three codes until the
case-exact change (vfm-8k1) narrows it. The exclusion must be in place before that change, or
`just test` reports three false negatives.

## NOT RULED: do the other 36 non-numeric codes follow?

Athena has 39 non-numeric NDC concept_codes. Every one is non-conforming under today's 207.33(a), not
only the three lower-case ones. (Before November 29, 2016, 12 of them were legal; see the UPDATE
below.) RxNav returns `UNKNOWN` for all 39 (log
`ndc-nonnumeric-20261031-065836.log`). They are:

- Mallinckrodt radiopharmaceuticals, labeler `00019`: `00019N068`, `00019N120`, `000199092B0`.
- Blood-bag anticoagulant systems, labelers `53157` and `62646`: `531570AS3BO`, `626460120PO`.
- Pacific Garden soaps and sanitizers, labeler `10685`: `106850687E5`, `106850689BM`.
- `041163NEW`, a meclizine tablet whose product segment is the word `NEW`.
- The three lower-case oxygen codes.

`NDC.ALPHANUM` exists only to admit these 39 codes. Its `notes` cite an OHDSI forum thread
(forums.ohdsi.org/t/ndc-codes-with-letters/1142). There, an OHDSI responder said: "they are not
real NDC, but they will pop up in the data and hence we need to be able to handle them." So the
row's original reason was "OHDSI publishes them, and source data may contain them". It was never
"they are valid NDCs".

The directions:

- **(a) The three only.** Exclude the three, because they are both non-conforming and lower case.
  Keep the other 36 in `NDC.ALPHANUM`'s target. The row stays as it is. The cost: the rule
  "non-conforming NDCs are bad" is applied to 3 codes of 39, and the reason is case, not
  conformance.
- **(b) Conformance is the rule.** Every non-conforming NDC is outside every row's target.
  `NDC.ALPHANUM` has no target left and is retired, with a note in README's retirement section.
  The cost: it removes a published row that consumers may read. It also contradicts OHDSI's
  advice that such codes "pop up in the data". Rule 2 of this repo (never a false negative) holds
  only if these codes are not real codes, which is exactly what 207.33(a) says.
- **(c) Keep the row as an explicit non-conforming variant.** `NDC.ALPHANUM` keeps the 36. Its
  `notes` and its target say that it admits codes that are non-conforming under 207.33(a), on
  purpose, because OHDSI publishes them. The three lower-case codes stay excluded because they
  are also case defects.

No rows in claims data were measured. Whether these 36 codes occur in any claims we hold is the
fact that would separate (b) from (c).

## UPDATE 2026-10-31: why OHDSI publishes them, and which of the 39 were ever NDCs

Ryan, verbatim: "research why OHDSI is publishing them and verify if they are NDC or not".

### Why OHDSI publishes them

OHDSI builds the NDC vocabulary with `NDC_SPL/load_stage.sql` in the OHDSI/Vocabulary-v5.0 repo.
Its sources are the FDA NDC files (`product.txt`, `package.txt`), the DailyMed SPL full releases,
RxNorm, and the RxNav NDC history API. The script copies each code as the source gives it. It pads
the labeler and product segments with zeros, and it sets the concept class from the string length:

```
LENGTH(concept_code) || '-digit NDC' AS concept_class_id,
```

No step checks that a code contains only digits. That is why `00019N068` is classed as a
"9-digit NDC". The codes stay valid (end date 2099-12-31) because their drug labels are still on
DailyMed and were never replaced. 37 of the 39 have no relationship at all in Athena. Two
Mallinckrodt codes have a `Maps to`: `00019N450` to RxNorm `1546275` and `00019N452` to RxNorm
Extension `OMOP4698583`.

The OHDSI forum answer that `NDC.ALPHANUM` cites says the same thing from the other side: "they are
not real NDC, but they will pop up in the data and hence we need to be able to handle them."

### The rule changed in 2016, so the answer depends on the date

The 2012 and 2016 editions of 21 CFR 207.35(b)(1) allowed letters, but only for drugs already in
the original National Drug Code System. FDA had expanded those labelers' 3-character labeler codes
to 4 characters with a lead zero. The text:

```
A manufacturer or distributor may either retain alphanumeric characters that are already used in
the Product Code and Package Code segments of the National Drug Code or convert these alphanumeric
characters to all numeric digits.
```

The 2016 final rule (Federal Register 2016-20471, effective November 29, 2016) replaced that text
with today's 207.33(a). Its preamble says: "This final rule refers to the NDC as a numeric code,
not an alphanumeric code. This takes into account comments that objected to the inclusion of alpha
characters in NDCs as disruptive of current systems and practices."

### The 39 codes fall into two groups

**Group 1: legacy NDCs that were once legal. 12 codes, all from Mallinckrodt (labeler `0019`).**
`0019` is a 4-digit labeler code from the original system, so the 207.35(b)(1) permission covered
it. The codes: `00019N068`, `00019N068B0`, `00019N094`, `00019N096`, `00019N120`, `00019N180`,
`00019N450`, `00019N452`, `00019N601`, `00019N602`, `000199092B0`, `000199092D0`.

- Each `N` code has a numeric twin in Athena with `9` in the same position, for the same product:
  `00019N068` and `000199068` are both Ultratag RBC. `00019N120` and `000199120` are both
  thallous chloride Tl 201.
- FindACode lists `00019-N068` (Ultratag RBC) as deleted on 2015-11-01 and `00019-N120`
  (thallous chloride) as deleted on 2014-08-15. So the FDA directory once carried them.
- The products moved to Curium (labeler `69945`) with numeric NDCs: Ultratag RBC is
  `69945-068-20`, thallous chloride is `69945-120-56`, Technescan PYP is `69945-094-20`, and
  sodium iodide I-123 is `69945-601-10` and `69945-602-20` (openFDA, 2026-10-31).
- `000199092B0` and `000199092D0` (packages `B0` and `D0` of a sestamibi kit) are classified by
  labeler only. No label or directory entry was found for them.

These were NDCs. They can appear in claims from before the products were renumbered. They do not
conform to today's 207.33(a).

**Group 2: outside the original-system permission. 27 codes.** Each labeler has a 5-digit
labeler code, which that permission did not cover. The regulation text did not allow their
letters. But the FDA accepted these codes on submitted drug labels, and no evidence shows that
they did not exist as NDCs. (Corrected 2026-10-31: this heading first said "never NDCs under any
version of the rule", which the evidence does not support.)

- 19 blood-bag codes from Haemonetics (`53157`) and Medsep (`62646`), NUTRICEL CP2D/AS-3 systems
  under application BN820915. Their labels on DailyMed (setids
  `e713f9f1-4208-4ea9-b33f-d758a06346ce`, 2013, and `6c5cf2fb-8f57-496e-b756-dfbfba07b516`, 2012)
  list `53157-120-92`, `53157-120-BO`, `53157-AS3-PO` and similar. Each letter code has a numeric
  sibling in Athena (`53157012092`). `053157AS3` and `062646AS3` are also padded in the wrong place
  (the correct form is `531570AS3`), so they are OHDSI padding defects too.
- 4 Pacific Garden soap and sanitizer codes, labeler `10685` (`106850687E5`, `106850688E5`,
  `106850689BM`, `106850689E7`). The products now carry numeric NDCs under Georgia-Pacific's
  labeler `54622` (`54622-687-37`, `54622-689-12`).
- 3 oxygen codes (`1549912340a`, `1549912340b`, `5812800010a`). See the evidence above.
- 1 placeholder, `041163NEW` (meclizine, labeler `41163`), whose product segment is the word `NEW`.

### What this changes in the open question

Before this research, the choices were "keep all 36 non-conforming codes" or "drop all 36". The
research shows a third boundary: keep the 12 legacy Mallinckrodt NDCs in `NDC.ALPHANUM`'s target,
because they were real NDCs, and exclude the 27 codes outside the original-system permission.
Under rule 2 of this repo, a code that was once a real NDC must not be a false negative in a row
that admits historical codes.

Not ruled. The question stays open in `vfm-39i`.

### Related, not acted on

The 2026 final rule (Federal Register 2026-04368, effective March 7, 2033) changes every NDC to a
uniform 12-digit numeric format (6-4-2). Commenters proposed alphanumeric labeler codes, and FDA
kept the code numeric. The NDC rows here will need a 12-digit form before 2033.

### Sources and logs

- OHDSI build: github.com/OHDSI/Vocabulary-v5.0, `NDC_SPL/load_stage.sql` and `readme.md`.
- 21 CFR 207.35, 2012 and 2016 editions (govinfo.gov). 21 CFR 207.33, current edition (eCFR API).
- Federal Register 2016-20471 and 2026-04368 (federalregister.gov API).
- DailyMed `spls.json?ndc=` and `spls/<setid>/ndcs.json`. openFDA `drug/ndc`. FindACode's
  Mallinckrodt labeler page.
- Logs in the primary checkout's `claude_stuff/` (not committed):
  `ndc-nonnumeric-rel-20261031-070423.log`, `ohdsi-ndc-build-20261031-070434.log`,
  `ndc-nonnumeric-spl-20261031-070503.log`, `ndc-nonnumeric-spl2-20261031-070514.log`,
  `ndc-openfda-labelers-20261031-070533.log`, `ndc-nonnumeric-twins-20261031-070615.log`,
  `cfr-207-35-2012-20261031-070650.log`, `fr-2016-ndc-alnum-*.log`, `fr-ndc-detail-*.log`.

## RULED 2026-10-31 (Ryan): keep all 36 in NDC.ALPHANUM

Ryan, verbatim: "for ndcalphanum, keep all 36".

All 36 non-numeric, upper-case NDC codes stay in `NDC.ALPHANUM`'s target. That includes the 12
legacy Mallinckrodt NDCs and 24 codes from labelers outside the original-system permission. The
three lower-case oxygen codes
stay excluded. `NDC.ALPHANUM` is not retired. The 207.33(a) evidence above stays as the record of
which codes are legacy NDCs and which are not, in case the question returns.

Ryan will discuss the codesistant side of case sensitivity with a codesistant agent himself
(codesistant seed `cst-gp2`).

## RULED 2026-10-31 (Ryan): letters in legacy NDCs are respected for the foreseeable future

Ryan, verbatim: "for my ruling on ndcs with alphas -- we don't _knnow_ the 27 "never were" as far
as I know because we've never seen evidence they didn't exist (that's hard evidence to find) and
apparently legacy NDC allowed alphas, so we need to respect that for the foreseeable future".

What this corrects:

- The claim "never NDCs" was an inference from the regulation text, not evidence. It is corrected
  in place above. The evidence points the other way: the FDA accepted these codes on submitted
  labels (DailyMed SPLs for the blood bags and the oxygen), and the FDA directory once listed
  Mallinckrodt's `N` codes.
- The count was also wrong. Group 2 has 27 codes, and it includes the three lower-case oxygen
  codes. The 36 codes kept in `NDC.ALPHANUM` are 12 Mallinckrodt codes and 24 others.

The rule from here on: a letter in an NDC segment is not, by itself, evidence that a code is bad.
207.33(a) does not decide whether a code belongs in `NDC.ALPHANUM`'s target. The title of this
seed and the request that opened it ("filter out bad NDCs that don't conform to CFR 207.33(a)")
describe a position that this ruling replaces.

The three oxygen codes stay excluded, but for case only (vfm-8k1). Their letters are respected. An
upper-case spelling such as `1549912340A` belongs in `NDC.ALPHANUM`'s target and must pass the
row after it becomes case-exact. The exclusion's `why` in `checks/validation_targets.json` now
says this.
