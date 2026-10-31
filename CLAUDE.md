# vocabulary_formats

> Three data tables: PCRE regexes that say whether a code *looks* valid for a vocabulary
> (`vocabulary_formats.tsv`, 38 rows), a registry mapping vocabulary labels seen in the wild to
> OHDSI `vocabulary_id`s (`vocabulary_labels.tsv`, 79 rows), and which published vocabularies each
> hybrid we materialize is built from (`vocabulary_composition.tsv`, 2 rows).

## Status

- **Active** — a member of the `codesets` habitat; tracked with `bd` (`vocabulary_formats-`) and `seeds` (`vfm-`).
- Last meaningful work: 2026-08-13

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

### 2. COMPLETE first, then as NARROW as a plain regexp reasonably gets

Skew toward valid: accept anything that *could* be a valid code, **never reject a real code**. False
negatives are unacceptable — that is the repo's entire contract with its consumers, not a style
preference.

**But permissiveness is the FLOOR, not the goal.** The tie-break is an ORDERING, applied in order:

- **COMPLETENESS** — never a false negative within the row's declared target. Absolute.
- **NARROWNESS** — between two regexps that are both complete, take the narrower. Tolerate a false
  positive only as far as staying complete requires; if a plain regexp excludes it for free, exclude
  it, judged against ordinary prose and not only against sibling vocabularies.
- **PERMISSIVENESS BREAKS TIES** — when narrowing would risk a real code, present or future, stay
  wide.

`ICD10CM` shows both halves. *Permissiveness:* position 3 stayed `\w` for months, which is why
FY2026's `QA0` — the first category ever with a letter in position 2 — needed no edit here, while a
consumer that had respelled the shape more strictly went blind to a whole chapter. ⚠️ **That example
is historical as of 2026-08-27**: position 3 is now `[0-9ABab]` and the `QA` branch requires a
following digit, because the wildcard was admitting `T2DM`, `QALY`, `H2O` and `T2D` into a human
reviewer's candidate list. Measured at **0 new false negatives** over all 100,035 codes — the `QA0`
case is now enumerated explicitly rather than covered by a wildcard, which is narrowness winning on
its own terms rather than permissiveness being abandoned. See `CHANGELOG.md`. *Narrowness:* that
same row was still narrowed twice, for free — position 1 to a letter (the old shape accepted 16,100
of 17,564 `ICD9CM` codes; `.DOTLESS` accepted 17,562, nearly the whole vocabulary) and position 2 to
(digit | `QA`), dropping 426 ordinary word-tokens (`ABC`, `ALL`, `Age`). Both cost **zero in-target
false negatives** over 100,035 published codes. "Favor the more permissive" would have argued against
both.

**The 2026-08-13 sweep (`vocabulary_formats-wir`) applied that ordering to every remaining row**,
narrowing ten — each measured on its own before/after pair, all still at 0 in-target false negatives
over 8,662,422 codes. `EDI` went from admitting 7,637 ordinary words to **0** (every one of its
442,551 codes is 5, 8 or 9 characters with digits in positions 4-5), `ICD10.DOTLESS` 5,565 → 15,
`NDC.ALPHANUM` 2,899 → 0, `CPT4_HCPCS` 1,158 → 0, `ICD10PCS` 5,708 → 2,323 (the spec bars `I` and
`O`). Just as load-bearing is what was **not** narrowed: `\w{2}` really is the shape of a modifier
and `\d{3}` really is the shape of a DRG, so those rows now carry a note saying they cannot carry
their own weight in a text scan — a false negative would have been the worse trade. `just prose` is
the instrument; per-row numbers are in the `notes` column, the summary table is in `README.md`.

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

**Rows are CASE-EXACT** (ruled 2026-10-31, seed `vfm-8k1`; built in `vocabulary_formats-7a1`).
`i16.5` is not an ICD-10-CM code. A row that is case-insensitive declares it with the scoped flag
`(?i:...)`. No row does today, because no published code in any vocabulary here is lower case
except the SNOMED UUIDs, which are ONLY lower case (`SNOMED.WITHRETIRED` uses `[0-9a-f]`). Never
write `\w` or a lower-case range in a regexp again: `\w` admits lower case and `_`. A caller
whose source writes codes in lower case changes the case itself, in a named step.

Related: usage-specific strictness belongs in the CALLER, never here. A >=4-character floor for
*scanning* free text is correct in a scanner (bare 3-char categories appear in ordinary disease
prose) but would be a forbidden false negative here, since I10 is a legitimate code. Completeness is
the line, not width: a narrowing that costs no real code belongs HERE, and one that would cost even a
single real code belongs in the caller.

## THE LABEL REGISTRY: a missing row is NOT a decision

`vocabulary_labels.tsv` is the ONLY place a vocabulary label is normalized — producers extract it
verbatim (ruled 2026-08-04, `vocabulary_formats-wyf`). A lookup has **five** outcomes:

- row, `mapped` → bind to `vocabulary_id`.
- row, `unsupported` → ADJUDICATED: no OHDSI home. Drop, expected and counted.
- row, `multi_vocabulary` → ADJUDICATED: the producer SPLITS the set (habitat rule 4).
- row, `needs_context` → ADJUDICATED: the caller PICKS one of `candidates` from the paper's
  context; a lookup that cannot pick must surface it, never default.
- **NO ROW → UNADJUDICATED.** Nobody has looked. Surface and count it — an error condition that
  needs a human, never a quiet drop.

The first four are decisions; the fifth is the absence of one. A consumer that treats "not found"
like a blank `vocabulary_id` silently loses a mappable code set and reports it identically to one
we deliberately declined. **Never add a `status=unseen` row** — a row would mean someone looked, and
`just lint` rejects any status outside the four. The miss report belongs in the PRODUCER; do not
add producer code here.

A lookup compares labels after **THE LABEL FOLD** (ruled 2026-09-30, `vocabulary_formats-7j0`;
the contract is in README, the reference is `fold_label` in `checks/lint.py`): Pd dashes and U+2212
become `-` (U+00AD soft hyphen does NOT); whitespace — the Unicode `White_Space` property, 25 code
points written out as `WHITE_SPACE`, NBSP included, and NOT `str.isspace()` / `\s`, which add
U+001C–U+001F (`vocabulary_formats-ssu`) — collapses and is dropped beside a dash; case is folded.
Dashes and spaces are never removed, so `ICD 10 CM`, `ICD-10-CM` and `ICD10CM` are three rows. `just lint` fails if two labels fold together — a variant the fold covers
gets a `source` entry on the existing row, not a row. Bare `Read` has deliberately NO row (seed
`vfm-b19`, deferred until Read-code work starts).

## Tech Stack

- Language: the PUBLISHED artifacts are data only (TSV/Parquet) — nothing a consumer loads is code.
  `checks/` holds the gate (Python), which no consumer imports; the tables stay polyglot.
- Framework: none. `justfile` is the front door, `Makefile` still owns TSV -> parquet.
- Key dependencies: duckdb only, and never installed — `uv run --no-project --with 'duckdb<2'`, the same
  way icd10cm and ohdsi_supplemental_vocabs do it. No pyproject, no lockfile, nothing to maintain.

## Purpose

Provides regular expressions that verify if medical terminology codes "look" valid without requiring database lookups. Never rejects a real code — and past that floor, admits as few non-codes as a plain regexp reasonably can (rule 2). Useful for validating codes from claims data, vocabulary files, or user input.

## Key Entry Points

**The published interface is SIX files and nothing else**: `vocabulary_formats.tsv`/`.parquet` (the
regexps, human-editable TSV), `vocabulary_labels.tsv`/`.parquet` (the label registry, same shape) and
`vocabulary_composition.tsv`/`.parquet` (hybrid -> source vocabularies, same shape).
`checks/`, the `justfile` and the `Makefile` are internal machinery — no consumer imports them, which
is what keeps the tables polyglot. `README.md` states this for consumers, with what to pin to (a
commit SHA; there are no tags) and what may change under them.

- `vocabulary_composition.tsv` — ruled 2026-09-30 (`vocabulary_formats-909`): `CPT4_HCPCS` ->
  {`CPT4`, `HCPCS`}, so a lookup keyed on published vocabularies (editions) fans out through it
  instead of joining the widened label target and finding nothing. HCPCS finds its editions; CPT4
  honestly finds none (no UMLS licence). **Never add edition rows for a hybrid** — it has no
  publisher, release or cadence. The `CPT` / `CPT-4` / `HCPCS` widening notes in
  `vocabulary_labels.tsv` stay as they are; this table complements them, it does not undo them.
- `vocabulary_formats.csv` — **RETIRED** 2024-06-21 (`446f5cb`), replaced by the TSV; ruled
  2026-08-13 that it stays retired. The raw URL 404s. A consumer moving off it must bind a boundary
  in the same change: the CSV's patterns were anchored `^…$`, today's are bare, so a bare URL swap
  silently widens the match. Retiring anything else means a note in that README section — its
  absence is what let this break go unsignalled for two years.

## Commands

```bash
just lint    # THE GATE — structural, no database, seconds. Run before every commit.
just test    # the false-negative harness; skips cleanly when the machine has no concept table
just prose   # what each row admits from real running text; a REPORT, never a gate
make all     # regenerate every parquet after editing a TSV (just lint checks that you did)
```

**`just lint`** enforces what nothing else did: every regexp compiles, **no anchors** and **no
top-level alternation** in the regexp column (both invariants were measured once and then protected
only by memory), **no inline flag except the scoped `(?i:...)`** (the case declaration,
`vocabulary_formats-7a1`), unique keys, parquet in sync with the TSV, and every row's validation
target declared. It self-tests its own scanner against hand-built patterns first, because the code
enforcing those two rules can be silently wrong like any other. For `vocabulary_labels.tsv` it
enforces the registry's row contract (`vocabulary_formats-yq4`, 2026-09-30): `status` is one of
`mapped` / `unsupported` / `multi_vocabulary` / `needs_context`; `vocabulary_id` is filled IFF
`mapped`; `candidates` IFF `needs_context`, with 2+ distinct `|`-separated ids; and every `source`
entry parses as `<producer>:<run>[;key=count...]`, entries `|`-separated, no run twice
(`vocabulary_formats-7dl`) — self-tested on hand-built bad rows the same way; and every label is
unique after the label fold (`vocabulary_formats-7j0`), with the fold self-tested on hand-built
labels and colliding label columns. For `vocabulary_composition.tsv` it enforces a unique
(`vocabulary_id`, `source_vocabulary_id`) pair (`vocabulary_formats-909`), self-tested on
hand-built pair columns, and its parquet in sync like the other two.

**`just test`** replaces the hand-run snippet this section used to carry. It scores every row against
its OWN declared target — `checks/validation_targets.json`, where each target and every deliberate
exclusion lives as data with its evidence — and fails on any in-target false negative. Substrates are
a stock Athena `CONCEPT.csv` and a `vocabulation` build (schema `ohdsi_vocabs`, **not** `main`, and
the only place the OI-minted `CPT4_HCPCS` / `ICD03_*` exist), named by
`VOCABULARY_FORMATS_ATHENA_CSV` / `VOCABULARY_FORMATS_OI_DUCKDB`. Editing a regexp means re-running
it; adding a row means declaring its target, or lint fails. It also checks that every id
`vocabulary_labels.tsv` names — `vocabulary_id` and each of `candidates` — exists in the oi build's
`vocabulary` table; with only Athena present, ids Athena lacks are reported UNVERIFIED, never
missing, because Athena cannot hold the OI-minted ones. The same check, through the same code,
covers both ids of every `vocabulary_composition.tsv` row.

**Substrate paths live in an untracked `.env`, never in a tracked file** (`vocabulary_formats-6q7`,
2026-09-30). The justfile has `set dotenv-load`; `.env.example` lists all four names
(`_ATHENA_CSV`, `_OI_DUCKDB`, `_TABULAR_DUCKDB`, `_PAPERS_DIR`) without values. No script carries a
default path, and an UNSET variable is a loud SKIP naming the variable, because the gate runs on
every commit and a quiet skip hides a disarmed check. A fresh clone or worktree has no `.env`, so
`just test` there skips every row until one is copied in.

**`just prose`** answers the other half: not "does this row reject a real code?" but "what ELSE does
it accept?", scored against real running text — the FY2026 ICD-10-CM tabular (21,248 tokens) and the
litmine pilot's 20 papers (17,570). It is a **report, not a gate**: a row that admits half the
dictionary may be honest, and the right answer is then a `notes` entry saying the row cannot carry
its own weight, not a narrowing that costs a real code. `--try 'LABEL=REGEXP'` scores a candidate
beside the row it would replace, which is how a before/after pair is produced. **Narrowing a row
means running both**: `just prose` says what the change bought, `just test` says what it cost.

Gotcha: ICD vocabularies are NON-standard in OMOP, so `standard_concept` is NULL — never filter
`standard_concept='S'` for them or you get zero rows.

## Relationships

- **Depends on**: None. The published tables carry no code and no runtime — a Ruby or R consumer
  reads them as-is. `checks/` is Python because the gate has to run somewhere; keep it out of what
  ships.
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
- Rows for labels the harvest has not met yet. The registry is **harvest-fed** (ruled 2026-08-04):
  the producer emits unseen labels with counts → a domain agent (Odie or Vincent, per habitat
  routing) adjudicates the status and validates the target against the concept table → the row
  lands here with a `source` entry and **evidence in `notes`**, not an asserted target → `make all`,
  `just lint`, `just test`. A label seen again APPENDS a `source` entry; it never overwrites one.
  The full loop and the `source` grammar are in README's registry section.

## Domain Concepts

- **vocabulary_id**: OMOP vocabulary identifier (e.g., ICD9CM, NDC, CPT4)
- **DOTLESS variants**: Codes without decimal points, common in Medicare claims
- **WITHMODIFIERS variants**: Include procedure modifiers in same vocabulary

## Principles

- A vocabulary's code format is ONE regexp that must match every code the vocabulary publishes, then be narrowed to admit as few non-codes as a plain regexp reasonably can — guarded by a test over the published set, because a miss is silent: the reference does not go wrong, it vanishes. — vfm-ges, 2026-08-12
- Judge a format's false positives against ordinary PROSE, not just against sibling vocabularies — these regexps are used to FIND codes in text, so a shape that also matches "ABC", "ALL" or "Age" fails even when it excludes every neighbouring vocabulary. — vfm-311, 2026-08-12
