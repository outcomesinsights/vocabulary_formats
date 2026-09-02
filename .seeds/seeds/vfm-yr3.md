---
id: vfm-yr3
title: "THE RATCHET: a false negative is never acceptable; false positives are tightened away incrementally, on measurement"
status: captured
type: decision
created_at: 2026-08-27T20:55:00.892321+00:00
updated_at: 2026-08-27T20:57:34.487564+00:00
tags:
  - principle
  - ratchet
  - false-negative
  - false-positive
  - trellis-candidate
  - ryan
  - 2026-08-27
converted_at: 2026-09-02T14:41:48.760748+00:00
---

RYAN, 2026-08-27, stating the governing rule for every regex in this repo:

  "The whole point of maintaining vocabulary_formats and using it as our source of truth is
   that when we find a problem with a regular expression in vocabulary_formats and we address
   it, like the more tightened version we just came up with, then it is important we change
   vocabulary_formats so that everything downstream consuming it benefits from that knowledge...
   it is important that we again avoid any possibility of a false negative but continue to
   tighten as best we can to avoid false positives."

## THE RULE, in two asymmetric halves

  FALSE NEGATIVE   inviolable. A row must never reject a real code, judged against that row own
                   declared target (see vfm-k2n: the default targets claims-observable codes;
                   variants carry the rest). This is a HARD constraint, not a preference. A
                   rejected real code is silent, unrecoverable, and propagates to every consumer.

  FALSE POSITIVE   a RATCHET. Never acceptable to widen, always legitimate to tighten, one
                   measured increment at a time. Each tightening must be validated at 0 NEW
                   false negatives against the full concept list before it lands.

The asymmetry is the whole principle. The two errors are not symmetric costs: a false positive
costs a human one glance in review, a false negative costs a code nobody will ever know was lost.

## WHY IT LIVES HERE AND NOT IN A CONSUMER

This is the argument for the repo existing. A consumer that discovers a tightening and keeps it
locally has helped itself once; the same defect stays live in every other consumer, and the next
person re-derives it. Fixing it HERE means the knowledge propagates by construction.

Concretely: on 2026-08-27 the literature consumer was offering T2DM, QALY, H2O and T2D to a human
reviewer as candidate ICD-10-CM codes. The temptation was to filter them consumer-side. The right
fix was the row, because the claims consumer had the same latent hole and nobody had noticed.

## THE RATCHET NEEDS A RECORD, OR IT SLIPS

Ryan, same message: "we probably at this point need to be keeping track of the edge cases that we
are encountering and how that is affecting vocabulary formats. Probably could suffice as maybe a
change log kept in vocabulary formats."

Hence CHANGELOG.md. Each entry: the edge case, where it was found, what the row was, what it
became, and the false-negative count measured before and after. Without it the notes column
accumulates history nobody reads in order, and a later agent re-widens a row that was narrowed
for a reason it cannot see.

⚠️ A worked example of the slip this prevents, from the very row changed that day: ICD10CM notes
said "Positions 2-3 stay \w deliberately - FY2026 introduced QA0". Position 2 had ALREADY been
narrowed on 2026-08-12, so the note defended a state the row no longer had. A changelog ordered by
date would have made that visible; a notes field appended to for a month did not.

## The measurement discipline the ratchet requires

Tighten only with (a) the full concept list scored before and after, and (b) real corpus tokens
that motivated it. Reading a regex is not measuring it -- on 2026-08-27 I called ICD10PCS default
"catastrophically broad" from the pattern alone, then measured 96% precision in practice. See
clc-ass in the literature consumer: fixtures are harvested from real documents, never invented.


## ALREADY TRELLISED — this seed restates rule 2, it does not add a rule

Checked before trellising: CLAUDE.md section "THE TWO RULES THAT GOVERN EVERY EDIT" rule 2
("COMPLETE first, then as NARROW as a plain regexp reasonably gets") already states this exactly:
"never reject a real code. False negatives are unacceptable — that is the repo entire contract
with its consumers, not a style preference" and "permissiveness is the FLOOR, not the goal", with
the ordering COMPLETENESS -> NARROWNESS -> PERMISSIVENESS-BREAKS-TIES.

So no third rule was added. What this seed contributes beyond it:

  1. THE CHANGELOG. Rule 2 governs each edit in isolation; it has nothing to say about keeping the
     RECORD of edits legible over time. CHANGELOG.md, created 2026-08-27, is the addition.

  2. THE PROOF THAT THE RECORD WAS ALREADY SLIPPING. Rule 2 own worked example had gone stale in
     the durable context: it cited "positions 2-3 stay \w" as the permissiveness illustration,
     while position 2 had been narrowed 2026-08-12 and position 3 was narrowed 2026-08-27. The
     principle was right and its evidence had rotted. Corrected in place, marked historical
     rather than deleted, per house style.

  3. THE ENFORCEMENT GAP, split out as vfm-v3k: rule 2 is a rule nothing executes on every run.
     just test needs a 1.4 GB substrate and skips without it; just lint checks structure and never
     looks at a code. A committed known-good/known-bad fixture set is what would make rule 2
     enforceable rather than aspirational.
