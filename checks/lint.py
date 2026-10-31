"""Structural lint over the three published tables. NO DATABASE, NO NETWORK, fast.

This is the gate (`just lint`). It answers "is the table well-formed, and does it still obey the
invariants we measured?" -- never "is a regexp right", which needs the concept table and lives in
`just test` (checks/false_negatives.py).

Every check here was previously protected by nothing but memory:

  compiles          a row that does not compile takes down every consumer that loads the table
  no anchors        stripped from all 34 rows 2026-08-12; the caller binds the boundary now
  no top-level |    asserted once when the anchors were stripped, enforced by nothing since
  inline flags      a row is case-exact; the ONLY inline flag allowed is the scoped (?i:...),
                    which declares case-insensitivity (vfm-8k1, vocabulary_formats-7a1)
  unique key        a duplicate vocabulary_id makes "the regexp for X" ambiguous
  parquet in sync   TSV and parquet are BOTH the published interface (vocabulary_formats-t5u)
  columns / tabs    the file is read as TSV by every consumer
  targets declared  a row with no entry in validation_targets.json is silently never validated
  label rows        vocabulary_labels: status is a known value, vocabulary_id is filled IFF mapped,
                    candidates IFF needs_context (2+ distinct ids), and every `source` entry
                    parses. Consumers in two languages branch on status, so an unknown value is a
                    row that silently falls through every branch (vocabulary_formats-yq4, -7dl).
  label fold        vocabulary_labels: labels are unique AFTER THE LABEL FOLD, the comparison every
                    consumer's lookup performs -- two rows that fold together are one lookup key
                    with two answers (vocabulary_formats-7j0).
  composition pair  vocabulary_composition: (vocabulary_id, source_vocabulary_id) is unique -- a
                    repeated pair makes an edition lookup fan out to the same source twice
                    (vocabulary_formats-909).

Regexps are compiled with Python's `re`. The column is documented as PCRE, but the live consumers
(litmine, codesistant) are Python, so Python is the compiler that decides whether a row works.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMATS = ROOT / "vocabulary_formats.tsv"
LABELS = ROOT / "vocabulary_labels.tsv"
COMPOSITION = ROOT / "vocabulary_composition.tsv"
TARGETS = Path(__file__).resolve().parent / "validation_targets.json"

TABLES = {
    FORMATS: ["vocabulary_id", "regexp", "context", "use", "source", "notes"],
    LABELS: ["label", "vocabulary_id", "candidates", "status", "source", "notes"],
    COMPOSITION: ["vocabulary_id", "source_vocabulary_id", "notes"],
}

# vocabulary_labels.tsv. The status set is CLOSED: a consumer branches on it, and a value it does
# not know is a row it silently drops. There is deliberately no `unseen` status -- a label nobody
# has adjudicated has NO ROW, because a row would mean someone looked (vocabulary_formats-wyf).
LABEL_STATUSES = {"mapped", "unsupported", "multi_vocabulary", "needs_context"}

# '|' means LIST everywhere in vocabulary_labels.tsv: the ids in `candidates` and the entries in
# `source` (ruled 2026-09-30).
LIST_DELIMITER = "|"

# One `source` ENTRY: <producer>:<run>, then optional ;key=count pairs whose counts are per run.
# e.g. litmine:pilot-2026-07;sets=117;papers=10  or  code_collector:vocabulary_labels.py@1a2b3c4
SOURCE_ENTRY = re.compile(
    r"(?P<producer>[A-Za-z0-9_.-]+):(?P<run>[^;|\s]+)(?P<counts>(?:;[a-z_]+=[0-9]+)*)"
)

LABEL_RULE = """
    RULE: a registry row states ONE adjudicated decision, and its columns must agree with it:
      mapped            vocabulary_id filled, candidates blank
      unsupported       both blank -- no OHDSI home as of now
      multi_vocabulary  both blank -- the producer SPLITS the set (whether candidates may list
                        its components is undecided, vfm-bmg)
      needs_context     vocabulary_id blank, candidates = 2+ distinct '|'-separated ids; the
                        caller PICKS one per paper
    A label nobody has adjudicated gets NO ROW -- never a status of its own.
"""

SOURCE_RULE = """
    RULE: `source` is '|'-separated ENTRIES, each <producer>:<run>[;key=count...], e.g.
    litmine:pilot-2026-07;sets=117;papers=10. A later run APPENDS an entry and never overwrites
    one, and its counts are that run's alone -- so one run appearing twice double-counts it.
"""

ANCHOR_RULE = """
    RULE: the regexp column carries NO boundary. The anchors were stripped from all 34 rows on
    2026-08-12 and binding them became the CALLER's job -- a caller writes \\A(?:pattern)\\z.
    An anchor left here is invisible in both directions: it double-anchors for a caller that
    wraps, and it silently works for a caller that does not, so nothing errors and the row
    quietly means two different things to two consumers. Delete it. If a boundary is needed,
    the caller supplies it.
"""

FLAG_RULE = """
    RULE: a regexp is CASE-EXACT unless the row declares otherwise, and the only declaration is
    the SCOPED flag (?i:...) (Ryan, 2026-10-31, seed vfm-8k1). A GLOBAL flag such as (?i) is
    refused: every caller wraps the row as \\A(?:pattern)\\z, which puts the flag inside a group.
    Python 3.11+ then refuses to compile it, and Ruby applies it to the rest of the group, so the
    row means two different things to two consumers. Any other inline flag is refused too: the
    letters differ by dialect (Ruby's m is Python's s). Write (?i:...) around exactly the part
    that is case-insensitive.
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
KNOWN_TRANSFORMS = {
    "strip_dots",
    "strip_leading_zeros",
    "strip_behavior_suffix",
    "hyphenate_ndc_5_4_2",
}

failures = []


def fail(where, what, rule=""):
    failures.append((where, what, rule))


def bound(pattern):
    r"""The pattern as a CALLER binds it: \A(?:pattern)\z.

    Python spells PCRE's \z as \Z (Python's \z is not an escape at all), so the wrapper below is
    the same boundary the documented contract names, in the dialect the live consumers run.
    """
    return r"\A(?:%s)\Z" % pattern


def inline_flag(pattern, i):
    """The inline-flag group that opens at pattern[i] == '(', or None.

    A flag group is `(?` + flag letters (optionally `-` letters) + `)` (global) or `:` (scoped).
    `(?:`, `(?=`, `(?!`, `(?<`, `(?P<` and `(?#` are not flag groups. Returns the group's
    opening text, e.g. '(?i)' or '(?i:'.
    """
    if pattern[i + 1 : i + 2] != "?":
        return None
    j = i + 2
    while j < len(pattern) and (pattern[j].isalpha() or pattern[j] == "-"):
        j += 1
    letters = pattern[i + 2 : j]
    if not letters or letters.startswith("P") or j >= len(pattern):
        return None
    if pattern[j] in "):":
        return pattern[i : j + 1]
    return None


def scan_pattern(pattern):
    """Walk a regexp once. Returns (anchors, top_level_alternations, bad_flags) as
    [(offset, token)].

    Tracks escapes, character classes and group depth so that the legitimate uses are not
    flagged: `^` at the head of a class is negation, `$` inside a class is a literal dollar,
    and `|` inside any group is ordinary alternation. `bad_flags` is every inline-flag group
    except the one allowed declaration, the scoped `(?i:`.
    """
    anchors, alternations, bad_flags = [], [], []
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
            if (
                i < len(pattern) and pattern[i] == "]"
            ):  # a literal ] must lead the class
                i += 1
            continue
        if ch in "^$":
            anchors.append((i, ch))
        elif ch == "(":
            depth += 1
            flag = inline_flag(pattern, i)
            if flag is not None and flag != "(?i:":
                bad_flags.append((i, flag))
        elif ch == ")":
            depth -= 1
        elif ch == "|" and depth == 0:
            alternations.append((i, "|"))
        i += 1
    return anchors, alternations, bad_flags


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


# Inline flags, the same discipline: (pattern, refused flag tokens). The allowed declaration and
# every group that only LOOKS like a flag must pass; every global flag and every other letter fails.
FLAG_SELFTEST = [
    (r"(?i:[A-Z]\d{4})", []),  # the one allowed declaration
    (r"[A-Z](?i:[a-z]{2})", []),  # ... scoped to part of a row
    (
        r"(?i)[A-Z]\d{4}",
        ["(?i)"],
    ),  # global: what Python 3.11 refuses inside \A(?:...)\z
    (r"[A-Z](?i)x", ["(?i)"]),  # global, not at the start
    (r"(?m:^x)", ["(?m:"]),  # scoped, but m means different things in Ruby and Python
    (r"(?ix)a", ["(?ix)"]),
    (r"(?-i:A)", ["(?-i:"]),  # nothing to turn off: rows are already case-exact
    (r"(?:a|b)", []),  # non-capturing group, not a flag
    (r"(?=a)b", []),  # lookahead
    (r"(?<!a)b", []),  # lookbehind
    (r"(?P<x>a)", []),  # Python named group
    (r"\(?i\)", []),  # escaped parens are literals: an optional '(', 'i', ')'
    (r"\((?i)", ["(?i)"]),  # a literal '(' and THEN a real global flag
    (r"[(?i)]", []),  # inside a class it is four literal characters
]


def selftest_scanner():
    for pattern, want_flags in FLAG_SELFTEST:
        got = [token for _, token in scan_pattern(pattern)[2]]
        if got != want_flags:
            fail(
                "checks/lint.py scan_pattern",
                f"flag self-test failed on {pattern!r}: refused {got!r} (want {want_flags!r})",
                "    RULE: the flag scanner enforces the case declaration (vfm-8k1). A scanner\n"
                "    that is wrong reports green over a broken table, so it is checked against\n"
                "    hand-computed answers every time the gate runs.",
            )
    for pattern, want_anchors, want_alts in SCANNER_SELFTEST:
        anchors, alternations, _ = scan_pattern(pattern)
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


def source_problems(source):
    """Why a `source` value breaks the entry grammar, as a list of messages (empty = clean)."""
    if not source.strip():
        return ["source is empty; every row records where its label was observed"]
    problems, runs = [], set()
    for entry in source.split(LIST_DELIMITER):
        m = SOURCE_ENTRY.fullmatch(entry)
        if not m:
            problems.append(
                f"source entry {entry!r} is not <producer>:<run>[;key=count...]"
            )
            continue
        keys = [pair.split("=")[0] for pair in m["counts"].split(";")[1:]]
        if len(keys) != len(set(keys)):
            problems.append(f"source entry {entry!r} repeats a count key")
        run = (m["producer"], m["run"])
        if run in runs:
            problems.append(f"source names run {':'.join(run)!r} twice")
        runs.add(run)
    return problems


def label_row_problems(row):
    """What is wrong with one vocabulary_labels row, as [(column, message)] (empty = clean)."""
    problems = [("source", msg) for msg in source_problems(row["source"])]
    status = row["status"]
    if status not in LABEL_STATUSES:
        # The other columns are judged RELATIVE to status; against an unknown one they would only
        # repeat this complaint.
        problems.append(
            ("status", f"status {status!r} is not one of {sorted(LABEL_STATUSES)!r}")
        )
        return problems

    vid = row["vocabulary_id"].strip()
    if (status == "mapped") != bool(vid):
        problems.append(
            (
                "vocabulary_id",
                f"status {status!r} with vocabulary_id {vid!r}: vocabulary_id is filled "
                "IFF status is mapped",
            )
        )

    candidates = row["candidates"]
    if status != "needs_context":
        if candidates.strip():
            problems.append(
                (
                    "candidates",
                    f"status {status!r} with candidates {candidates!r}: candidates is "
                    "filled IFF status is needs_context",
                )
            )
        return problems
    ids = candidates.split(LIST_DELIMITER)
    if any(not i or i != i.strip() for i in ids):
        problems.append(
            ("candidates", f"candidates {candidates!r} has an empty or padded id")
        )
    elif len(ids) != len(set(ids)):
        problems.append(("candidates", f"candidates {candidates!r} repeats an id"))
    elif len(ids) < 2:
        problems.append(
            (
                "candidates",
                f"candidates {candidates!r} names fewer than 2 ids -- one id is a mapping",
            )
        )
    return problems


# Hand-built rows with hand-computed answers, checked every run: these checks decide whether a
# consumer can branch on a row, so they get the scanner's treatment.
# (vocabulary_id, candidates, status, source, the columns that must be flagged)
_OK_SOURCE = "litmine:pilot-2026-07;sets=117;papers=10"
LABEL_SELFTEST = [
    ("ICD10CM", "", "mapped", _OK_SOURCE, []),
    ("", "", "unsupported", _OK_SOURCE, []),
    ("", "", "multi_vocabulary", _OK_SOURCE, []),
    ("", "ICD10CM|ICD10", "needs_context", _OK_SOURCE, []),
    ("", "", "unseen", _OK_SOURCE, ["status"]),  # no row for the unadjudicated, ever
    ("ICD10CM", "", "Mapped", _OK_SOURCE, ["status"]),  # the set is case-sensitive
    ("", "", "mapped", _OK_SOURCE, ["vocabulary_id"]),
    ("ICD10", "", "unsupported", _OK_SOURCE, ["vocabulary_id"]),
    ("ICD10", "ICD10CM|ICD10", "needs_context", _OK_SOURCE, ["vocabulary_id"]),
    ("", "", "needs_context", _OK_SOURCE, ["candidates"]),
    ("", "ICD10", "needs_context", _OK_SOURCE, ["candidates"]),  # one id is a mapping
    ("", "ICD10|ICD10CM|ICD10", "needs_context", _OK_SOURCE, ["candidates"]),
    ("", "ICD10||ICD10CM", "needs_context", _OK_SOURCE, ["candidates"]),
    ("", "ICD10| ICD10CM", "needs_context", _OK_SOURCE, ["candidates"]),
    ("", "ICD9CM|ICD10CM", "multi_vocabulary", _OK_SOURCE, ["candidates"]),  # vfm-bmg
    ("ICD10CM", "ICD10CM|ICD10", "mapped", _OK_SOURCE, ["candidates"]),
    ("ICD10CM", "", "mapped", "", ["source"]),
    ("ICD10CM", "", "mapped", "litmine pilot 2026-07", ["source"]),
    ("ICD10CM", "", "mapped", "litmine:pilot;sets=many", ["source"]),
    ("ICD10CM", "", "mapped", "litmine:pilot;sets=1;sets=2", ["source"]),
    ("ICD10CM", "", "mapped", "litmine:pilot;sets=1|litmine:pilot;sets=2", ["source"]),
    ("ICD10CM", "", "mapped", _OK_SOURCE + "|", ["source"]),
    ("ICD10CM", "", "mapped", _OK_SOURCE + ",code_collector:h1", ["source"]),
    (
        "ICD10CM",
        "",
        "mapped",
        "code_collector:vocabulary_labels.py@1a2b3c4|"
        "code_collector:harvest-2026-09-10;sets=267;papers=84",
        [],
    ),
]


def selftest_labels():
    for vid, candidates, status, source, want in LABEL_SELFTEST:
        row = {
            "label": "selftest",
            "vocabulary_id": vid,
            "candidates": candidates,
            "status": status,
            "source": source,
            "notes": "",
        }
        got = sorted(column for column, _ in label_row_problems(row))
        if got != sorted(want):
            fail(
                "checks/lint.py label_row_problems",
                f"self-test failed on vocabulary_id={vid!r} candidates={candidates!r} "
                f"status={status!r} source={source!r}: flagged {got!r}, want {sorted(want)!r}",
                "    RULE: these checks decide whether a registry row is one a consumer can\n"
                "    branch on. Checks that are wrong report green over a broken table, so they\n"
                "    are checked against hand-computed answers every time the gate runs.",
            )


# THE LABEL FOLD (ruled 2026-09-30, vocabulary_formats-7j0). The README states it as a contract and
# codesistant's resolve_label() implements it exactly, so the two must not drift:
#   1. dashes made UNIFORM, never removed: Unicode category Pd, plus U+2212 MINUS SIGN, -> '-'.
#      U+00AD SOFT HYPHEN is deliberately NOT a dash (an invisible line-break hint; turning it into
#      '-' would invent a dash the author never printed). It is left exactly as it is.
#   2. whitespace (the Unicode White_Space property: the 25 code points in WHITE_SPACE below, so
#      NBSP counts) collapses to one space, the ends are trimmed, and whitespace ADJACENT TO A DASH
#      is dropped. Spaces elsewhere stay: 'ICD 10 CM' != 'ICD-10-CM' != 'ICD10CM'. Stripping dashes
#      and spaces entirely was REJECTED. NOT str.isspace() and NOT regex \s, which add U+001C-U+001F
#      (the ASCII file/group/record/unit separators) by bidi class; Ruby has no such predicate, so
#      the contract names a set both languages can enumerate (vocabulary_formats-ssu, 2026-09-30).
#   3. case is ignored (str.casefold).
EXTRA_DASHES = {"−"}  # MINUS SIGN is category Sm, but authors print it as a dash
# The Unicode White_Space property, written out: every character the fold treats as whitespace.
# Checked against the `regex` module's \p{White_Space} and Ruby's /\p{White_Space}/ (both 25).
WHITE_SPACE = frozenset(
    [chr(c) for c in range(0x0009, 0x000D + 1)]  # TAB, LF, VT, FF, CR
    + ["\u0020", "\u0085", "\u00a0", "\u1680"]  # SPACE, NEL, NBSP, OGHAM SPACE MARK
    + [chr(c) for c in range(0x2000, 0x200A + 1)]  # EN QUAD .. HAIR SPACE
    + ["\u2028", "\u2029", "\u202f", "\u205f", "\u3000"]  # LS PS NNBSP MMSP IDEO.
)
# Only ever sees ' ': every WHITE_SPACE character is mapped to it first.
_SPACE_RUN = re.compile(" +")
_SPACE_AT_DASH = re.compile(r" ?- ?")


def fold_label(label):
    """A label as every registry lookup compares it. See THE LABEL FOLD above."""
    s = "".join(
        "-"
        if unicodedata.category(c) == "Pd" or c in EXTRA_DASHES
        else " "
        if c in WHITE_SPACE
        else c
        for c in label
    )
    # strip(" "), never bare strip(): that trims by str.isspace(), U+001C-U+001F included
    s = _SPACE_RUN.sub(" ", s).strip(" ")
    return _SPACE_AT_DASH.sub("-", s).casefold()


# Hand-built inputs with hand-computed answers: (label, what it must fold to).
FOLD_SELFTEST = [
    ("ICD-10-CM", "icd-10-cm"),
    ("icd-10-cm", "icd-10-cm"),
    ("ICD‐10", "icd-10"),  # U+2010 HYPHEN (Pd)
    ("ICD‑10", "icd-10"),  # U+2011 NON-BREAKING HYPHEN (Pd)
    ("ICD–10", "icd-10"),  # U+2013 EN DASH (Pd)
    ("ICD—10", "icd-10"),  # U+2014 EM DASH (Pd)
    ("ICD−10", "icd-10"),  # U+2212 MINUS SIGN (Sm): in the dash set by ruling
    ("ICD­10", "icd­10"),  # U+00AD SOFT HYPHEN: NOT a dash, and not removed
    ("ICD - 10", "icd-10"),  # whitespace adjacent to a dash is dropped
    ("ICD – 10 ‑ CM", "icd-10-cm"),
    ("ICD 10 CM", "icd 10 cm"),  # NBSP is whitespace
    ("  ICD \t 10   CM ", "icd 10 cm"),  # runs collapse, ends trimmed
    ("ICD 10 CM", "icd 10 cm"),  # spaces NOT beside a dash stay ...
    ("ICD10CM", "icd10cm"),  # ... and nothing is inserted or removed
    ("CPT/HCPCS", "cpt/hcpcs"),  # a slash is not a dash
    ("-ICD-", "-icd-"),  # a dash is never removed, even at an end
    # whitespace is the Unicode White_Space property, NOT str.isspace() (vocabulary_formats-ssu)
    ("ICD\u300010", "icd 10"),  # U+3000 IDEOGRAPHIC SPACE is White_Space
    ("ICD\u008510", "icd 10"),  # U+0085 NEXT LINE is White_Space
    ("\u3000ICD \u2013\u0085 10\u0085", "icd-10"),  # trimmed; dropped beside a dash
    ("ICD\u001f10", "icd\u001f10"),  # U+001F UNIT SEPARATOR is NOT (isspace says yes)
    ("ICD\u001c\u001d\u001e10", "icd\u001c\u001d\u001e10"),  # nor are U+001C-U+001E
    ("\u001fICD\u001f", "\u001ficd\u001f"),  # and the ends are not trimmed of them
    ("ICD \u001f 10", "icd \u001f 10"),  # a separator does not join a whitespace run
]

# Hand-built label columns, and the collisions label_collisions must report for each as
# (line, line of the earlier label it folds onto). Lines count from 2, as in the file.
UNIQUE_SELFTEST = [
    (["ICD-10-CM", "ICD 10 CM", "ICD10CM"], []),  # Ryan: three different labels
    (["ICD-10", "icd-10"], [(3, 2)]),
    (["ICD-10", "ICD‐10"], [(3, 2)]),
    (["ICD-10", "ICD − 10"], [(3, 2)]),
    (["ICD 10 CM", "ICD 10  CM "], [(3, 2)]),
    (["ICD-10", "ICD­10", "ICD10"], []),  # soft hyphen: neither a dash nor nothing
    (["SNOMED", "LOINC", "Snomed", "SNOMED"], [(4, 2), (5, 2)]),
    # White_Space folds together; U+001F does not
    (["ICD 10", "ICD\u300010", "ICD\u001f10"], [(3, 2)]),
]


def label_collisions(labels):
    """[(line, earlier_line, folded)] for each label folding onto an earlier one. Lines from 2."""
    seen, out = {}, []
    for lineno, label in enumerate(labels, start=2):
        key = fold_label(label)
        if key in seen:
            out.append((lineno, seen[key], key))
        else:
            seen[key] = lineno
    return out


def selftest_fold():
    rule = (
        "    RULE: the label fold is a published contract (README) that a consumer in another\n"
        "    language re-implements. A fold that is wrong here lets two rows answer one lookup,\n"
        "    so it is checked against hand-computed answers every time the gate runs."
    )
    if len(WHITE_SPACE) != 25:
        fail(
            "checks/lint.py WHITE_SPACE",
            f"has {len(WHITE_SPACE)} code points, want the 25 of Unicode White_Space",
            rule,
        )
    for label, want in FOLD_SELFTEST:
        got = fold_label(label)
        if got != want:
            fail(
                "checks/lint.py fold_label",
                f"self-test failed on {label!r}: folded to {got!r}, want {want!r}",
                rule,
            )
    for labels, want in UNIQUE_SELFTEST:
        got = [(line, earlier) for line, earlier, _ in label_collisions(labels)]
        if got != want:
            fail(
                "checks/lint.py label_collisions",
                f"self-test failed on {labels!r}: collisions {got!r}, want {want!r}",
                rule,
            )


LABEL_FOLD_RULE = """
    RULE: `label` is the lookup key, and every lookup compares labels AFTER THE LABEL FOLD
    (README): dashes made uniform, whitespace collapsed and dropped beside a dash, case ignored.
    Two rows that fold together are one key with two answers, and which one a consumer gets
    depends on how it loads the file. Keep one row per spelling the fold keeps distinct; for a
    variant the fold already covers, append a `source` entry to the existing row instead.
"""


def check_labels_unique(rows):
    labels = [row["label"] for _, row in rows]
    for index, earlier, key in label_collisions(labels):
        lineno, row = rows[index - 2]
        earlier_lineno, earlier_row = rows[earlier - 2]
        fail(
            f"{LABELS.name}:{lineno} {row['label']!r}",
            f"folds to {key!r}, the same as {earlier_row['label']!r} on line {earlier_lineno}",
            LABEL_FOLD_RULE,
        )


def check_labels(rows):
    for lineno, row in rows:
        for column, message in label_row_problems(row):
            fail(
                f"{LABELS.name}:{lineno} {row['label']!r}",
                message,
                SOURCE_RULE if column == "source" else LABEL_RULE,
            )


# vocabulary_composition.tsv (vocabulary_formats-909): one row per (hybrid, source vocabulary) pair.
COMPOSITION_KEY = ("vocabulary_id", "source_vocabulary_id")

COMPOSITION_RULE = """
    RULE: vocabulary_composition states each (vocabulary_id, source_vocabulary_id) pair ONCE. An
    edition lookup fans out over a hybrid's rows, so a repeated pair returns that source's editions
    twice, and two rows disagreeing in `notes` leave a consumer to guess which evidence stands.
    Delete the duplicate; put anything it added in the surviving row's notes.
"""

# Hand-built pair columns, and the duplicates composition_duplicates must report for each as
# (line, line of the earlier identical pair). Lines count from 2, as in the file. Ids are compared
# EXACTLY: vocabulary_ids are case-sensitive keys, and `just test` catches an id that names nothing.
COMPOSITION_SELFTEST = [
    ([("CPT4_HCPCS", "CPT4"), ("CPT4_HCPCS", "HCPCS")], []),  # the table as ruled
    ([("CPT4_HCPCS", "CPT4"), ("CPT4_HCPCS", "CPT4")], [(3, 2)]),  # the rule's target
    (
        [("CPT4_HCPCS", "CPT4"), ("CPT4_HCPCS", "HCPCS"), ("CPT4_HCPCS", "CPT4")],
        [(4, 2)],
    ),
    ([("A_B", "A"), ("C_A", "A")], []),  # one source feeding two hybrids is fine
    ([("CPT4_HCPCS", "CPT4"), ("CPT4_HCPCS", "cpt4")], []),  # exact: case not folded
    ([("CPT4_HCPCS", "CPT4"), ("CPT4", "CPT4_HCPCS")], []),  # the pair is ordered
    ([("X", "Y"), ("X", "Y"), ("X", "Y")], [(3, 2), (4, 2)]),
]


def composition_duplicates(pairs):
    """[(line, earlier_line)] for each pair repeating an earlier one. Lines from 2."""
    seen, out = {}, []
    for lineno, pair in enumerate(pairs, start=2):
        if pair in seen:
            out.append((lineno, seen[pair]))
        else:
            seen[pair] = lineno
    return out


def selftest_composition():
    for pairs, want in COMPOSITION_SELFTEST:
        got = composition_duplicates(pairs)
        if got != want:
            fail(
                "checks/lint.py composition_duplicates",
                f"self-test failed on {pairs!r}: duplicates {got!r}, want {want!r}",
                "    RULE: the pair check decides whether an edition lookup fans out once per\n"
                "    source. A check that is wrong reports green over a broken table, so it is\n"
                "    checked against hand-computed answers every time the gate runs.",
            )


def check_composition_unique(rows):
    pairs = [tuple(row[k] for k in COMPOSITION_KEY) for _, row in rows]
    for index, earlier in composition_duplicates(pairs):
        lineno, row = rows[index - 2]
        earlier_lineno, _ = rows[earlier - 2]
        fail(
            f"{COMPOSITION.name}:{lineno}",
            f"duplicate pair ({row['vocabulary_id']!r}, {row['source_vocabulary_id']!r}) "
            f"(first seen on line {earlier_lineno})",
            COMPOSITION_RULE,
        )


def read_table(path, columns):
    """Parse a TSV by hand -- no csv module, no duckdb. Checks tabs, columns, and returns rows."""
    text = path.read_bytes().decode("utf-8")
    if "\r" in text:
        fail(
            path.name, "contains CR characters; the file must use bare LF line endings"
        )
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

        anchors, alternations, bad_flags = scan_pattern(pattern)
        for offset, token in bad_flags:
            fail(
                f"{FORMATS.name}:{lineno} {vid}",
                f"regexp contains the INLINE FLAG {token!r} at offset {offset}: {pattern}",
                FLAG_RULE,
            )
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
    for tsv in TABLES:
        parquet = tsv.with_suffix(".parquet")
        if tsv in malformed:
            print(
                f"  {parquet.name}: not compared -- {tsv.name} did not survive the checks above"
            )
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
            fail(
                parquet.name,
                f"columns are {pq_cols!r}, TSV has {tsv_cols!r}",
                PARQUET_RULE,
            )
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
            fail(
                f"{TARGETS.name} {vid}",
                f"names unknown source {target.get('source')!r}",
            )
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
                fail(
                    f"{TARGETS.name} {vid}",
                    f"code_filter.pattern does not compile -- {exc}",
                )
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
    print(
        f"  scan_pattern self-test: {len(SCANNER_SELFTEST)} hand-built patterns, "
        f"{len(FLAG_SELFTEST)} hand-built inline-flag patterns"
    )
    selftest_labels()
    print(f"  label_row_problems self-test: {len(LABEL_SELFTEST)} hand-built rows")
    selftest_fold()
    print(
        f"  fold_label self-test: {len(FOLD_SELFTEST)} hand-built labels, "
        f"{len(UNIQUE_SELFTEST)} hand-built label columns"
    )
    selftest_composition()
    print(
        f"  composition_duplicates self-test: {len(COMPOSITION_SELFTEST)} "
        "hand-built pair columns"
    )
    malformed = set()
    rows_by_table = {}
    for path in TABLES:
        before = len(failures)
        rows_by_table[path] = read_table(path, TABLES[path])
        if len(failures) > before:
            malformed.add(path)
        print(
            f"  {path.name}: {len(rows_by_table[path])} rows, {len(TABLES[path])} columns"
        )
    formats_rows, labels_rows = rows_by_table[FORMATS], rows_by_table[LABELS]

    compiled = check_regexps(formats_rows)
    print(f"  regexps that compile as \\A(?:...)\\z: {compiled}/{len(formats_rows)}")
    check_unique(formats_rows, "vocabulary_id", FORMATS.name)
    check_labels_unique(
        labels_rows
    )  # after the fold, which implies byte-for-byte unique
    check_labels(labels_rows)
    check_composition_unique(rows_by_table[COMPOSITION])
    check_parquet_in_sync(malformed)
    check_targets(formats_rows)

    if not failures:
        print(
            "\nOK: no anchors, no top-level alternation, no inline flag but (?i:...),\n    unique keys, parquet in sync,"
        )
        print("    every row's validation target declared, every label row consistent,")
        print(
            "    every label unique after the label fold, every composition pair unique."
        )
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
