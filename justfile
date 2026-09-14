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

# Arm THIS clone's git hooks. A gate in .git/hooks is per-clone and untracked, so a
# fresh clone silently has none; this recipe is the tracked declaration that one is
# expected, plus the installer. `habituate repo-doctor` reports an unarmed clone.
# Chains the beads hook first and preserves any hook it did not write.
hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    root="$(git rev-parse --show-toplevel)"
    # RESOLVE FROM THE GIT DIR, NOT `--git-path hooks`. --git-path HONOURS core.hooksPath,
    # which beads points at .beads/hooks -- so the obvious call aimed this recipe at beads'
    # OWN shim and wrote the dispatcher over it. The dispatcher then chains
    # "$root/.beads/hooks/$h", i.e. itself, and every commit recursed until the shell gave
    # up. Measured by the seeds session 2026-09-13: `git commit` hung silently, reporting
    # only "shell level (1000) too high", until killed at two minutes. Their fix, adopted
    # here verbatim; the guard below is the half that matters, turning a silent self-call
    # into a loud refusal.
    hooks="$(git rev-parse --absolute-git-dir)/hooks"
    case "$hooks" in
        */.beads/hooks)
            echo "refusing to write hooks inside .beads: $hooks" >&2
            echo "core.hooksPath still points at beads; unset it first" >&2
            exit 1
            ;;
    esac
    # A linked worktree shares the git COMMON dir, so arming from one would reach OUT of it
    # and mv the main checkout's live hooks aside while it is using them. One arming covers
    # every worktree, which is why this refuses rather than "fixes" the path.
    if [ "$(git rev-parse --git-common-dir)" != "$(git rev-parse --git-dir)" ]; then
        echo "refusing: run 'just hooks' in the MAIN checkout, not a worktree." >&2
        echo "  hooks are shared via the git common dir, so arming there covers this worktree too." >&2
        exit 1
    fi
    mkdir -p "$hooks"
    for h in pre-commit pre-push; do
        just --summary 2>/dev/null | tr ' ' '\n' | grep -qx "$h" || continue
        live="$hooks/$h"
        # DEFER TO THE BEADS PUSH DRIVER. It already runs the beads shim, then `just
        # pre-push`, then `bd dolt push` -- a superset of this wrapper. Preserving and
        # chaining it instead makes the gate run TWICE per push (measured: ~14 min rather
        # than ~7 in a Spark-backed repo) and fires the beads hook twice. Neither piece is
        # wrong alone; the interaction is.
        if grep -qs 'beads-install-push-driver' "$live"; then
            echo "kept: $h (beads push driver already runs this gate)"
            continue
        fi
        # Never clobber a hook this recipe did not write; chain it instead.
        keep=""
        if [ -f "$live" ] && ! grep -qs 'just hooks' "$live"; then
            mkdir -p "$hooks/preserved"
            keep="$hooks/preserved/$h"
            [ -e "$keep" ] || { mv "$live" "$keep"; chmod +x "$keep"; }
        fi
        {
            echo '#!/usr/bin/env sh'
            echo '# Written by `just hooks`. Re-run to regenerate.'
            echo 'set -e'
            echo 'root="$(git rev-parse --show-toplevel)"'
            echo 'hooks="$(git rev-parse --absolute-git-dir)/hooks"'
            [ -n "$keep" ] && echo "p=\"\$hooks/preserved/$h\"; [ -x \"\$p\" ] && { \"\$p\" \"\$@\" || exit \$?; }"
            echo "b=\"\$root/.beads/hooks/$h\"; [ -x \"\$b\" ] && { \"\$b\" \"\$@\" || exit \$?; }"
            echo "cd \"\$root\" && exec just $h"
        } > "$live"
        chmod +x "$live"
        echo "armed: $h"
    done
