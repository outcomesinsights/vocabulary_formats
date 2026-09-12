# vocabulary_formats — the front door. Two commands, split by whether they need a database.
#
#   just lint    STRUCTURAL. No database, no network, seconds. THIS IS THE GATE.
#   just test    the false-negative harness: every row scored against its own declared target.
#                Needs an OHDSI concept table and SKIPS cleanly without one.
#
# The split is the point: a gate that needs a 1.4 GB vocabulary download is a gate nobody keeps,
# and a repo with no gate at all cannot be dispatched into (vocabulary_formats-h0x).
#
# This repo has no pyproject.toml and needs none — duckdb arrives via `uv run --with`, the same
# way icd10cm and ohdsi_supplemental_vocabs do it. The Makefile still owns TSV -> parquet; this
# file does not replace it, and `just lint` deliberately does not run it (see checks/lint.py).

python := "uv run --no-project --with duckdb python"

# so `just prose --try 'X=\w{3}'` reaches the script intact instead of through the shell twice
set positional-arguments

# default: the gate that needs nothing
default: lint

# THE GATE. Regexps compile; no anchors; no top-level alternation; unique keys; parquet in sync
# with the TSV; every row's validation target declared. Rules live in checks/lint.py.
lint:
    #!/usr/bin/env bash
    set -uo pipefail
    mkdir -p claude_stuff
    log="claude_stuff/lint-$(date +%Y%m%d-%H%M%S).log"
    {{ python }} checks/lint.py 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
    echo "log: $log" | tee -a "$log"
    exit $rc

# THE FALSE-NEGATIVE HARNESS. Pulls each row's declared target out of the concept table and
# requires every code in it to match — the check that used to live as prose in the notes column.
# Targets and their deliberate exclusions are data: checks/validation_targets.json.
test:
    #!/usr/bin/env bash
    set -uo pipefail
    mkdir -p claude_stuff
    log="claude_stuff/false-negatives-$(date +%Y%m%d-%H%M%S).log"
    {{ python }} checks/false_negatives.py 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
    echo "log: $log" | tee -a "$log"
    exit $rc

# THE PROSE-ADVERSARY REPORT. What each row admits from ordinary running text, which is the
# question the cross-vocabulary false-positive numbers cannot see (vocabulary_formats-wir). NOT a
# gate: it never fails, because a row that admits half the dictionary may still be honest. Score a
# candidate narrowing beside the row it would replace:
# just prose --try 'ICD10=[A-Za-z][0-9][0-9A-Za-z](\.\w{1,4})?'
prose *ARGS:
    #!/usr/bin/env bash
    set -uo pipefail
    mkdir -p claude_stuff
    log="claude_stuff/prose-$(date +%Y%m%d-%H%M%S).log"
    {{ python }} checks/prose.py "$@" 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
    echo "log: $log" | tee -a "$log"
    exit $rc

# regenerate both parquets from their TSVs. Run after editing a TSV, then commit both — `just lint`
# checks that you did.
parquet:
    make all

# Rewrite files to canonical format. Run deliberately; never from a hook.
fmt:
    uv run ruff format .
    just --fmt --unstable
    git ls-files "*.md" | xargs -r mdformat

# Report format drift without changing anything. This is what the hooks run —
# a formatter that rewrites files mid-commit changes what you already reviewed.
fmt-check:
    uv run ruff format --check .
    just --fmt --check --unstable
    git ls-files "*.md" | xargs -r mdformat --check

# Full local CI equivalent — run this before pushing.
# The recipe IS the contract: if CI runs a check and this does not, the gate is
# decorative (see ~/.config/home-manager/docs/ci-gates.md).
ci: fmt-check lint test

# What actually runs before a push. Defaults to the complete `ci`; point it at
# something smaller ONLY where running complete CI locally is impractical.
pre-push: ci

# Runs on every commit, so it must stay FAST — a sub-minute budget. Tests belong
# here when they fit; lint alone when they do not. fmt-check never rewrites.
pre-commit: fmt-check lint test
