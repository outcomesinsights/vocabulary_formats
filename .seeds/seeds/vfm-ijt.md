---
id: vfm-ijt
title: A peer session called this repo's consumer seam undocumented -- it is documented four ways. The gap is REACH, not coverage.
status: captured
type: concern
created_at: 2026-09-14T21:30:07.171407+00:00
updated_at: 2026-09-14T21:33:03.120386+00:00
tags:
  - consumer-contract
  - detector
  - validator
  - readme
  - discoverability
  - cross-repo
  - declined-tripwire
  - 2026-09-14
  - root-caused
  - briefing-drift
---

A peer Claude session (working in habituate; name withheld -- derived session names
collide with seed-ID syntax) asked this repo to add a tripwire line to CLAUDE.md or
README stating that "the rules governing how consumers may and may not use these
tables are NOT documented here", so that an agent reasoning about the seam would feel
a gap and go read a cross-repo briefing.

DECLINED. The premise is false, and the line would have been false in a load-bearing way.

WHAT THE PEER ASSERTED, AND WHAT IS ACTUALLY TRUE (verified 2026-09-14)

"Your regexes are anchored"
Zero of the 38 rows carry an anchor. `just lint` enforces no-anchors as a
structural invariant, and the README devotes a whole section to why
("The patterns carry NO anchors -- the caller supplies the boundary").
The peer's own illustration, ^\\w{3}$ matching "the"/"and"/"NOS", is an
ANCHORED pattern, which lint would reject outright -- and ICD10CM has not
been \\w{3} since 2026-08-27, when position 3 became [0-9ABab] precisely
to stop T2DM / QALY / H2O.

"deliberately PERMISSIVE"
Rule 2 says the opposite: permissiveness is the FLOOR, not the goal. The
2026-08-13 sweep narrowed ten rows (EDI 7,637 prose hits -> 0;
ICD10.DOTLESS 5,565 -> 15; NDC.ALPHANUM 2,899 -> 0), each at 0 in-target
false negatives.

"the consumer seam is invisible from inside a repo with two tables and no code"
It is documented FOUR ways, and one of them is better than prose:
1\. README "The patterns carry NO anchors" -- 18 lines, a per-language
binding table (Ruby \\A..\\z not ^..$; Python fullmatch; R stringr is
ICU not PCRE; DuckDB regexp_full_match), and the exact detection
recipe (?\<![0-9A-Za-z])(?:PATTERN)(?![0-9A-Za-z]).
2\. The `use` COLUMN -- the containment rule encoded as DATA, not prose.
Closed set, assigned BY MEASUREMENT at 2 hits per 10k characters over
2,020,962 characters of real article text. 21 rows validator,detector;
17 validator-only.
3\. README "A validator and a detector want opposite things" -- names the
exact case the peer was worried about, and resolves it the peer's way:
detector-only SIBLINGS (ICD10PCS.BILLABLE, CPT4_HCPCS.CODEONLY) rather
than narrowing a default. Plus "Validator-only is a legitimate
permanent answer" for hierarchy tops (A in ATC, 79 in CPT, 250 in ICD-9).
4\. CLAUDE.md Tech Stack / Relationships -- data-only, checks/ is internal,
located by VOCABULARY_FORMATS_DIR and never by a sibling path.
Also already a seed: vfm-6x1, the 2M-character validator/detector census.

Every rule the peer enumerated is already stated here. The `use` column was
added 2026-08-26 (vocabulary_formats-5i7) for exactly the reason the peer gives:
code_collector had measured it itself, and the next consumer would have repeated
the measurement.

WHY THE PROPOSED LINE WOULD HAVE BEEN ACTIVE HARM

A tripwire manufactures a felt gap so an agent goes looking. Pointed at a seam
that IS covered, it does the reverse of its purpose: it asserts absence where
there is presence, and routes an agent AWAY from the README section and the
`use` column that answer the question precisely -- toward a briefing that, on
this subject, knows less. A false "not documented here" is worse than silence,
because an agent that trusts it stops reading.

THE FINDING WORTH KEEPING -- THE INVERSE OF THE ASK

A peer session reasoned confidently about this repo's seam, in enough detail to
propose a remedy, while holding three specific beliefs the README refutes inside
its first 120 lines. It never opened the README. That is a REACH problem, not a
coverage problem, and it is the second instance: code_collector bound all 37 rows
over 2M characters to derive what the `use` column now states as data.

The hypothesis to test, NOT decided here: agents form a model of this repo from
its auto-loaded CLAUDE.md and from what sibling repos say about it, and never
read README.md -- because CLAUDE.md loads by walk-up and feels complete, while
README is a file you must choose to open. CLAUDE.md is the EDITOR's doc (the two
rules, the gate, the substrates); README is the CONSUMER contract (what you may
rely on, what changes under you, how to bind a pattern, what `use` and `context`
mean). An editing agent gets the editor's doc for free and the consumer's doc
never.

If that is right, the fix is the opposite shape from the ask: not a line saying
knowledge is elsewhere, but a line in CLAUDE.md saying the consumer contract
lives in README.md, and that an agent reasoning about a CONSUMER's obligations
must open it. Cheap, in-repo, no sibling path, and it points at something true.

Wants evidence before acting. Two instances is not a pattern, and a pointer line
is itself a thing that can go stale and still be trusted.

PROVENANCE
The peer's underlying incident was real but in a DIFFERENT repo -- a sibling
producer, LOINC answer lists, a session proposing a new concept_id_2 coverage
check when supplemental sidecars are already resolve-or-drop by INNER JOIN under
a strict FK to CONCEPT. Nothing to do with these tables; the peer generalised
from it to the whole group. Recorded because the generalisation is the
interesting part, not the incident.

=== ROOT-CAUSED 2026-09-14, same day. The hypothesis is no longer untested. ===

The peer verified all three corrections independently rather than taking them on my
word (including the nice catch that the four rows matching ^ or $ match in the NOTES
column, as prose about history -- CPT4's "WIDENED 2026-07-27 from ^\\d{4}\\w$" -- while
the regexp column is 0), accepted the decline, and traced where its false premises
came from. They were not its invention.

THE SOURCE: habituate's briefings/vocabulary.md rule 9 says verbatim "Its regexes are
**anchored and permissive**" and uses ^\\w{3}$ as its illustration. The peer restated
the briefing as established fact. The briefing is wrong. Filed there as habituate-yqy.

IT WAS TRUE FOR EXACTLY ONE DAY. Rule 9 cites its settling in vfm-ges, 2026-08-12:

```
  2026-08-13  the narrowing sweep (vocabulary_formats-wir), ten rows
  2026-08-26  the `use` column (vocabulary_formats-5i7)
  2026-08-27  ICD10CM position 3 -> [0-9ABab]
```

All after. Wrong for 33 days with nothing flagging it: `habituate doctor` checks that
repos exist, briefings are reachable and the symlink resolves -- all structural. It
cannot check whether a briefing's CLAIMS still hold.

REACH IS NOW MEASURED, NOT HYPOTHESIZED, and worse than I guessed. The peer sent that
stale framing to SIX repos in one day as fact. FIVE accepted it. The one that did not
was this one, and only because the README was opened. A stale briefing does not sit
inert -- it launders into other repos' deliberation at the speed of dispatch, and each
acceptance makes it look better corroborated.

THIRD DATA POINT for the CLAUDE.md-vs-README hypothesis, and the peer volunteered
itself as such: it reasoned about this seam in enough detail to propose a remedy
without opening README.md. Two of the three data points are agents that had the answer
one file away. Carried into habituate-yqy as worth more than the tripwire was.

THE SHARPER FINDING, which supersedes the pointer-line idea as the thing to act on:

A briefing that PROSE-RESTATES what the `use` column holds as checked data is a
second source of truth, and the second one drifts. The column is regenerated from
measurement (2 hits/10k chars over 2,020,962 characters) and cannot silently go
stale; rule 9's sentence can, did, and took 33 days and six repos to notice.

So the fix is probably DELETION, not correction: rule 9 should point at the tables
and stop describing them. A corrected rule 9 is just a fresh copy of the same
failure with a later date on it. Peer agrees and has explicitly NOT edited it --
it is Ryan's ruling, in habituate, not ours.

WHAT THIS REPO SHOULD TAKE FROM IT

1. The pointer-line idea (CLAUDE.md -> "the consumer contract is in README.md")
   now has three data points instead of two. Still cheap, still true, still not
   obviously sufficient -- two of three agents here failed by not reading ANY of
   our files, and a pointer only helps an agent already reading CLAUDE.md.
2. Stronger candidate, and the one this repo can act on alone: anything outside
   this repo that DESCRIBES the tables rather than READING them is a liability we
   cannot lint. We can make that cheaper to resist by making the data easier to
   cite than to paraphrase -- the `use` and `context` columns already do this and
   are the reason the error was catchable at all.
3. Do NOT generalise to "briefings are bad". One briefing sentence went stale
   because it duplicated machine-checked data. That is a narrow, diagnosable
   failure, not a verdict on cross-repo knowledge.

Note the asymmetry worth remembering: the peer's ask would have added a THIRD
prose source of truth about this seam, to fix a problem caused by the second one.
