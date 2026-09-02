---
id: vfm-ges
title: "A vocabulary format is ONE regexp: complete over every published code first, then as narrow as a plain regexp reasonably gets"
status: resolved
type: decision
created_at: 2026-08-12T19:56:52.530348+00:00
updated_at: 2026-08-12T19:57:01.671164+00:00
resolved_at: 2026-08-12T19:57:01.671161+00:00
resolution: "Recorded as a trellis in `CLAUDE.md` on 2026-08-12: A vocabulary's code format is ONE regexp that must match every code the vocabulary publishes, then be narrowed to admit as few non-codes as a plain regexp reasonably can — guarded by a test over the published set, because a miss is silent: the reference does not go wrong, it vanishes."
tags:
  - vocabulary-format
  - regexp
  - false-negative
  - false-positive
  - detection-vs-validation
  - qa0
  - trellis-candidate
  - ryan
  - 2026-08-12
  - trellis
converted_at: 2026-09-02T14:41:48.760748+00:00
---

Ryan, 2026-08-12:

> "must be respresented as a regexp and never allow false negatives but avoid as many false
> positives as is reasonable"
> "I do want vocabulary formats to be sensitive, but still to maintain a defensible amount of
> specificty as well. If we can avoid false positives with a reasonable regex, I say we do it"

## WHAT THIS CHANGES ABOUT RULE 2

CLAUDE.md rule 2 already says never reject a real code, and says to 'tolerate a few false
positives'. This does NOT overturn that ordering -- completeness still comes first -- it puts a
DUTY on the second half. 'Tolerate' reads as indifference; the rule is now: tolerate a false
positive only as far as staying complete requires, and if a plain regexp can exclude it, exclude it.

README.md line 28 currently states the tie-break the other way -- 'If a choice has to be made
between a more restrictive or a more permissive regexp, we'll favor the more permissive.' That line
needs to be reconciled with this, because at the margin the two pull in opposite directions. The
resolution is that permissiveness is the floor (never a false negative), not the goal.

## THE EVIDENCE THAT PROMPTED IT -- ICD-10-CM's QA0, 2026-08-12

FY2026 introduced QA0 ('Neurodevelopmental disorders related to specific genetic pathogenic
variants', 20 codes) -- the FIRST ICD-10-CM category with a LETTER in position 2. Measured across
both editions on disk: FY2025 had 1,917 categories and ZERO such; FY2026 has 1,918 and exactly one.

THIS REPO WAS NOT WRONG. Its ICD10CM row is ^\\w{3}(\\.\\w{1,4})?$ and matches QA0 already --
verified. That is the permissive contract working exactly as intended: a new code shape arrived and
the format did not have to change.

The bug was in a CONSUMER that had respelled the shape more strictly (icd10cm's note extractor,
[A-Z][0-9][0-9A-Z]), where chapter 17's own title and code_range scanned to NOTHING for a whole
edition. Which is the argument for this repo being the source of truth: a format respelled in a
consumer is a format that silently rots.

## THE ASYMMETRY THAT MAKES COMPLETENESS FIRST

  FALSE NEGATIVE  silent. The code is not judged invalid -- it is NOT SEEN. Nothing errors, nothing
                  counts it, and 'no matches here' is indistinguishable from 'nothing to match'.
  FALSE POSITIVE  loud. It fails downstream against a real concept table and lands somewhere
                  countable.

## BUT NARROWNESS IS NOT OPTIONAL -- measured on the same case

Three candidates over the FY2026 note corpus:

  [A-Z][0-9A-Z][0-9A-Z]              +59 non-codes for +3 real gains: NOS, NEC, ICD, CDC, BMI, HPV,
                                     CKD, TIA, SLE, and the words 'and', 'are', 'for', 'see', 'the'.
  [A-Z](?:[0-9][0-9A-Z]|[A-Z][0-9])  1 false positive -- GH1, a GENE SYMBOL. Letter-letter-digit IS
                                     that shape, and CMS is adding genetic content every edition.
  (?:[A-Z][0-9]|QA)[0-9A-Z]          CHOSEN by the consumer: +3 real, 0 false, 0 lost.

## DETECTION IS NOT VALIDATION -- the boundary this repo must not be asked to cross

A consumer asked whether it should just use this repo's regexes for finding codes in prose. It
cannot, and the README already says why in other words ('to see if a code COULD be possibly valid').

  VALIDATION (this repo)  ANCHORED, permissive. 'Could this STRING be a code?'
  DETECTION (consumer)    UNANCHORED, must be strict. 'WHERE in this sentence is a code?'

Unanchored, ^\\w{3}$ shreds ordinary prose -- over one real note it yields 'Cod', 'fir', 'any',
'NOS', 'and', 'see', 'the', 'ICD'. So a detector is legitimately STRICTER than the format. The
relationship that must hold is not equality but CONTAINMENT: everything a detector finds should
validate here, and every real published code must be detectable. That is checkable, and nobody
checks it today.

## WHAT THIS REPO STILL LACKS

Rows record their validation in PROSE ('Validated 2026-07-27 vs 100,035 concept_codes: 0 FN') and
nothing re-runs it. The guard is the durable half of any format rule -- an enumeration is only as
current as the line holding it -- so the trellis's 'guarded by a test' half is aspirational here
until that harness exists.
