"""Per-row FALSE-NEGATIVE harness: every row, scored against its OWN declared target.

`just test`. This is the half of the trellis the repo did not have -- until 2026-08-13 each row's
validation existed only as prose in the notes column ("Validated 2026-07-27 vs 100,035
concept_codes: 0 FN") and nothing re-ran it. A format is an enumeration of what a code can look
like, and an enumeration is only as current as the line holding it.

WHAT IT ASSERTS. For each row, pull the concept_codes of its declared target from the OHDSI
substrate and require that EVERY ONE of them matches the row's regexp, bound the way a caller binds
it: \\A(?:pattern)\\z. A code in target that does not match is a false negative and fails the run.

RULE 1 SCOPES RULE 2. The target is the row's own, never the whole vocabulary: a 9-digit NDC failing
the claims-default NDC row is CORRECT, and the same code failing NDC.COMPLETE is a bug. The targets,
and every deliberate exclusion, are declared as data in checks/validation_targets.json -- read that
file to see what a row is being held to, and edit it (not this script) when a target changes.

SUBSTRATE. Two sources, both optional, both skippable:
  athena  the stock Athena CONCEPT.csv    (env VOCABULARY_FORMATS_ATHENA_CSV)
  oi      vocabulation's built duckdb     (env VOCABULARY_FORMATS_OI_DUCKDB)
The OI-minted vocabularies (CPT4_HCPCS, ICD03_*) exist only in the second. A missing source SKIPS
the rows that need it and never fails the run -- a gate that cannot run on a machine without a
1.4 GB vocabulary download is a gate nobody keeps.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMATS = ROOT / "vocabulary_formats.tsv"
TARGETS = Path(__file__).resolve().parent / "validation_targets.json"

FN_EXAMPLES = 8  # how many false negatives to print per row before truncating

TRANSFORMS = {
    "strip_dots": lambda code: code.replace(".", ""),
    "strip_leading_zeros": lambda code: code.lstrip("0") or "0",
    "strip_behavior_suffix": lambda code: re.sub(r"/\d\Z", "", code),
}


def bound(pattern):
    r"""The pattern as a CALLER binds it: \A(?:pattern)\z.

    This is the whole contract under test. The row carries no boundary of its own, so the harness
    must supply the same one a consumer does -- scoring a row unbound would pass anything with a
    matching substring. Python spells PCRE's \z as \Z.
    """
    return r"\A(?:%s)\Z" % pattern


def load_rows():
    """The regexp of every row in the published TSV, in file order."""
    lines = FORMATS.read_text(encoding="utf-8").rstrip("\n").split("\n")
    header = lines[0].split("\t")
    rows = {}
    order = []
    for line in lines[1:]:
        row = dict(zip(header, line.split("\t")))
        rows[row["vocabulary_id"]] = row["regexp"]
        order.append(row["vocabulary_id"])
    return rows, order


def resolve_sources(declaration):
    """Which substrates are actually on this machine. Absence is a skip, never a failure."""
    resolved = {}
    for name, spec in declaration["sources"].items():
        path = Path(os.environ.get(spec["env"], spec["default_path"]))
        resolved[name] = {
            "path": path,
            "kind": spec["kind"],
            "schema": spec.get("schema"),
            "available": path.exists(),
            "reason": "" if path.exists() else f"not on this machine: {path}",
        }
    return resolved


def connect(sources):
    """One duckdb connection; the file sources are attached, the CSV is read in place."""
    import duckdb

    con = duckdb.connect(":memory:")
    for name, source in sources.items():
        if not source["available"] or source["kind"] != "duckdb":
            continue
        try:
            con.execute(f"ATTACH '{sql_str(source['path'])}' AS {name} (READ_ONLY)")
        except duckdb.Error as exc:  # in use by another process, corrupt, wrong version...
            source["available"] = False
            source["reason"] = f"cannot be opened ({exc.__class__.__name__}: {exc})"
    return con


def sql_str(value):
    return str(value).replace("'", "''")


def relation(source, name):
    """The SQL relation holding CONCEPT for a source."""
    if source["kind"] == "duckdb":
        return f"{name}.{source['schema']}.concept"
    # quote='' / escape='': Athena's CONCEPT.csv is not a quoted CSV -- concept_name carries bare
    # double quotes, and letting duckdb treat them as quoting shifts columns silently.
    return (
        f"read_csv('{sql_str(source['path'])}', delim = '\t', header = true, "
        "quote = '', escape = '', all_varchar = true)"
    )


def in_list(values):
    return ", ".join("'" + sql_str(v) + "'" for v in values)


def fetch_target(con, rel, target):
    """DISTINCT concept_codes of the target, each with an example concept_id."""
    where = [f"vocabulary_id IN ({in_list(target['concept_vocabulary_ids'])})"]
    if target.get("concept_classes"):
        where.append(f"concept_class_id IN ({in_list(target['concept_classes'])})")
    if target.get("valid_only"):
        where.append("invalid_reason IS NULL")
    sql = (
        f"SELECT concept_code, min(concept_id) FROM {rel} "
        f"WHERE {' AND '.join(where)} GROUP BY concept_code"
    )
    return con.execute(sql).fetchall()


def fetch_name_prefix_codes(con, rel, target, prefix):
    """concept_codes whose concept_name starts with a prefix -- the placeholder-row exclusions."""
    sql = (
        f"SELECT DISTINCT concept_code FROM {rel} "
        f"WHERE vocabulary_id IN ({in_list(target['concept_vocabulary_ids'])}) "
        f"AND concept_name LIKE '{sql_str(prefix)}%'"
    )
    return {r[0] for r in con.execute(sql).fetchall()}


def score(con, target, regexp, sources):
    """Score one row. Returns a result dict; never raises on a missing substrate."""
    name = target["source"]
    source = sources[name]
    result = {"vocabulary_id": target["vocabulary_id"], "notes": []}
    if not source["available"]:
        result["skipped"] = f"source '{name}' {source['reason']}"
        return result

    rel = relation(source, name)
    rows = fetch_target(con, rel, target)
    result["in_substrate"] = len(rows)
    if not rows:
        result["error"] = (
            f"target matched ZERO concept_codes in source '{name}'. Either the declaration in "
            f"{TARGETS.name} names a vocabulary_id / concept_class_id that does not exist, or the "
            "vocabulary left the release. Both are drift, not a pass."
        )
        return result

    excluded = set()
    for exclusion in target.get("exclusions", []):
        if exclusion.get("name_prefix"):
            hit = fetch_name_prefix_codes(con, rel, target, exclusion["name_prefix"])
            if not hit:
                result["notes"].append(
                    f"exclusion by name_prefix {exclusion['name_prefix']!r} matched nothing"
                )
            excluded |= hit
        else:
            declared = set(exclusion["codes"])
            present = {code for code, _ in rows} & declared
            missing = declared - present
            if missing:
                result["notes"].append(
                    f"declared exclusion(s) {sorted(missing)!r} are not in this source (inert here)"
                )
            excluded |= declared

    kept = [(code, cid) for code, cid in rows if code not in excluded]
    result["excluded"] = len(rows) - len(kept)

    code_filter = target.get("code_filter")
    if code_filter:
        keep = re.compile(bound(code_filter["pattern"]))
        before = len(kept)
        kept = [(code, cid) for code, cid in kept if keep.match(code)]
        result["out_of_target"] = before - len(kept)

    transform = target.get("transform")
    if transform:
        fn = TRANSFORMS[transform]
        kept = [(fn(code), cid) for code, cid in kept]

    # Bound exactly as the contract says a caller binds it.
    rx = re.compile(bound(regexp))
    misses = [(code, cid) for code, cid in kept if not rx.match(code)]
    result["tested"] = len(kept)
    result["false_negatives"] = misses
    return result


def main():
    declaration = json.loads(TARGETS.read_text(encoding="utf-8"))
    regexps, order = load_rows()
    targets = {t["vocabulary_id"]: t for t in declaration["targets"]}
    sources = resolve_sources(declaration)

    print("false-negative harness -- every row against its own declared target")
    print(f"  targets: {TARGETS}")
    for name, source in sources.items():
        state = "available" if source["available"] else f"UNAVAILABLE ({source['reason']})"
        print(f"  source {name}: {source['path']} -- {state}")

    if not any(s["available"] for s in sources.values()):
        print(
            "\nSKIPPED: no OHDSI concept substrate on this machine, so there is nothing to score\n"
            "         false negatives against. This is a skip, not a pass -- the rows are\n"
            "         UNVALIDATED. Point one of these at a substrate and re-run:\n"
            + "".join(
                f"           {declaration['sources'][n]['env']}={declaration['sources'][n]['default_path']}\n"
                for n in sources
            )
            + "         `just lint` is the structural gate and needs no database."
        )
        return 0

    con = connect(sources)
    missing = sorted(set(order) - set(targets))
    if missing:
        print(f"\nERROR: rows with no declared target: {missing} (run `just lint`)")
        return 1

    results = [score(con, targets[vid], regexps[vid], sources) for vid in order]
    con.close()

    print(f"\n  {'row':<28} {'codes tested':>14}  {'FN':>6}")
    for r in results:
        if "skipped" in r:
            print(f"  {r['vocabulary_id']:<28} {'-':>14}  {'SKIP':>6}   {r['skipped']}")
        elif "error" in r:
            print(f"  {r['vocabulary_id']:<28} {'-':>14}  {'ERROR':>6}")
        else:
            fn = len(r["false_negatives"])
            print(f"  {r['vocabulary_id']:<28} {r['tested']:>14,}  {fn:>6}")

    notes = [(r["vocabulary_id"], n) for r in results for n in r.get("notes", [])]
    if notes:
        print("\nNOTES (not failures):")
        for vid, note in notes:
            print(f"  {vid}: {note}")

    errors = [r for r in results if "error" in r]
    offenders = [r for r in results if r.get("false_negatives")]
    if offenders:
        print("\nFALSE NEGATIVES -- codes inside the row's own target that the regexp rejects:")
        for r in offenders:
            vid = r["vocabulary_id"]
            print(f"\n  {vid}  ({len(r['false_negatives'])} of {r['tested']:,} tested)")
            print(f"    regexp: {regexps[vid]}")
            for code, cid in r["false_negatives"][:FN_EXAMPLES]:
                print(f"      {code!r}  (concept {cid})")
            if len(r["false_negatives"]) > FN_EXAMPLES:
                print(f"      ... {len(r['false_negatives']) - FN_EXAMPLES:,} more")
        print(
            "\n  A false negative inside the row's declared target is a BUG in the row, and the\n"
            "  repo's contract is that it never ships. Either the regexp must widen, or the code\n"
            "  is not in target and checks/validation_targets.json must say so WITH EVIDENCE\n"
            "  (concept_id, invalid_reason, concept_class_id). Do not quietly widen the target."
        )
    if errors:
        print("\nDECLARATION DRIFT:")
        for r in errors:
            print(f"  {r['vocabulary_id']}: {r['error']}")

    scored = [r for r in results if "tested" in r]
    skipped = [r for r in results if "skipped" in r]
    print(
        f"\n{len(scored)} of {len(results)} rows scored, "
        f"{sum(r['tested'] for r in scored):,} codes tested, "
        f"{sum(len(r['false_negatives']) for r in scored)} false negatives."
    )
    if skipped:
        print(f"{len(skipped)} row(s) UNVALIDATED for want of a substrate: ")
        for r in skipped:
            print(f"  {r['vocabulary_id']}: {r['skipped']}")
    return 1 if (offenders or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
