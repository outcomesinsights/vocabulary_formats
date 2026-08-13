"""Per-row PROSE-ADVERSARY score: every row, against ordinary running text.

`just prose`. The other half of the question `just test` answers. The harness in false_negatives.py
asks "does this row reject a real code?" (completeness). This one asks "what ELSE does it accept?"
-- and it asks it against ordinary English, not against sibling vocabularies.

WHY THE DISTINCTION IS NOT ACADEMIC (vocabulary_formats-wir, seed vfm-311). Until 2026-08-12 every
false-positive number in this repo was scored across vocabularies: "how many ICD9CM codes does the
ICD10CM row accept?" Narrowing ICD10CM's position 2 from \\w to (digit | QA) removed exactly ZERO
cross-vocabulary false positives -- 1,357 either way, because V## and E### are already letter+digit
-- so that number said "do not bother". Scored against the FY2026 tabular it removed 426 distinct
word-tokens: ABC, ALL, ARE, Age, Air, AST. These regexps are used to FIND codes in text; ordinary
prose is the adversary the cross-vocabulary number cannot see.

THIS IS A REPORT, NOT A GATE. It never fails a run and `just lint` does not call it. There is no
threshold to be under: a row that admits half the dictionary may be perfectly honest (every
two-character string IS a valid HCPCS modifier), and the correct response there is a note saying the
row cannot carry its own weight alone -- not a narrowing that costs a real code. Rule 2's ordering
stands: COMPLETE first, then narrow, and permissiveness breaks ties.

USE IT BEFORE AND AFTER. Each narrowing needs its own before/after pair, which is what `--try` is
for -- score a candidate beside the row it would replace without touching the table:

    just prose --try 'ICD10=[A-Za-z][0-9][0-9A-Za-z](\\.\\w{1,4})?'

Then re-run `just test`: a narrowing that costs even one in-target code is a bug, not a trade.
"""

import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

from false_negatives import bound, load_rows  # noqa: E402  (path set above)

ROOT = Path(__file__).resolve().parent.parent

EXAMPLES = 10  # sample tokens printed per row, per corpus

# Corpora, as data. Both are large local artifacts that not every machine has; a missing one SKIPS,
# exactly as a missing concept substrate does in false_negatives.py.
CORPORA = {
    "tabular": {
        "kind": "duckdb",
        "default_path": (
            "/home/ryan/projects/outins/one_offs/icd10cm/data/processed/"
            "icd10cm_supplemental_2026.duckdb"
        ),
        "env": "VOCABULARY_FORMATS_TABULAR_DUCKDB",
        "queries": [
            "SELECT note_text FROM notes",
            "SELECT description FROM codes",
        ],
        "what": (
            "FY2026 ICD-10-CM tabular: 25,160 Includes/Excludes notes + 46,881 code descriptions. "
            "CLINICAL prose -- disease names, anatomy, the language a code description is written "
            "in. Built by one_offs/icd10cm; this is the corpus the 2026-08-12 ICD10CM narrowing "
            "was measured against, so numbers here are comparable to that note."
        ),
    },
    "papers": {
        "kind": "nxml_dir",
        "default_path": "/home/ryan/projects/outins/litmine/papers",
        "env": "VOCABULARY_FORMATS_PAPERS_DIR",
        "what": (
            "The litmine pilot's 20 PubMed Central articles, as JATS XML. LITERATURE prose -- "
            "methods, tables, statistics, citations, and the code lists papers actually print. "
            "This is the corpus that matters most: litmine is the consumer that runs these "
            "regexps over free text, where a loose row costs more than in claims "
            "canonicalization (there the input is already known to be a code)."
        ),
    },
}

# A token is [0-9A-Za-z.]+ with dots stripped from the ends -- the tokenization the ICD10CM
# measurement used, kept identical so every later number is comparable to the 426 in that note.
TOKEN_RE = re.compile(r"[0-9A-Za-z.]+")


def tokenize(text):
    """Distinct word-tokens of a chunk of text."""
    out = set()
    for raw in TOKEN_RE.findall(text):
        token = raw.strip(".")
        if token:
            out.add(token)
    return out


# The tokenizer decides every number this tool prints, so it is checked against hand-computed
# answers on every run -- the same discipline lint.py's scan_pattern self-test follows.
TOKENIZER_SELFTEST = [
    ("Age 10-24 years", {"Age", "10", "24", "years"}),
    ("Excludes1: diabetes (E11.-)", {"Excludes1", "diabetes", "E11"}),
    ("code A15-A19 first", {"code", "A15", "A19", "first"}),
    ("8140/3 histology", {"8140", "3", "histology"}),
    ("...", set()),  # dots alone are not a token
    ("p=.05, n=1,204", {"p", "05", "n", "1", "204"}),  # commas split, a leading dot is stripped
    ("O.R. 1.5", {"O.R", "1.5"}),  # an interior dot stays -- E11.9 must survive tokenization
    ("under_score", {"under", "score"}),  # '_' is not in the token alphabet, unlike \\w
]


def selftest_tokenizer():
    bad = []
    for text, want in TOKENIZER_SELFTEST:
        got = tokenize(text)
        if got != want:
            bad.append(f"    {text!r}: got {sorted(got)!r}, want {sorted(want)!r}")
    if bad:
        print("TOKENIZER SELF-TEST FAILED -- every count below would be wrong:")
        print("\n".join(bad))
        sys.exit(2)


def resolve(name, spec):
    path = Path(os.environ.get(spec["env"], spec["default_path"]))
    return {"name": name, "path": path, "spec": spec, "available": path.exists()}


def load_corpus(source):
    """Distinct tokens of one corpus, plus how much text it came from."""
    spec = source["spec"]
    tokens, chunks = set(), 0
    if spec["kind"] == "duckdb":
        import duckdb

        con = duckdb.connect(str(source["path"]), read_only=True)
        for query in spec["queries"]:
            for (text,) in con.execute(query).fetchall():
                if text:
                    chunks += 1
                    tokens |= tokenize(text)
        con.close()
        return tokens, f"{chunks:,} text fields"

    for xml in sorted(source["path"].rglob("*.nxml")):
        chunks += 1
        # itertext() walks the article body as rendered, so tags do not become tokens.
        tokens |= tokenize(" ".join(ElementTree.parse(xml).getroot().itertext()))
    return tokens, f"{chunks:,} articles"


def shape(token):
    """letters / digits / mixed -- the decomposition that says WHICH hazard a row has."""
    if token.isalpha():
        return "letters"
    if token.isdigit():
        return "digits"
    return "mixed"


def score(pattern, tokens):
    rx = re.compile(bound(pattern))
    hits = sorted(t for t in tokens if rx.match(t))
    counts = {"letters": 0, "digits": 0, "mixed": 0}
    for token in hits:
        counts[shape(token)] += 1
    return hits, counts


def samples(hits):
    """A spread of what got in, alphabetic tokens FIRST -- they are the damning ones."""
    words = [t for t in hits if t.isalpha()]
    rest = [t for t in hits if not t.isalpha()]
    picked = words[:EXAMPLES] if words else rest[:EXAMPLES]
    if words and len(picked) < EXAMPLES:
        picked += rest[: EXAMPLES - len(picked)]
    return picked


def main(argv):
    selftest_tokenizer()
    regexps, order = load_rows()

    extra = []
    for arg in argv:
        if arg == "--try":  # the flag is a marker; the candidate rides in the next argument
            continue
        if "=" not in arg:
            print(f"unrecognised argument {arg!r}; use --try 'LABEL=REGEXP'")
            return 2
        label, _, pattern = arg.partition("=")
        try:
            re.compile(bound(pattern))
        except re.error as exc:
            print(f"--try {label}: candidate does not compile -- {exc}")
            return 2
        extra.append((f"try {label.strip()}", pattern))

    print("prose-adversary score -- every row against ordinary running text")
    corpora = {}
    for name, spec in CORPORA.items():
        source = resolve(name, spec)
        state = "available" if source["available"] else "UNAVAILABLE (not on this machine)"
        print(f"  corpus {name}: {source['path']} -- {state}")
        if source["available"]:
            corpora[name] = source

    if not corpora:
        print(
            "\nSKIPPED: no text corpus on this machine, so there is nothing to score the rows\n"
            "         against. This is a report, not a gate -- `just lint` and `just test` are\n"
            "         unaffected. Point one of these at a corpus and re-run:\n"
            + "".join(f"           {s['env']}={s['default_path']}\n" for s in CORPORA.values())
        )
        return 0

    loaded = {}
    for name, source in corpora.items():
        tokens, provenance = load_corpus(source)
        loaded[name] = tokens
        print(f"  {name}: {len(tokens):,} distinct tokens from {provenance}")

    scored = [(vid, regexps[vid]) for vid in order] + extra
    names = list(loaded)
    header = "  " + f"{'row':<28}" + "".join(f"{n:>34}" for n in names)
    print("\n" + header)
    print("  " + " " * 28 + "".join(f"{'tokens   (letters/digits/mixed)':>34}" for _ in names))
    for vid, pattern in scored:
        cells = ""
        for name in names:
            hits, counts = score(pattern, loaded[name])
            cells += (
                f"{len(hits):>12,}"
                f"   ({counts['letters']:>6,}/{counts['digits']:>6,}/{counts['mixed']:>5,})"
            )
        print(f"  {vid:<28}{cells}")

    print("\nWHAT EACH ROW ADMITS (alphabetic tokens first -- those are the ordinary words):")
    for vid, pattern in scored:
        print(f"\n  {vid}   {pattern}")
        for name in names:
            hits, counts = score(pattern, loaded[name])
            if not hits:
                print(f"    {name:<9} admits nothing in this corpus")
                continue
            share = 100.0 * len(hits) / len(loaded[name])
            print(
                f"    {name:<9} {len(hits):>6,} of {len(loaded[name]):,} tokens ({share:5.1f}%), "
                f"{counts['letters']:,} of them ordinary words: {', '.join(samples(hits))}"
            )

    print(
        "\nA high number is a FINDING, not a failure. Before narrowing anything, re-read rule 2:\n"
        "complete first, then narrow, and permissiveness breaks ties. Then run `just test` --\n"
        "a narrowing that costs one in-target code is a bug, whatever it bought here."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
