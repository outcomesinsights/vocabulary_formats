---
id: vfm-6x1
title: 'A validator and a detector want opposite things: 9 rows collapse to a tiny mandatory core and flood free text — census over 2M chars of real articles'
status: captured
type: decision
created_at: 2026-08-26T20:33:39.191631+00:00
updated_at: 2026-08-27T20:17:15.325381+00:00
tags:
  - formats
  - detector
  - validator
  - census
  - measured
  - ryan
  - 2026-08-26
converted_at: 2026-09-02T14:41:48.760748+00:00
---

RYAN, 2026-08-26: "let's capture each as a seed and see how we can improve each —
icd10pcs seems ready to accept as a decision and promote to a bead, but let's walk
through the other regexps and give each a similar treatment."

Three rows had surfaced by accident (`ICD10PCS`, `ATC`, WHO `ICD10`) while
`code_collector-azyr.3` built the two-tier candidate net. Measuring ALL 35 rows shows
the problem is wider than those three, narrower in one case than reported, and has a
single cause.

## The census

Every row `\b`-bound and run over **2,020,962 characters of real article body text**
(25 papers from the pubmed ground-truth queue, XML structural units only):

```
row                          matches   per 10k chars
ICD10PCS                     172,323      852.7
CPT4.WITHMODIFIERS            68,835      340.6
CPT4_HCPCS.WITHMODIFIERS      68,835      340.6
HCPCS.WITHMODIFIERS           68,806      340.5
HCPCS_MODIFIER                68,806      340.5
CPT4_MODIFIER                 68,806      340.5
CPT4_HCPCS_MODIFIER           68,806      340.5
DRG.UNPADDED                  66,718      330.1
RxNorm                        40,660      201.2
ICD9Proc.DOTLESS              40,639      201.1
ICD9Proc                      23,979      118.7
ICD9CM.DOTLESS                15,864       78.5
ICDO3                         12,388       61.3
ICD9CM / DRG                  12,319       61.0
ATC                            7,474       37.0
ICD03_Morphology.NOBEHAVIOR    3,529       17.5
---- usable as detectors below this line ----
ICD10.DOTLESS                    362        1.8
ICD10                            273        1.4
ICD10CM.DOTLESS                  170        0.8
ICD10CM                           77        0.4
ICD03_Topography(.DOTLESS)     74 / 120    0.4 / 0.6
EDI                               40        0.2
CPT4 / CPT4_HCPCS                 29        0.1
SNOMED(.WITHRETIRED)               6        0.0
HCPCS, NDC x4, RxNorm Extension,
ICD03_Morphology                   0        0.0
```

## ⚠️ ONE REPORTED FLOOD WAS WRONG

`code_collector-azyr.3` named WHO **`ICD10`** as flooding on its bare roman-numeral
Chapter branch. Measured, it is **1.4 per 10k — one of the cleanest rows in the
table.** The chapter alternative is real (`I`, `V`, `X` …) but standalone roman
numerals are rare in medical prose. Do not narrow that row on the strength of the
earlier report; it was inferred from reading the pattern, not measured.

`ATC` at 37.0 is a genuine flood but a mid-table one, not comparable to ICD10PCS.

## THE SINGLE CAUSE

Every flooding row has **optional parts that collapse to a tiny mandatory core**:

```
CPT4.WITHMODIFIERS   (\w\d{3}\w|\w{2})       the |\w{2} alternative is ANY two word chars
ATC                  [ABCDGHJ…](\d{2}…)?     trailing ? — a SINGLE LETTER matches
ICD10PCS             [0-9A-Za-z]{1,7}        {1,…} admits the vocabulary's hierarchy parents
DRG.UNPADDED         \d{1,3}                 any 1-3 digit number
RxNorm               \d{2,8}                 any 2-8 digit number
ICD9Proc             \d{2}(\.\d{1,2})?       any 2-digit number
ICD9Proc.DOTLESS     \d{2,4}
ICD9CM.DOTLESS       (V\d{2,4}|\d{3,5}|E\d{3,4})
```

## THE RULE THIS ESTABLISHES — and it is not "these rows are wrong"

**A validator and a detector want opposite things, and this table serves both.**

Asked with `fullmatch` — "is this string a code in vocabulary X" — `{1,7}` is CORRECT
for ICD10PCS, because a 3-character hierarchy parent genuinely IS a concept_code, and
`\d{1,3}` is correct for an unpadded DRG. Narrowing the default would break the job
the row exists to do, and `vfm-k2n` already says the default targets its declared
purpose while variants carry the rest.

Scanning FREE TEXT is the opposite question — "which spans here might be codes" — and
a pattern whose mandatory core is one character answers "all of them".

So the fix is never to narrow a default. It is to add a **detector-safe sibling**
where one is possible, and to declare a row NOT DETECTABLE where it is not. That is
the shape `NDC.PUBLISHED` took on 2026-08-26.

⚠️ Some rows have no detector-safe form and that is a legitimate answer. A bare
2-digit ICD-9 procedure code cannot be told from a number by shape at all. Saying so
in the row is worth more than a pattern that pretends otherwise — `code_collector`'s
two-tier design (`clc-0bb`) already handles this by scanning bare-numeric shapes ONLY
when the document names the vocabulary, which is the right home for that class.

## PER-ROW TREATMENT

**Settled — promote to a bead.** ICD10PCS. `[0-9BCDFGHX][0-9A-HJ-NP-Z]{6}`: zero
false negatives against all 82,327 billable codes, 79% fewer matches than
uppercase-exactly-7. Position 1 uses only 17 characters and is the whole win;
position 5's narrower alphabet was measured and adds nothing. Cannot exclude
all-digit strings — 504 billable codes are pure digits. See `vocabulary_formats-wsa`.

**Next, in flood order.** Each needs the same treatment: derive from the concept_codes
rather than the spec, measure false negatives against the whole vocabulary, measure
matches over this same corpus, and accept "not detectable" where that is the answer.

1. the seven CPT4/HCPCS MODIFIER rows — all ~340/10k and all sharing `|\w{2}`.
   Almost certainly ONE fix applied seven times; check whether the modifier belongs
   as a standalone alternative at all, or only as a suffix.
2. DRG.UNPADDED, RxNorm, ICD9Proc(.DOTLESS), ICD9CM.DOTLESS — the bare-numeric
   class. Likely "not detectable, use the name-directed tier".
3. ICDO3 and ICD03_Morphology.NOBEHAVIOR — mid-table, unexamined.
4. ATC — 37/10k, caused by the trailing `?`.

## METHOD NOTE

Two of the three rows reported by inference were wrong or overstated once measured.
Read the pattern to form a hypothesis; run it over real text before believing it.
The corpus is `sources/pubmed/cache/linked/…` in `code_collector`, read-only, via
`jats.select_body` + `candidates.unit_reading`.

______________________________________________________________________

## PER-ROW RESULTS, measured 2026-08-26 against ALL concept_codes in the OHDSI vocabs

Ryan's constraint: "reduce false positives, never allow a single false negative,
compare against all known codes in the ohdsi vocabs."

That constraint splits the table cleanly, and the split is the finding.

### TWO TRUE ZERO-FN WINS

```
ICD10PCS       852.7 -> ~0.3 /10k   0 FN   [0-9BCDFGHX][0-9A-HJ-NP-Z]{6}
DRG.UNPADDED   330.1 ->  61.0 /10k  0 FN   \d{1,3} -> \d{3}
```

`DRG.UNPADDED` is free: all 871 DRG concept_codes are EXACTLY 3 digits, so `\d{1,3}`
was pointlessly wide — and the row's own name says it was meant to be padded. 5x
fewer matches for nothing.

### CPT4 / HCPCS — SPLIT THE CODE FROM THE MODIFIER, never one pattern

RYAN, 2026-08-26: "modifiers often are reported entirely separately from cpt codes
themselves (at least in claims data they are separate columns). Perhaps we just
shouldn't mix CPT and modifiers together in any regexp. I've never seen a modifier
tacked on as a suffix to a CPT code, but I could be wrong and we'll look out for
that in the literature."

He is right, and this supersedes a suffix form I proposed an hour earlier
(`code(?:[- ]?modifier)?`) which I had INVENTED from how modifiers appear in some
billing contexts. Measured: **0 occurrences of a code followed by a 2-char token
across 25 papers**, and the suffix version scored 0.15/10k against the code-only
version's 0.14 — it bought nothing even if the form existed.

```
CODE detector   (?:\d{5}|\d{4}[A-Za-z]|[A-Za-z]\d{4})
                0 FN over all 25,850 real 5-char CPT4+HCPCS codes
                340.5 -> 0.14 /10k   (a 2,400x reduction)

MODIFIERS       NOT DETECTABLE in free text. 686 distinct two-character tokens,
                including MG, AT, AA, AP, AS, US, CT, PT. Enumerating all 686
                as literals still measures 64.2/10k, because they ARE ordinary
                words. No pattern fixes this.
```

**The seven flooding rows all exist because someone combined the two concerns.**
`(\w\d{3}\w|\w{2})` reads "a code OR a modifier", and the `|\w{2}` alternative is
the entire flood — it matches any two word characters. Split them and both problems
disappear: the code half becomes near-perfect, the modifier half becomes an honest
"not detectable".

⚠️ `CPT4.WITHMODIFIERS` ALSO HAS 3,853 FALSE NEGATIVES TODAY against its own
vocabulary — it misses every 7-digit CPT code. That is a live validator bug,
independent of detection. Per Ryan the 7-digit chapter codes are out of scope for
US, but the row still claims to validate them.

### NOT DETECTABLE WITHOUT FALSE NEGATIVES — and that is the answer, not a failure

```
RxNorm            \d{6,8} -> 0.0/10k but 4,584 FN of 315,157 (1.5%)
ICD9Proc(.DOTLESS) no narrowing beats 100+ FN
ICD9CM.DOTLESS    V/E branch alone -> 0.0/10k, but 14,746 FN (the numeric branch)
ATC               5+ chars -> 0.0/10k, but 108 FN — `A`, `B`, `C` are REAL codes
CPT4/HCPCS mods   686 two-char tokens, indistinguishable by shape
```

### THE STRUCTURAL FINDING

**Every vocabulary with a hierarchy has short codes at the top of it** — `A` in ATC,
`79` in CPT, `250` in ICD-9, `0` in ICD10PCS — and those are indistinguishable from
ordinary text BY SHAPE ALONE. Under a no-false-negative rule they cannot be dropped,
so they cannot be detected either.

**Which means `clc-0bb`'s name-directed tier is not an optimisation — for these
vocabularies it is the ONLY mechanism that can ever find them.** "Scan bare-numeric
shapes only when the document names the vocabulary" is not a way to reduce noise; it
is the sole route by which a bare `250` can be treated as a code at all. That design
was carrying more weight than it appeared to.

### A QUESTION THE LABELS WILL SETTLE

Ryan: "we'll look out for that in the literature." Whether any paper prints a
suffixed modifier is empirically answerable by the adjudication screen itself — if
one appears, it will show up as a candidate a reviewer marks as used-as-a-code.
Nothing needs deciding in advance.

______________________________________________________________________

## DRG: RULED 2026-08-26, and the ruling exposes a MISSING AXIS

RYAN: "claims data sometimes reports numbers unpadded, so we need \\d{1,3} but for
papers I'd expect 0 padded every time."

So `DRG.UNPADDED`'s `\d{1,3}` is **CORRECT and stays**. The earlier reading —
"pointlessly wide, every DRG concept_code is exactly 3 digits, narrow it for free" —
was measuring the wrong thing. It compared the pattern against the OHDSI CONCEPT
TABLE, where codes are stored padded. It is not the concept table this row has to
survive; it is CLAIMS DATA, which sometimes prints `12` for `012`.

**Narrowing it would have silently dropped real DRG codes from claims**, and the
measurement that "proved" it safe could not have detected that, because the evidence
was never in the vocabulary.

⚠️ METHOD FAILURE WORTH KEEPING. Measuring against every concept_code is necessary
and NOT sufficient. A row can be correct for data that does not appear in the
vocabulary at all — the vocabulary holds canonical forms, and the wild holds
presentations of them. The same trap already bit NDC (`NDC.PUBLISHED` exists because
papers print hyphenated forms no concept_code contains) and would have bitten DRG.

## THE AXIS THIS REVEALS — and Ryan named the gap

RYAN: "should we start keeping a 'notes' column for why a given row exists and where
it might best be applied? I've given a lot of knowledge and experience to you and
that's not getting captured and presented to anyone using these formats."

A `notes` column already exists and IS being written — every one of the 37 rows has
one, median 583 characters, and 35 mention claims, papers, detection or validation.
So the knowledge is captured. What is missing is that it is captured as PROSE:

- a human choosing a row must read ~21,000 characters to compare 37 of them;
- **a program cannot ask.** `code_collector-azyr.3` had to MEASURE which rows were
  detector-safe, binding each over 2,020,962 characters of article text, because
  the table could not be queried for it. That cost is already paid once and will
  be paid again by the next consumer.

The rows already vary along at least two axes nobody has written down:

```
CONTEXT   what data is this row meant to survive?
          claims (DRG.UNPADDED, NDC) · literature (NDC.PUBLISHED) · the concept
          table itself (ICD10PCS's {1,7}, which admits hierarchy parents)

USE       fullmatch VALIDATOR on a string you already have, or \b-bound DETECTOR
          scanned over prose? They want opposite things, and this table serves
          both from one column.
```

`vfm-k2n` already recorded the damage when this stays implicit: NDC's default
quietly widened toward "everything real" and came to reject 338,328 real codes,
because two consumers were pulling the row in opposite directions with nothing
naming which one it served.

Reshaped into `vocabulary_formats-5i7`.

## ICD10CM.DOTLESS joins the census — measured 2026-08-27 from a consumer, not a scan

Found when Ryan asked why T2DM and QALY were being offered as code candidates on a sleep-apnea
paper by the literature-mining consumer.

```
ICD10CM.DOTLESS   (?:QA|[A-Za-z][0-9])[0-9A-Za-z]\w{0,4}
```

Two holes:

- the QA branch requires NO DIGIT AT ALL, so QALY matches (QA + L + Y)
- [A-Za-z][0-9] then \\w{0,4} takes T2DM (T, 2, then DM as trailing word characters)

It ranks above the other census rows for one reason: the consumer scans this shape on EVERY
document regardless of which vocabularies the document names, where the other flooding rows are
only scanned when their vocabulary is named. A permissive row costs most where it is unconditional.

⚠️ THE CLAIM THAT JUSTIFIES IT DOWNSTREAM IS FALSE, and is worth knowing here because it will be
repeated: the consumer records "a letter followed by a digit. No English word and no quantity has
that shape, so the dotless form is as safe as the dotted one." One article disproves it four
times — T2DM, T90, H2O, S13b.

## MEASURED SCALE — small, and I initially overstated it

Over 30 articles, 1,640 candidate tokens:

```
starting with a letter:  120 occurrences, 114 distinct
matching the QA branch:    1 occurrence,    1 distinct  (QALY)
```

109 of the 114 are REAL codes: N05A/N05B/N05C/N06A/N06B/N06C/N07B (ATC), U07.1, I60, I69, C50,
C76, C80, C77.3, B18.0, B18.1, B20, B97.35, R75, Z21, Z22.51, plus the wildcard notations F11.xxx
and M80.x. The junk is five distinct strings: T2DM (x3), T90, H2O, S13b, QALY.

~96% precise in practice. I called this "catastrophically broad" on reading the pattern and was
wrong — reading a regex is not measuring it, which is the same lesson this census was built on.
A detector-safe sibling is still worth having; it is a small win, not an emergency.

## ICD10PCS default: confirms the census thesis, latent rather than active

[0-9A-HJ-NP-Za-hj-np-z]{1,7} fullmatches nearly any short word avoiding I and O — QALY, T2DM,
T90, S13b, E930, C50 all match. It never fired in the measurement because the consumer only
scans it when an article names ICD-10-PCS and none did. ICD10PCS.BILLABLE (added 2026-08-26) is
already the detector-safe sibling; the permissive default is CORRECT for the validator consumer
and should stay. That pairing is the pattern this census recommends, now with a second worked
example.

## A consumer-side ordering bug, reported here only because it looks like a formats problem

E930.4 is located as E930 by the literature consumer: it tries ICD10CM before ICD9CM, so the
letter-plus-digits shape claims the ICD-9 E-code stem before ICD9CM dotted row is reached. E930
is not a valid ICD-10-CM code. NOT a vocabulary_formats defect — the rows are fine; the consumer
races them in the wrong order. Recorded so a reader who meets it here does not edit a row to fix it.
