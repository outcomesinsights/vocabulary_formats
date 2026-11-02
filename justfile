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

# duckdb is pinned below 2: the stock 2.x wheel dies with SIGILL on titan (ruled 2026-10-28).
python := "uv run --no-project --with 'duckdb<2' python"

# so `just prose --try 'X=\w{3}'` reaches the script intact instead of through the shell twice
set positional-arguments

# Substrate and corpus paths come from this host's UNTRACKED .env (names in .env.example). No
# script carries a default path; an unset variable makes its check SKIP loudly, naming it.
set dotenv-load

# default: the gate that needs nothing
default: lint

# Install the pinned tools and arm THIS checkout's hooks (gator's githooks standard). Every
# clone, host and worktree runs it once: a hook arrangement cannot travel in a commit.
setup:
    mise install
    @if [ -d .beads ] && [ ! -d .beads/embeddeddolt ] && command -v bd >/dev/null 2>&1; then bd bootstrap; fi
    @if [ -d .githooks ]; then git config core.hooksPath .githooks; fi

# THE GATE. Regexps compile; no anchors; no top-level alternation; unique keys; parquet in sync
# with the TSV; every row's validation target declared. Rules live in checks/lint.py.
lint:
    #!/usr/bin/env bash
    set -uo pipefail
    ruff check || exit 1
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

# regenerate every parquet from its TSV. Run after editing a TSV, then commit both — `just lint`
# checks that you did.
parquet:
    make all

# Format every tracked file, in every language present. Config: treefmt.toml (gator's blocks).
fmt:
    treefmt

# Report format drift. treefmt --fail-on-change FORMATS and then exits 1: fix-and-fail, so
# re-stage and commit again.
fmt-check:
    treefmt --fail-on-change

# The seed store's own check. --gate, not --against-git: only --gate honours
# SEEDS_GATE_CONFIRM=1, the escape for an intended rewrite of many seeds (seeds-ikkx).
seeds-check:
    @command -v seeds >/dev/null 2>&1 || exit 0; seeds check --gate

# Full local CI equivalent — run this before pushing.
# This repo has no hosted CI, so this recipe IS the contract: the push gate
# (.githooks/pre-push) runs it at the pushed commit, and a check it lacks is not run at all.
ci: lint fmt-check test seeds-check

# Kept for checkouts still on the old hook wrappers, which call it by name. The standard
# .githooks/pre-push runs `ci` at the pushed commit instead. Delete this recipe only when every
# checkout of this repo is armed (gator docs/githooks-migration.md, "Ending the transition").
pre-push: ci

# The commit gate. The standard .githooks/pre-commit runs this on the working tree. `test` is
# NOT here: it takes about 51 s (measured 2026-11-02), over the 30 s commit budget, so it runs
# in `ci` at every push instead.
pre-commit: fmt-check lint seeds-check
