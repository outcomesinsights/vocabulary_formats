# vocabulary_formats

> Collection of PCRE regular expressions to validate medical terminology codes (ICD9CM, ICD10CM, CPT4, HCPCS, NDC).

## Status

- **Active** — a member of the `codesets` habitat; tracked with `bd` (`vocabulary_formats-`) and `seeds` (`vfm-`).
- Last meaningful work: 2026-07-25

## THE RULE THAT GOVERNS EVERY EDIT — keep the regexes PERMISSIVE

Skew toward valid: accept anything that *could* be a valid code, tolerate a few false positives,
**never reject a real code**. False negatives are unacceptable. This is not a style preference — it
is the repo's entire contract with its consumers.

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

## Open work (see `bd ready`)

- Extend the format regexes beyond claims vocabularies to WHO ICD10, SNOMED, RxNorm, ICD10PCS, ATC,
  DRG, ICD-O-3.
- Add a SECOND table: the vocab-label id-normalization **registry** — every label seen in the wild
  recorded verbatim, mapping to a known-good OHDSI `vocabulary_id` or to a **blank** meaning "not
  supported in OHDSI as of now". The blank rows double as the producers' extract-but-don't-produce gate.

## Domain Concepts

- **vocabulary_id**: OMOP vocabulary identifier (e.g., ICD9CM, NDC, CPT4)
- **DOTLESS variants**: Codes without decimal points, common in Medicare claims
- **WITHMODIFIERS variants**: Include procedure modifiers in same vocabulary
