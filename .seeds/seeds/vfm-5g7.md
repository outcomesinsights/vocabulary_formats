---
id: vfm-5g7
title: 'Non-conforming NDCs (21 CFR 207.33(a): an NDC is numeric): the three lower-case oxygen codes are excluded as worked examples; whether the other 36 follow is not ruled'
status: captured
type: decision
created_at: 2026-10-31T14:00:02.452446+00:00
updated_at: 2026-10-31T14:00:11.483951+00:00
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

Athena has 39 non-numeric NDC concept_codes. Every one is non-conforming under 207.33(a), not
only the three lower-case ones. RxNav returns `UNKNOWN` for all 39 (log
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
