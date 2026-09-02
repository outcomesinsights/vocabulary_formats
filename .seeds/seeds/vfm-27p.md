---
id: vfm-27p
title: "SNOMED: all 464,018 UUID-shaped codes are INVALID (not the UK drug extension) — so a numeric-only default has ZERO false negatives on valid concepts"
status: captured
type: decision
created_at: 2026-07-27T18:46:15.089261+00:00
updated_at: 2026-07-27T18:46:15.089270+00:00
tags:
  - snomed
  - uuid
  - retired
  - invalid-reason
  - claims
  - odie
  - ryan
  - 2026-07-27
converted_at: 2026-09-02T14:41:48.760748+00:00
---

DISCOVERED 2026-07-27 while reviewing Odie's SNOMED row, which added a UUID alternation and described
the UUIDs as 'retired UK Drug extension'. Both halves of that were off.

## NOT the UK drug extension
UUID-shaped SNOMED codes by concept_class:
    Physical Object      194,791       Qualifier Value    8,735
    Pharma/Biol Product  192,709       Substance          2,786
    Context-dependent     64,755       Model Comp           183
Physical Object is the LARGEST bucket; Context-dependent, Qualifier Value and Model Comp are not drugs
at all. So the UUID form is not an extension-specific encoding.

## What it actually is: THE RETIRED PORTION OF SNOMED, ENTIRELY
    UUID-shaped (464,018):  invalid_reason='U' 367,198  ·  'D' 96,820  ·  **VALID: 0**
    numeric IDs (629,129):  349,211 valid+standard, plus U/D/non-standard
Not one UUID-shaped code is a valid concept. Measured:
    ^[0-9]+$  vs ALL SNOMED concept_codes    ->  464,018 false negatives
    ^[0-9]+$  vs VALID SNOMED concept_codes  ->  **0 false negatives**

## DECIDED (Ryan, 2026-07-27)
Default `SNOMED` -> `^[0-9]+$`. Ryan: 'I'd favor a regexp for non-uk drug extension as our default
snomed format, then use the standard regexp for uuid for snomed.plusukdrugext or something.'
The instinct was right and the justification is stronger than the framing: it is not that the drug
extension is a special case, it is that **every UUID code is retired**, so a numeric-only default
rejects nothing valid.
NAMING: the variant should be named for what it IS — retired/withdrawn concepts — NOT for the UK drug
extension, which is not what distinguishes them. Something like SNOMED.WITHRETIRED.
Cost avoided: Odie's alternation made the regex accept ANY UUID as a SNOMED code, in exchange for
covering 464k concepts of which none is valid.

## Fits the claims principle
SNOMED barely appears in US claims at all — it is in this repo because litmine extracts it from
PAPERS. So the claims-default rule does not really bite here; what does is 'valid vs retired', and
numeric-only happens to be exactly the valid set. Convenient, and worth noting it is a coincidence of
SNOMED's encoding history rather than a general pattern.
