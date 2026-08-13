"""Structural lint over the two published tables. NO DATABASE, NO NETWORK, fast.

This is the gate (`just lint`). It answers "is the table well-formed, and does it still obey the
invariants we measured?" -- never "is a regexp right", which needs the concept table and lives in
`just test` (checks/false_negatives.py).

Every check here was previously protected by nothing but memory:

  compiles          a row that does not compile takes down every consumer that loads the table
  no anchors        stripped from all 34 rows 2026-08-12; the caller binds the boundary now
  no top-level |    asserted once when the anchors were stripped, enforced by nothing since
  unique key        a duplicate vocabulary_id makes "the regexp for X" ambiguous
  parquet in sync   TSV and parquet are BOTH the published interface (vocabulary_formats-t5u)
  columns / tabs    the file is read as TSV by every consumer
  targets declared  a row with no entry in validation_targets.json is silently never validated

Regexps are compiled with Python's `re`. The column is documented as PCRE, but the live consumers
(litmine, codesistant) are Python, so Python is the compiler that decides whether a row works.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMATS = ROOT / "vocabulary_formats.tsv"
LABELS = ROOT / "vocabulary_labels.tsv"
TARGETS = Path(__file__).resolve().parent / "validation_targets.json"

TABLES = {
    FORMATS: ["vocabulary_id", "regexp", "source", "notes"],
    LABELS: ["label", "vocabulary_id", "status", "source", "notes"],
}

ANCHOR_RULE = """
    RULE: the regexp column carries NO boundary. The anchors were stripped from all 34 rows on
    2026-08-12 and binding them became the CALLER's job -- a caller writes \\A(?:pattern)\\z.
    An anchor left here is invisible in both directions: it double-anchors for a caller that
    wraps, and it silently works for a caller that does not, so nothing errors and the row
    quietly means two different things to two consumers. Delete it. If a boundary is needed,
    the caller supplies it.
"""

ALTERNATION_RULE = """
    RULE: every row must be a SINGLE SELF-CONTAINED expression. A caller that writes ^pattern$
    around a bare `a|b` gets `(^a)|(b$)` -- the anchors bind to the first branch only, and the
    row starts matching any string that merely ENDS in b. Wrap the alternation in a group:
    (?:a|b). This held for all 34 rows when the anchors were stripped; keep it that way.
"""

PARQUET_RULE = """
    RULE: the TSV and the parquet are BOTH the published interface (vocabulary_formats-t5u), and
    a consumer reading the stale one gets an answer nobody reviewed. Regenerate and commit:
        make all
    (lint deliberately does NOT run make itself -- a gate that repairs the thing it is judging
    reports green while the committed artifact is still wrong.)
"""

TARGETS_RULE = """
    RULE: every row in vocabulary_formats.tsv declares its target in checks/validation_targets.json,
    because a row with no target is one `just test` silently never scores -- which is how the notes
    column became the only record that a row had ever been checked (vocabulary_formats-h0x).
"""

KNOWN_TARGET_KEYS = {
    "vocabulary_id",
    "source",
    "concept_vocabulary_ids",
    "concept_classes",
    "valid_only",
    "transform",
    "code_filter",
    "exclusions",
    "class_note",
}
KNOWN_TRANSFORMS = {"strip_dots", "strip_leading_zeros", "strip_behavior_suffix"}

failures = []


def fail(where, what, rule=""):
    failures.append((where, what, rule))


def bound(pattern):
    r"""The pattern as a CALLER binds it: \A(?:pattern)\z.

    Python spells PCRE's \z as \Z (Python's \z is not an escape at all), so the wrapper below is
    the same boundary the documented contract names, in the dialect the live consumers run.
    """
    return r"\A(?:%s)\Z" % pattern


def scan_pattern(pattern):
    """Walk a regexp once. Returns (anchors, top_level_alternations) as [(offset, token)].

    Tracks escapes, character classes and group depth so that the legitimate uses are not
    flagged: `^` at the head of a class is negation, `$` inside a class is a literal dollar,
    and `|` inside any group is ordinary alternation.
    """
    anchors, alternations = [], []
    depth, in_class, i = 0, False, 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            nxt = pattern[i + 1] if i + 1 < len(pattern) else ""
            if not in_class and nxt in "AzZbB":
                anchors.append((i, "\\" + nxt))
            i += 2
            continue
        if in_class:
            if ch == "]":
                in_class = False
            i += 1
            continue
        if ch == "[":
            in_class = True
            i += 1
            if i < len(pattern) and pattern[i] == "^":  # negation, not an anchor
                i += 1
            if i < len(pattern) and pattern[i] == "]":  # a literal ] must lead the class
                i += 1
            continue
        if ch in "^$":
            anchors.append((i, ch))
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "|" and depth == 0:
            alternations.append((i, "|"))
        i += 1
    return anchors, alternations


# The scanner is the check with teeth, so it gets hand-built inputs with hand-computed answers.
# Every case here is one where a naive `'^' in pattern` / `'|' in pattern` test gets it wrong in
# one direction or the other. (pattern, anchor tokens, top-level alternation count)
SCANNER_SELFTEST = [
    (r"\w{5}", [], 0),
    (r"^\w{5}$", ["^", "$"], 0),  # the anchors this rule exists to catch
    (r"\A\d{3}\z", ["\\A", "\\z"], 0),  # ... and their escape spellings
    (r"\bfoo\b", ["\\b", "\\b"], 0),
    (r"[^A-Z]+", [], 0),  # '^' heading a class is negation, NOT an anchor
    (r"[$]", [], 0),  # '$' inside a class is a literal dollar
    (r"[]$^]", [], 0),  # a literal ']' may lead a class; the rest stays inside it
    (r"a|b", [], 1),  # the alternation this rule exists to catch
    (r"(a|b)", [], 0),  # grouped: fine
    (r"(?:a|b)c", [], 0),
    (r"(?:a|b)|c", [], 1),  # grouped AND bare: still broken
    (r"\|", [], 0),  # an escaped pipe is a literal, not alternation
    (r"\\|x", [], 1),  # an escaped backslash, THEN a real alternation
    (r"[a|b]", [], 0),  # a pipe inside a class is a literal
]


def selftest_scanner():
    for pattern, want_anchors, want_alts in SCANNER_SELFTEST:
        anchors, alternations = scan_pattern(pattern)
        got_anchors = [token for _, token in anchors]
        if got_anchors != want_anchors or len(alternations) != want_alts:
            fail(
                "checks/lint.py scan_pattern",
                f"self-test failed on {pattern!r}: anchors {got_anchors!r} (want {want_anchors!r}), "
                f"{len(alternations)} top-level alternation(s) (want {want_alts})",
                "    RULE: the scanner is what enforces the two invariants that nothing else\n"
                "    protects. A scanner that is wrong reports green over a broken table, so it is\n"
                "    checked against hand-computed answers every time the gate runs.",
            )


def read_table(path, columns):
    """Parse a TSV by hand -- no csv module, no duckdb. Checks tabs, columns, and returns rows."""
    text = path.read_bytes().decode("utf-8")
    if "\r" in text:
        fail(path.name, "contains CR characters; the file must use bare LF line endings")
    if not text.endswith("\n"):
        fail(path.name, "does not end with a newline")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        fail(path.name, "is empty")
        return []

    header = lines[0].split("\t")
    if header != columns:
        fail(
            path.name,
            f"header is {header!r}, expected {columns!r}",
            "    RULE: the column set is the published schema; consumers index it by name.",
        )
        return []

    rows = []
    for lineno, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(columns):
            fail(
                f"{path.name}:{lineno}",
                f"has {len(fields)} tab-separated fields, expected {len(columns)}",
                "    RULE: the file must be GENUINELY tab-delimited -- one tab between fields and\n"
                "    no embedded tabs. A short line means a missing trailing column (an empty final\n"
                "    column is a real value here); a long one means a tab inside a field.",
            )
            continue
        rows.append((lineno, dict(zip(columns, fields))))
    return rows


def check_regexps(rows):
    compiled = 0
    for lineno, row in rows:
        vid, pattern = row["vocabulary_id"], row["regexp"]
        if not vid.strip():
            fail(f"{FORMATS.name}:{lineno}", "has an empty vocabulary_id")
        if not pattern.strip():
            fail(f"{FORMATS.name}:{lineno} {vid}", "has an empty regexp")
            continue

        anchors, alternations = scan_pattern(pattern)
        for offset, token in anchors:
            fail(
                f"{FORMATS.name}:{lineno} {vid}",
                f"regexp contains the ANCHOR {token!r} at offset {offset}: {pattern}",
                ANCHOR_RULE,
            )
        for offset, _ in alternations:
            fail(
                f"{FORMATS.name}:{lineno} {vid}",
                f"regexp has a TOP-LEVEL ALTERNATION '|' at offset {offset}: {pattern}",
                ALTERNATION_RULE,
            )

        try:
            re.compile(bound(pattern))
        except re.error as exc:
            fail(
                f"{FORMATS.name}:{lineno} {vid}",
                f"regexp does not compile as \\A(?:...)\\z -- {exc}: {pattern}",
                "    RULE: a row that does not compile takes down every consumer that loads the\n"
                "    table, not just the row that owns it.",
            )
            continue
        compiled += 1
    return compiled


def check_unique(rows, key, filename):
    seen = {}
    for lineno, row in rows:
        value = row[key]
        if value in seen:
            fail(
                f"{filename}:{lineno}",
                f"duplicate {key} {value!r} (first seen on line {seen[value]})",
                f"    RULE: {key} is the lookup key. A duplicate makes 'the row for {value}'\n"
                "    ambiguous, and which one a consumer gets depends on how it loads the file.",
            )
        else:
            seen[value] = lineno


def check_parquet_in_sync(malformed):
    """Compare the COMMITTED parquet against the TSV, content for content.

    `malformed` names TSVs that already failed the structural checks: comparing a file that is
    not a TSV against its parquet answers a question nobody asked, and the real complaint has
    already been filed.
    """
    try:
        import duckdb
    except ImportError:
        fail("parquet sync", "duckdb is not importable -- run this through `just lint`")
        return

    con = duckdb.connect(":memory:")
    for tsv in (FORMATS, LABELS):
        parquet = tsv.with_suffix(".parquet")
        if tsv in malformed:
            print(f"  {parquet.name}: not compared -- {tsv.name} did not survive the checks above")
            continue
        if not parquet.exists():
            fail(parquet.name, "is missing", PARQUET_RULE)
            continue
        tsv_sql = str(tsv).replace("'", "''")
        pq_sql = str(parquet).replace("'", "''")
        # Read the TSV exactly as the Makefile does, so this compares the artifacts and not
        # two different opinions about how to parse a TSV.
        try:
            from_tsv = con.execute(
                f"SELECT * FROM read_csv('{tsv_sql}', delim = '\t', header = true)"
            )
            tsv_cols = [d[0] for d in from_tsv.description]
            tsv_rows = from_tsv.fetchall()
            from_pq = con.execute(f"SELECT * FROM read_parquet('{pq_sql}')")
            pq_cols = [d[0] for d in from_pq.description]
            pq_rows = from_pq.fetchall()
        except duckdb.Error as exc:
            fail(
                tsv.name,
                f"cannot be read as a TSV by duckdb -- {exc.__class__.__name__}: "
                f"{str(exc).splitlines()[0]}",
                "    RULE: `make all` reads this file with duckdb to build the parquet, so a file\n"
                "    duckdb cannot parse cannot be published at all. Fix the delimiters/quoting\n"
                "    first; the parquet comparison cannot run until it parses.",
            )
            continue

        raw_lines = tsv.read_text(encoding="utf-8").rstrip("\n").count("\n")
        if len(tsv_rows) != raw_lines:
            fail(
                tsv.name,
                f"duckdb parses {len(tsv_rows)} rows but the file has {raw_lines} data lines",
                "    RULE: the TSV must mean the same thing to a line-oriented reader and to a CSV\n"
                "    parser. A mismatch means a quote or newline inside a field is being consumed.",
            )
        if tsv_cols != pq_cols:
            fail(parquet.name, f"columns are {pq_cols!r}, TSV has {tsv_cols!r}", PARQUET_RULE)
            continue
        if len(tsv_rows) != len(pq_rows):
            fail(
                parquet.name,
                f"has {len(pq_rows)} rows, {tsv.name} has {len(tsv_rows)}",
                PARQUET_RULE,
            )
            continue
        for i, (a, b) in enumerate(zip(tsv_rows, pq_rows), start=2):
            if a != b:
                fail(
                    parquet.name,
                    f"row {i - 1} differs from {tsv.name}:{i}\n"
                    f"        tsv:     {a!r}\n"
                    f"        parquet: {b!r}",
                    PARQUET_RULE,
                )
                break
    con.close()


def check_targets(rows):
    try:
        declaration = json.loads(TARGETS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(TARGETS.name, f"is missing or unparseable -- {exc}", TARGETS_RULE)
        return

    sources = declaration.get("sources", {})
    targets = declaration.get("targets", [])
    declared = {}
    for target in targets:
        vid = target.get("vocabulary_id")
        if vid is None:
            fail(TARGETS.name, f"a target has no vocabulary_id: {target!r}")
            continue
        if vid in declared:
            fail(TARGETS.name, f"duplicate target for {vid!r}")
        declared[vid] = target

        unknown = set(target) - KNOWN_TARGET_KEYS
        if unknown:
            fail(
                f"{TARGETS.name} {vid}",
                f"unknown key(s) {sorted(unknown)!r}",
                "    RULE: a key the harness does not read is a filter that silently does nothing.\n"
                f"    Known keys: {sorted(KNOWN_TARGET_KEYS)!r}",
            )
        if target.get("source") not in sources:
            fail(f"{TARGETS.name} {vid}", f"names unknown source {target.get('source')!r}")
        if not target.get("concept_vocabulary_ids"):
            fail(f"{TARGETS.name} {vid}", "declares no concept_vocabulary_ids")
        transform = target.get("transform")
        if transform is not None and transform not in KNOWN_TRANSFORMS:
            fail(
                f"{TARGETS.name} {vid}",
                f"unknown transform {transform!r}; known: {sorted(KNOWN_TRANSFORMS)!r}",
            )
        code_filter = target.get("code_filter")
        if code_filter is not None:
            try:
                re.compile(bound(code_filter.get("pattern", "")))
            except re.error as exc:
                fail(f"{TARGETS.name} {vid}", f"code_filter.pattern does not compile -- {exc}")
            if not code_filter.get("why", "").strip():
                fail(f"{TARGETS.name} {vid}", "code_filter has no 'why'")
        for exclusion in target.get("exclusions", []):
            has_codes = bool(exclusion.get("codes"))
            has_prefix = bool(exclusion.get("name_prefix"))
            if has_codes == has_prefix:
                fail(
                    f"{TARGETS.name} {vid}",
                    f"exclusion must have exactly one of codes / name_prefix: {exclusion!r}",
                )
            if not exclusion.get("why", "").strip():
                fail(
                    f"{TARGETS.name} {vid}",
                    f"exclusion has no 'why': {exclusion!r}",
                    "    RULE: an exclusion without evidence -- concept_id, invalid_reason, class --\n"
                    "    is just a regexp that lost an argument. The reason IS the record.",
                )

    in_tsv = {row["vocabulary_id"] for _, row in rows}
    for vid in sorted(in_tsv - set(declared)):
        fail(TARGETS.name, f"no target declared for row {vid!r}", TARGETS_RULE)
    for vid in sorted(set(declared) - in_tsv):
        fail(
            TARGETS.name,
            f"target {vid!r} has no row in {FORMATS.name}",
            "    RULE: an orphan target scores nothing and hides a rename.",
        )


def main():
    print(f"lint: {ROOT}")
    selftest_scanner()
    print(f"  scan_pattern self-test: {len(SCANNER_SELFTEST)} hand-built patterns")
    malformed = set()
    rows_by_table = {}
    for path in (FORMATS, LABELS):
        before = len(failures)
        rows_by_table[path] = read_table(path, TABLES[path])
        if len(failures) > before:
            malformed.add(path)
        print(f"  {path.name}: {len(rows_by_table[path])} rows, {len(TABLES[path])} columns")
    formats_rows, labels_rows = rows_by_table[FORMATS], rows_by_table[LABELS]

    compiled = check_regexps(formats_rows)
    print(f"  regexps that compile as \\A(?:...)\\z: {compiled}/{len(formats_rows)}")
    check_unique(formats_rows, "vocabulary_id", FORMATS.name)
    check_unique(labels_rows, "label", LABELS.name)
    check_parquet_in_sync(malformed)
    check_targets(formats_rows)

    if not failures:
        print("\nOK: no anchors, no top-level alternation, unique keys, parquet in sync,")
        print("    every row's validation target declared.")
        return 0

    print(f"\nFAILED: {len(failures)} problem(s)\n")
    for where, what, rule in failures:
        print(f"  {where}: {what}")
        if rule:
            print(rule.rstrip("\n"))
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
