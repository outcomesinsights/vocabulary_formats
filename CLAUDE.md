# vocabulary_formats

> Two data tables: PCRE regexes that say whether a code *looks* valid for a vocabulary
> (`vocabulary_formats.tsv`, 34 rows), and a registry mapping vocabulary labels seen in the wild to
> OHDSI `vocabulary_id`s (`vocabulary_labels.tsv`, 22 rows).

## Status

- **Active** — a member of the `codesets` habitat; tracked with `bd` (`vocabulary_formats-`) and `seeds` (`vfm-`).
- Last meaningful work: 2026-07-27

## THE TWO RULES THAT GOVERN EVERY EDIT

### 1. The DEFAULT row targets CLAIMS-OBSERVABLE codes; variants carry the rest

For each vocabulary, the **default** row targets what you would expect to see in **claims data —
mostly billable**. Anything broader (the full vocabulary, retired concepts, alternate encodings) goes
in a **named variant**: `.DOTLESS`, `.COMPLETE`, `.ALPHANUM`, `.WITHMODIFIERS`, `.WITHRETIRED`,
`.UNPADDED`, `.NOBEHAVIOR`.

This is not new — the `.DOTLESS` rows exist because Medicare claims often drop the dot, a
claims-shaped concern from the repo's first commit. It had simply never been written down, so the
default drifted.

**The repo has TWO consumers pulling opposite ways, which is why the split is load-bearing:**

1. **Claims canonicalization** (original) — billable codes, canonicalized before an exact join.
2. **Literature validation** (via `litmine`) — *any* real code a paper printed, including
   vocabularies that never appear on a US claim. SNOMED and WHO ICD-10 are here for this reason.

Variants serve both without either winning. The failure mode is the **default quietly widening to
mean "everything real"** — which is how `NDC` came to reject 26% of its own vocabulary (338,328 real
9-digit codes) while nobody noticed the purpose had blurred. Decided in seed `vfm-k2n`, 2026-07-27.

### 2. Keep the regexes PERMISSIVE

Skew toward valid: accept anything that *could* be a valid code, tolerate a few false positives,
**never reject a real code**. False negatives are unacceptable. This is not a style preference — it
is the repo's entire contract with its consumers.

**Rule 1 SCOPES rule 2, it does not overturn it.** A false negative is judged against **the row's own
declared target**: a 9-digit NDC failing the claims-default `NDC` row is *correct*; the same code
failing `NDC.COMPLETE` is a *bug*. Within a row's stated target false negatives remain unacceptable —
both 2026-07-27 regressions (ICD10CM rejecting 1,953 three-character codes; NDC rejecting 338,328)
were bugs precisely because the rejected codes sat squarely inside their own row's target.

A regex validates FORMAT ("does this look like a code of vocabulary X?"). It cannot validate
EXISTENCE ("is this a real, assigned code") — that is set membership, answered only by a lookup
against the concept DB. You cannot pattern your way to "E11.9 is real but E11.99 is not", and a
tight regex goes stale as codes are allocated each year.

The two layers together are more useful than either alone, because they classify failures on
different axes: passes-format-but-misses-DB = well-formed but not real (typo / retired / non-US
variant); fails-format = malformed.

**Precedent, 2026-07-25:** an edit tightened `ICD10CM` to require the dot (`^\w{3}\.\w{0,4}$`),
which rejected 1,953 real codes — every 3-character category, including I10, E11, F10, N18. A
parallel edit tightened `HCPCS` to `[A-V]`, which rejects the real code X1002. Both were caught only
by testing against the full Athena concept table. **Validate any regex change against real
concept_codes before committing** (see Commands).

Related: usage-specific strictness belongs in the CALLER, never here. A >=4-character floor for
*scanning* free text is correct in a scanner (bare 3-char categories appear in ordinary disease
prose) but would be a forbidden false negative here, since I10 is a legitimate code.

## Tech Stack

- Language: Data files only (TSV/Parquet)
- Framework: None
- Key dependencies: duckdb (for TSV to Parquet conversion via Makefile)

## Purpose

Provides regular expressions that verify if medical terminology codes "look" valid without requiring database lookups. Favors permissive matching to avoid false negatives on new/valid codes. Useful for validating codes from claims data, vocabulary files, or user input.

## Key Entry Points

- `vocabulary_formats.tsv` - Primary data file with regexps (human-editable)
- `vocabulary_formats.parquet` - Generated Parquet format for programmatic use

## Commands

```bash
# Generate parquet file from TSV (always run after editing the TSV)
make all
```

Validate a regex change against the real vocabulary before committing — the June-2026 Athena build
is on disk at `~/projects/outins/vocabulation/synpuf_test_data.duckdb`, schema `ohdsi_vocabs`
(**not** `main`). Expect zero false negatives:

```python
# uv run --with duckdb python
import duckdb, re
con = duckdb.connect('/home/ryan/projects/outins/vocabulation/synpuf_test_data.duckdb', read_only=True)
codes = [r[0] for r in con.execute(
    "SELECT concept_code FROM ohdsi_vocabs.concept WHERE vocabulary_id='ICD10CM'").fetchall()]
rx = re.compile(r'^\w{3}(\.\w{1,4})?$')
print(len([c for c in codes if not rx.match(c)]), "false negatives of", len(codes))
```

Gotcha: ICD vocabularies are NON-standard in OMOP, so `standard_concept` is NULL — never filter
`standard_concept='S'` for them or you get zero rows.

## Relationships

- **Depends on**: None (data only — deliberately no Python here, so it stays polyglot)
- **Feeds into**: `codesistant` (the shared Python producer lib that reads both tables),
  `code_collector` and `litmine` (producers), `code_set_catalog` (whose `docs/ingest-formats.md`
  cites it). Because several repos depend on it, growing it is cheap and welcome — but a regression
  here propagates to all of them.
- **First live consumer of BOTH tables** (2026-07-27): `litmine/validate.py` reads
  `vocabulary_formats.tsv` for the regexes *and* `vocabulary_labels.tsv` to resolve the free-text
  vocabulary label a paper printed, then existence-checks against the OHDSI concept table. It found
  the registry's coverage complete for the 20-paper pilot — all 22 labels resolved, no unmapped rows.
  Its `VOCABULARY_FORMATS_DIR` env var is how a consumer should locate this repo: by configuration,
  never by an assumed sibling path.

## Open work (see `bd ready`)

Both of the previously-listed items **shipped 2026-07-25** (`vocabulary_formats-3h8` extended the
regexes to 34 rows covering the non-claims vocabularies; `vocabulary_formats-e5s` added
`vocabulary_labels.tsv`). What is open:

- Make each row's **target** legible without reading the README. Today "is this row for claims or for
  the full vocabulary?" is inferable only from the variant suffix and the `notes` prose. A `target`
  column, or a documented naming convention, would make rule 1 checkable rather than remembered.
- Rows for labels `litmine` has not met yet. The registry is a *registry*: an unseen label gets
  appended verbatim, then mapped or left blank. `validate.py` prints unmapped labels for exactly this
  purpose — feed its output back here.

## Domain Concepts

- **vocabulary_id**: OMOP vocabulary identifier (e.g., ICD9CM, NDC, CPT4)
- **DOTLESS variants**: Codes without decimal points, common in Medicare claims
- **WITHMODIFIERS variants**: Include procedure modifiers in same vocabulary
