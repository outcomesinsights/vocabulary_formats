---
id: vfm-6oo
title: Extend the format regexes beyond claims vocabs to cover litmine's non-claims vocabularies (WHO ICD10, SNOMED, RxNorm, ICD10PCS, ATC, DRG, ICD-O-3)
status: captured
type: decision
created_at: 2026-07-25T17:46:45.079886+00:00
updated_at: 2026-07-25T18:31:07.399605+00:00
tags:
  - format-regex
  - coverage
  - non-claims
  - litmine
  - snomed
  - rxnorm
  - icd10pcs
  - atc
  - permissive
  - 2026-07-25
converted_at: 2026-09-02T14:41:48.760748+00:00
---

Decided by Ryan in litmine's lit-et6.1 (2026-07-23). Filed HERE 2026-07-25 during the codesets
seed-reconciliation pass — the work was decided but lived only in litmine's seed tree.

## The gap

The current table is 13 rows covering CLAIMS vocabularies only: ICD9CM (+.DOTLESS), ICD10CM
(+.DOTLESS), HCPCS (± modifiers), CPT4 (± modifiers), NDC (+.ALPHANUM). litmine extracts code sets in
whatever vocabulary a paper used, so it needs rows for **WHO ICD10, SNOMED, RxNorm, ICD10PCS, ATC,
DRG, ICD-O-3** and whatever else the corpus turns up.

Ryan: 'tens of rows at most', cheap — and fine to grow an asset several repos depend on.

## Keep them PERMISSIVE — this is the load-bearing constraint

Per this repo's own README the regexes are deliberately 'skewed toward valid': accept anything that
COULD be a valid code, tolerate false positives, **NEVER reject a real code**. False negatives are
unacceptable (hence the loose ICD10CM \\w{3}.\\w{0,4} so future U-codes still pass).

Strict/existence validation is explicitly OUT of scope — it belongs to the concept DB, which is where
the set of all known-good codes actually lives. A regex validates FORMAT ('does this look like a code
of vocab X?'); it cannot validate EXISTENCE. You can't pattern your way to 'E11.9 is real but E11.99
is not', and a tight regex goes stale as codes change yearly.

**The two layers together are more useful than either alone** — they classify failures on different
axes: passes-format-but-misses-DB = 'well-formed but not a real code' (typo / retired / non-US
variant); fails-format = malformed. That is exactly litmine's validate.py taxonomy
(valid_fy2025 / valid_earlier_fy / format_valid_not_found / invalid), already in production.

## Two field-tested constraints to inherit rather than rediscover

From Mark's litmine handoff, both hit by his recall scanner:

1. **The dotted-code trap.** An undotted-only regex truncates `M05.79` to the category `M05`,
   collapsing a 338-code list into ~12 hits and scoring a code-rich paper as empty. Any scan must
   handle BOTH forms — direct field confirmation of why the `.DOTLESS` variants exist, and a warning
   that a consumer reading only one variant silently UNDER-COUNTS rather than erroring.
2. **A >=4-character floor** stops bare 3-char categories in ordinary disease prose (`F10`, `I21`)
   from matching. This is a SCANNING threshold, not a validation one — a real 3-char code like
   `I10` is legitimately valid — so **the floor belongs in the CALLER, not in the format regex.**
   Worth stating explicitly as the regexes gain new consumers: it is exactly the kind of rule that
   gets pushed down into the shared layer by mistake.

## Mechanics

Edit the TSV; `make all` regenerates the parquet. Keyed by OHDSI `vocabulary_id`, which is also the
join key to the id-normalization registry (vfm-31w).

## Authoring

Hand the new regexes to a domain agent — Odie (OHDSI/OMOP) or Vincent (vocab) or the vocabulary
habitat — to author and validate.

## NB — repo is dirty

As of 2026-07-25 this repo has uncommitted changes to README.md and vocabulary_formats.tsv plus
untracked CLAUDE.md / Makefile / vocabulary_formats.parquet, all with mtimes from 2024-2026-02
(stale, not live work). Reconcile those before adding rows.

BEAD FILED 2026-07-25: **vocabulary_formats-3h8**.

## THE WORKING TREE ALREADY VIOLATES THIS (found 2026-07-25) — see bead vocabulary_formats-1n1

The 'NB — repo is dirty' note above understated it. The stale uncommitted changes are not inert:
they TIGHTEN three regexes, and the ICD10CM one is a correctness regression.

```
    committed:   ^\w{3}.?\w{0,4}$   (dot optional)
    uncommitted: ^\w{3}\.\w{0,4}$    (dot required)
```

Tested: I10, E11, F10, N18 all go PASS -> FAIL. Three-character ICD-10-CM codes are real, and in the
OHDSI concept table they live in the DOTTED vocabulary with no dot (verified against the June-2026
Athena build). So the 'permissive, never reject a real code' rule this seed records as a hard
constraint is already broken in the working tree — by an edit nobody documented, in a repo that had
no seeds or beads to record intent, which is exactly the gap this seed and vfm-31w were filed to close.
Resolve vocabulary_formats-1n1 BEFORE adding non-claims rows on top of an unreviewed base.
