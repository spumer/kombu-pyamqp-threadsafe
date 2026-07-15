---
artifact: "Quality record — process-state ledger (PFM7 compliance)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
role: "DPF-KNOWLEDGE-CURATION (curator, Sonnet) — repair round 1, Mode C (SKILL.md `dpf-authoring`)"
date_created: "2026-07-14"
purpose: "Holds process-run / phase-tracking text that critic-review.md (PFM7, §1) found leaking into
  the published carrier DPF.md. Per DPF-KNOWLEDGE-CURATION Pattern 1 (Accumulating Provenance Ledger)
  and the repair-list rule 'переносить, не удалять' — this file APPENDS moved text verbatim; it does
  not summarize or paraphrase it. Distinguish (per critic-review.md §1 PFM7 note): per-claim trust-cues
  (`pretrain recall, не верифицирован` / `verified this run (file read)`) are legitimate durable
  reader-facing content and were LEFT IN DPF.md unchanged — only process-run narrative/self-reference
  about the assembly session itself was moved here."
---

# DPF-DEDICATED-IO-THREAD — Quality record (process-state, PFM7)

## 0. Why this file exists

`references/critic-review.md` (Phase 6, guardian, 2026-07-14) found `PFM7 FAIL (repairable)`: process-run
residue — `research_mode:` frontmatter, and the repeated phrases "this run" / "Phase 6 has not run" /
"this is a Phase 4–5 assembly" / "assembler, this run" scattered across the structural report, §11, and
the Conformance checklist — exceeded "one admissible final conformance line" (`E.4.DPF.DA` PFM7 gate;
DPF-KNOWLEDGE-CURATION Pattern 2 / ОШ-05). Repair-list item 1 (this run's task) requires moving that text
here verbatim, not deleting it, and consolidating DPF.md down to one honest status statement per fact.

---

## 1. Moved verbatim — frontmatter `research_mode:` field (was line 13 of `DPF.md`, pre-repair)

> research_mode: "pretrain-only run, 2026-07-14 — WebSearch/WebFetch withheld by explicit customer
> decision for this run. Every SoTA claim below carries the trust-cue `pretrain recall, не
> верифицирован` unless explicitly marked `verified this run (file read)`. See Section 11 and Carrier
> note for what this means for reliance."

**Disposition:** removed from frontmatter. The substance (per-claim trust-cue regime) is not lost — it
is still stated in DPF.md §2 "Claim status", the Carrier note, and now `references/
web-verification-2026-07-14.md` (this round's update to that regime). The field itself was pure
process-run metadata (which run, under what customer instruction) — that belongs here, not in a
publication-carrier frontmatter a future reader will read out of process-context.

---

## 2. Moved verbatim — Structural report §0, "Honest status of this carrier" (pre-repair form)

> **Honest status of this carrier.** This is a Phase 4–5 assembly (architecture decision folded into
> this structural report + `E.4.PFAD`-shaped Section 9; pattern drafting). **Phase 6 — the independent
> `guardian` completeness-critic pass and `E.4.DPF.DA` package-adequacy scoring — has not run.** Per
> `CC-DPFDA.8` this package is **`seedOnly`**, not `admissibleForDeclaredDPFUse`, regardless of how
> complete Sections 0–10 look; see Section 11 and the Conformance checklist at the end for the exact,
> un-inflated status line. Separately, every literature claim in this file is `pretrain recall, не
> верифицирован` (this run's customer-mandated research mode) except the two rows marked `verified
> this run (file read)` — see Carrier note.

**Disposition:** condensed to one paragraph in DPF.md that keeps the substantive honest-status fact
(package is `seedOnly` per `CC-DPFDA.8`, self-declared before Phase 6 — **note for the reader of this
quality record only, not restated as a status change in DPF.md itself: Phase 6 has in fact since run,
see `references/critic-review.md`, verdict `repairBeforeDPFUse`; per Mode C rules the self-declared
status line in DPF.md is left untouched by the curator — only the critic updates it, in round 2**) and
points to this file and to `references/web-verification-2026-07-14.md` instead of re-narrating the
Phase 4–5 process inline.

---

## 3. Moved verbatim — Section 11, original "What has run" / "What has NOT run" (pre-repair form)

> **What has run:** Phase 0 (scope) → Phase 1 (SoTA harvest, 4 traditions + AI slice, `FamilyCoverageFloorK
> =3` met with margin) → Phase 2 (Bridge, role-separated from Phase 1, NQD ≥3 anti-theses on all six
> theses, 5 counterexamples, 10 typical errors, 2 file-read repairs including one falsification) → Phase 3
> (source-pack, 19 rows, retired-premises section present, 5 open provenance questions addressed to
> `architect`/`facilitator`, not resolved by the curator) → **this file**, Phase 4 (architecture decision,
> folded into the structural report above) and Phase 5 (assembly against the canon skeleton).
>
> **What has NOT run:** **Phase 6 — independent `guardian` completeness-critic pass and `E.4.DPF.DA`
> package-adequacy scoring (11 coordinates D1–D11 + PFM subpass) — has not been performed for this
> package.** Per `CC-DPFDA.8`, a `stage-0` package with complete-looking sections is still `seedOnly`
> until that independent pass runs; averaging pattern quality does not substitute for it (`CC-DPFDA.4`).
> **Declared status of this package: `seedOnly`.** It should not be relied on as `admissibleForDeclared
> DPFUse` by any role until Phase 6 completes.

**Disposition:** DPF.md §11 now opens with a single consolidated status statement (package is `seedOnly`
per the assembler's own self-declaration, unchanged by the curator per Mode C rules) plus a pointer to
this file for the phase-by-phase narrative, instead of repeating the full walk-through inline. The
"Known, explicit gaps" and "Refresh triggers" lists that followed this passage in the original DPF.md
are **not** process-state — they are durable content the CC-DPF.7 skeleton requires — and were left in
place, with the §0.2 backpressure/start-timing gap marked closed by this round's new Patterns 7–8 (see
`references/web-verification-2026-07-14.md` for what changed).

---

## 4. Moved verbatim — Conformance checklist, original final lines (pre-repair form)

> **Phase 6 status:** **not run.** No independent `guardian` completeness-critic pass and no `E.4.DPF.DA`
> package-adequacy scoring (D1–D11 + PFM subpass) have been performed against this package. Per
> `CC-DPFDA.8`, sections being complete does not promote a `stage-0` package past `seedOnly` on its own.
>
> \> conformance: CC-DPF.1–9 sections present and self-checked (assembler, this run, 2026-07-14);
> \> E.4.DPF.DA: **seedOnly** — Phase 6 (guardian, independent of this assembly) not yet run.

**Disposition:** the self-referential process marker "(assembler, this run, 2026-07-14)" was removed
from the final conformance line; the substantive status declaration ("CC-DPF.1–9 sections present and
self-checked" / "E.4.DPF.DA: seedOnly — Phase 6 … not yet run") is preserved verbatim in DPF.md,
because per Mode C rules only the critic may edit or supersede a status line, not the curator.

---

## 5. Repair round 1 — log (2026-07-14)

- **Trigger:** `references/critic-review.md` (Phase 6, guardian, 2026-07-14) — verdict
  `repairBeforeDPFUse` (D11 = 3, below floor 4), `gate_passed = false`; PFM7 = FAIL (repairable);
  completeness-critique §0.2 named an unoperationalized coverage gap (write-side backpressure;
  start-timing/lifecycle-ownership/naming), bearing on D1/D7.
- **Actor / role:** `DPF-KNOWLEDGE-CURATION` curator (Sonnet), executing `dpf-authoring` SKILL.md
  **Mode C — Ремонт по repair-спискам**, circle 1 of a maximum of 2.
- **Repair-list items closed this round:**
  1. PFM7 — process traces moved here (this file), verbatim, not deleted (§§1–4 above).
  2. Two new full-`E.8` patterns added to `DPF.md` §4: **Pattern 7 (Bounded Write Backpressure)** and
     **Pattern 8 (Start-Timing & Lifecycle Ownership)** — closing the §0.2 gap the critic named,
     grounded in this round's own web-verified sources (`references/web-verification-2026-07-14.md`,
     new rows S16–S23 in `references/source-pack.md`).
  3. Web-verification of S1–S14 (S1, S2, S3(light), S4, S5, S6, S9, S10, S11, S12, S13, S14) performed
     this round via WebSearch/WebFetch; results in `references/web-verification-2026-07-14.md`. One
     claim (S14, psycopg2/libpq counterexample CE3) was found **inaccurate as stated** and corrected in
     `DPF.md` with an explicit "исправлено по верификации 2026-07-14" annotation. The kombu-Hub
     self-pipe falsification (RP-1) that had already been corrected by direct file-read in the original
     Phase 2 run was re-checked for propagation across `DPF.md`, `source-pack.md`, `sota-research.md`,
     and `theses-antitheses.md` — found already consistent everywhere; no further change needed there.
- **Web tools used this round:** `WebSearch`/`WebFetch`. The original Phase 1–5 run (earlier the same
  day, 2026-07-14) explicitly withheld these tools by customer decision (see §1 above, the retired
  `research_mode:` field) — that restriction applied to the *original authoring* run. This *repair*
  round's task explicitly re-authorizes and requires web verification for repair-list item 3; the two
  runs are not in conflict, they are sequential and dated the same calendar day.
- **What this round did NOT do (explicit non-scope, honestly flagged, not silently skipped):**
  - Did not touch pattern bodies 1–6 or their worked slices (Mode C rule: pattern bodies not rewritten).
  - Did not touch `source-pack.md`'s existing adopted/rejected decisions for S1–S15 (only appended
    verification-field updates — evidence-anchor/trust-cue/currentness — per the explicit exception in
    this round's task rules; adoption decisions themselves are unchanged).
  - Did not change the package's self-declared status line in `DPF.md` (`seedOnly`) or add a
    conformance stamp — that remains the critic's exclusive action, per Mode C and
    `CC-DPFDA.8`/`CC-DPFDA.4`.
  - Did not backfill formal Phase-1 `CorpusLedger` entries in `sota-research.md` or formal Phase-2
    `Thesis`/`NQD` entries in `theses-antitheses.md` for the two new patterns' sources (S16–S23) — those
    are Phase 1 (SoTA Harvest, research role) and Phase 2 (Bridge, `DPF-ADVERSARIAL-REVIEW` role)
    artifacts outside this curator's mandate (Pattern 5, Steward Bounded to Format). `sota-research.md`
    received only a dated addendum to its existing "Freshness & repair register" section recording this
    round's S1–S13 web-verification outcome — not new ClaimSheet entries. Backfilling S16–S23 into a
    full Phase-1/2 pass is named here as an explicit open follow-up, addressed to `architect`/
    `facilitator`, not resolved by the curator (Pattern 5 discipline).
- **Next step:** independent `guardian` re-check (Opus, `DPF-ADVERSARIAL-REVIEW`), round 2 of Mode C's
  "ремонт → повторная проверка" cycle (max 2 circles total).

---

## 6. Repair round 2 (2026-07-14, круг 2) — moved verbatim per `critic-review-2026-07-14-r1.md`

`references/critic-review-2026-07-14-r1.md` (Phase 6 re-check, guardian, 2026-07-14) found round 1's own
repair-item #1 **regressed**: PFM7 FAIL, D5 = 3 below floor 4 — round 1 removed the pre-round-1
process-residue (§§1–4 above) but **introduced a new layer** of repair-changelog narrative into the
carrier itself (≈50+ occurrences of "added this repair round" / "this run" / "this round" / "исправлено
по верификации" / "pre-repair"/"post-repair", plus an internal recount inconsistency, 32 vs 33 rows).
Per DPF-KNOWLEDGE-CURATION Pattern 1 (no info loss) — every block below is the **exact pre-round-2 text**
of `DPF.md`, moved here verbatim, not paraphrased. The council's minimal-repair instruction to this
round named the below sub-items explicitly (`critic-review-2026-07-14-r1.md` §4, item 1); a few
additional matches of the same residue class, found by the same grep pattern the critic used, are moved
alongside them for consistency (not expanding scope — same defect class, same fix).

### 6.1 Frontmatter — `fpf_edition` / `updated` (pre-round-2)

> fpf_edition: "ailev/FPF@f7c7e93f (snapshot 2026-07-03; local copy ~/.claude/knowledge/fpf/FPF-Spec.md;
> E.4.DPF §1-§7/E.8/F.18 headers grepped live this run 2026-07-14; A.2.6/B.5.2.1/A.11/E.4.PFR
> line-anchors inherited from theses-antitheses.md, live-grepped the same day)"
> updated: "2026-07-14 (repair round, Mode C круг 1; original assembly same-day)"

**Disposition:** `fpf_edition`'s substantive content (which sections were grepped, when, and what was
inherited from where) is preserved — only the run-tie "this run" is dropped, leaving "grepped live
2026-07-14". `updated` is simplified to the bare date; the round-number/circle detail it carried is not
lost — it lives here (§5 above logs round 1; this §6 logs round 2).

### 6.2 Structural report §0 — "For whom, first task" bullet, Phase-6 clause (pre-round-2)

> Secondary readers: `dev` implementing against the resulting patterns; `guardian`/`cto`
> running the Phase 6 `E.4.DPF.DA` adequacy pass this package has **not yet received** (Section 11).

**Disposition:** "has not yet received" was stale by round 2 (Phase 6 has in fact run twice — round-0
`critic-review.md` and round-1 `critic-review-2026-07-14-r1.md`). Replaced with a pointer to Section 11
for current status, asserting no verdict itself (Mode C: only the critic writes status).

### 6.3 Structural report §0 — "What is foregrounded" bullet, Patterns 7–8 clause (pre-round-2)

> plus two added in the 2026-07-14 repair round to close a named coverage gap (`references/
> critic-review.md` §0.2): (7) write-side backpressure needs an explicit watermark pair, and
> (8) ownership's start-timing (lazy-on-first-use vs. explicit `start()`) must be named, not implied.
> Patterns 7–8 are grounded directly in this round's own web-verified sources (`references/
> web-verification-2026-07-14.md`); a formal Phase-1/2 backfill (`sota-research.md` CorpusLedger,
> `theses-antitheses.md` Thesis/NQD entries) for their sources remains an open follow-up outside this
> curator's mandate — flagged, not silently skipped (`references/quality-record-2026-07-14.md` §5).

**Disposition:** substance preserved (what Patterns 7–8 are, their sourcing, the open Phase-1/2 backfill
follow-up) — only "2026-07-14 repair round" / "this round's own" round-tie framing dropped in favor of
"grounded in web-verified sources".

### 6.4 Structural report §0 — "Honest status of this carrier" bullet (pre-round-2)

> **Honest status of this carrier.** Architecture decision is folded into this structural report plus
> the `E.4.PFAD`-shaped Section 9. **Phase 6 — the independent `guardian` completeness-critic pass and
> `E.4.DPF.DA` package-adequacy scoring — has not run.** Per `CC-DPFDA.8` this package is
> **`seedOnly`**, not `admissibleForDeclaredDPFUse`, regardless of how complete Sections 0–10 look; see
> Section 11 and the Conformance checklist at the end for the exact, un-inflated status line. Every
> literature claim in this file carries a per-claim trust-cue in Section 7 (SoTA-Echoing): most were
> `pretrain recall, не верифицирован`; a first web-verification pass (2026-07-14 repair round) raised
> most of them to `verified` — see `references/web-verification-2026-07-14.md` and the Carrier note.
> Process history of this file's assembly and repair runs is kept in `references/
> quality-record-2026-07-14.md`, not narrated here.

**Disposition:** "Phase 6 ... has not run" was stale by round 2 (same fact as §6.2). Rewritten to point to
`references/critic-review.md` and `references/critic-review-2026-07-14-r1.md` for the actual current
Phase-6 state instead of restating an outdated "has not run" claim; the trust-cue substance
(`verified <date>, <URL>` / `verified by file read` / `pretrain recall, не верифицирован`) and the
pointer to the quality record are preserved.

### 6.5 §1 Non-use boundary, last bullet (pre-round-2)

> **NOT** a production-checked claim set — every claim carries a per-claim trust-cue (Section 7); most
> of the literature basis (S1–S13) was web-verified in a 2026-07-14 repair round (`references/
> web-verification-2026-07-14.md`), but the AI-in-domain slice (Pattern 6) remains recall-only by
> construction (no single citable paper), and this package's overall status remains `seedOnly` pending
> an independent Phase 6 pass (Section 11).

**Disposition:** "remains `seedOnly` pending an independent Phase 6 pass" was stale (same fact as §6.2/
§6.4). Rewritten to point to Section 11 for status rather than asserting a specific state here; the
"web-verified" fact and AI-slice caveat preserved without the "repair round" framing.

### 6.6 "Instantiating project" paragraph, §1 (pre-round-2)

> verified this run by direct file read (`src/kombu_pyamqp_threadsafe/__init__.py`, classes/attributes at
> lines 353, 549, 555, 827/1103/1121)

**Disposition:** "this run" dropped, "verified by direct file read" (durable evidence-method statement)
kept; the line numbers and file path are unchanged.

### 6.7 §2 Source pack header — recount narrative (pre-round-2)

> Full provenance registry (33 rows: 3 phase artifacts, 23 CorpusLedger sources S1–S23 — S1–S15
> original, S16–S23 added 2026-07-14 for Patterns 7–8, 2 verified file-reads, FPF-Spec live grep,
> method.md canon, 3 confirmed-absent context paths — **исправлено по верификации 2026-07-14**: the
> pre-repair header here undercounted this registry as "19 rows"; recounted to 25 pre-repair / 32
> post-repair, a curator-format correction, not a domain-content change) —
> [`references/source-pack.md`](references/source-pack.md). Full ClaimSheets —
> [`references/sota-research.md`](references/sota-research.md). Full Bridge —
> [`references/theses-antitheses.md`](references/theses-antitheses.md). Below is a summary only.

**Disposition:** removed per `critic-review-2026-07-14-r1.md` §4 item 1 explicit instruction ("удалить
целиком (и заодно снять ошибку 32 vs 33); в носителе — просто «source-pack.md (S1–S23)»"). The
underlying arithmetic note for the record: `references/source-pack.md` currently carries 23
`S`-numbered CorpusLedger rows (S1–S23, `grep`-counted 2026-07-14); the pre-round-2 "25 pre-repair / 32
post-repair" row-count narrative in `DPF.md` did not reconcile with its own "33 rows" claim two
paragraphs later (Artifacts §, "33 rows: 25 pre-repair + 8 new") — 25 + 8 = 33, not 32. This is a
curator-arithmetic slip in round-1's own recount prose, not a `source-pack.md` content defect; no
`source-pack.md` edit was made or is proposed here (out of this round's scope). `DPF.md` §2 now states
only `source-pack.md (S1–S23)`, which does not depend on the exact row-count arithmetic being right.

### 6.8 §2 Adopted bullet — "verified this run" (pre-round-2)

> Two rows are **verified this run by direct file read**, not recall: this repository's own
> `DrainGuard`/`_transport_lock`/`channel_thread_bindings`/`_teardown_lock` machinery, and installed
> kombu 5.6.2's `hub.py` (used to **falsify** a sub-claim, see next bullet).

**Disposition:** "this run" dropped; "verified by direct file read" retained. Facts unchanged.

### 6.9 §2 Rejected/retired bullet — S14/CE3 "исправлено по верификации" (pre-round-2)

> S14 (psycopg2/libpq thread-affinity docs) parked as Tradition, used only as counterexample CE3
> (different resolution family from Patterns 1–2: no owning thread/turn — see Pattern 5 CE3 for the
> precise, corrected boundary; **исправлено по верификации 2026-07-14** — was "caller-supplied external
> lock, no library-provided primitive," corrected to "psycopg2 itself locks the shared connection
> internally; what it lacks is a Pattern-2-shaped *crossing-into-an-owner's-loop* primitive, not locking
> as such," source `references/web-verification-2026-07-14.md` §1 row S14).

**Disposition:** per repair-list rule ("исправлено по верификации … ×4 → оставить durable-формулировку
(текущее корректное содержание claim) + указатель на web-verification; убрать «было X / стало Y /
pre-repair»-нарратив"). Rewritten to state only the corrected, current content (psycopg2 locks
internally; what it lacks is a Pattern-2-shaped crossing primitive) plus the `web-verification` pointer;
the pre-repair wrong claim ("was ... corrected to ...") is not restated in `DPF.md` — its exact original
wording is preserved above and in `references/web-verification-2026-07-14.md` §1 row S14.

### 6.10 §2 Claim status bullet — repair-round framing (pre-round-2)

> A 2026-07-14 repair round web-verified S1–S13 against live sources (`references/
> web-verification-2026-07-14.md`): 11 of 13 confirmed as stated, one (S6/Kafka) confirmed-and-sharpened,
> and the adjacent S14 counterexample corrected (see above) — trust-cues in Section 7 now read `verified
> 2026-07-14, <URL>` per row.

**Disposition:** "A 2026-07-14 repair round" round-tie dropped; the verification outcome (11/13
confirmed, one sharpened, S14 corrected) and the date are preserved verbatim in substance.

### 6.11 §2 Currentness bullet — "(repair round)" parenthetical (pre-round-2)

> **Currentness:** scope/sota-research/theses-antitheses/source-pack all dated 2026-07-06 → **2026-07-14
> for this DPF's own artifacts**, web-verification pass **2026-07-14** (repair round); `fpf_edition`
> grepped live for `E.4.DPF`/`E.8`/`F.18`, inherited for `A.2.6`/`B.5.2.1`/`A.11`/`E.4.PFR` from the
> same-day Phase 2 grep. `review_due` 2026-09-29.

**Disposition:** "(repair round)" parenthetical dropped after "web-verification pass **2026-07-14**";
dates and the grep-inheritance fact preserved.

### 6.12 §4 Patterns section intro — Patterns 7–8 round-tie (pre-round-2)

> Rule: **general SoTA principle before our particular instantiation** (A.1.1). Patterns 1–6 map 1:1
> onto one thesis each in `references/theses-antitheses.md` §2; the anti-theses (NQD ≥3) and full
> scope lines live there and are not repeated in full here (faithful pointer, not restated content).
> Patterns 7–8 (added 2026-07-14 repair round) ground their principle directly in this round's
> web-verified sources instead — they do not yet have a matching Phase-2 thesis/NQD entry, an explicitly
> open follow-up (`references/quality-record-2026-07-14.md` §5), not a silent gap.

**Disposition:** "(added 2026-07-14 repair round)" and "this round's" dropped; the substantive fact
(Patterns 7–8 ground in web-verified sources, lack a matching Phase-2 thesis/NQD entry, open follow-up)
is preserved.

### 6.13 Pattern 7 heading and blocknote (pre-round-2)

> ### Pattern 7 (added 2026-07-14 repair): Bounded Write Backpressure — Explicit Watermarks, Not an
> Unbounded Queue
>
> > Added this repair round to close a coverage gap the independent critic named (`references/
> > critic-review.md` §0.2): `write-side backpressure` was named in the bounded context (§1) and in the
> > §8 glossary term "Backpressure," but no pattern actually delivered on it. Sources verified
> > 2026-07-14, `references/web-verification-2026-07-14.md` §3 (S16–S18).

**Disposition:** per repair-list rule ("блокноты «> Added this repair round to close…» на Pattern 7/8 →
заменить на нейтральный durable-текст паттерна"). Heading loses "(added 2026-07-14 repair)"; the
blocknote is rewritten to state what gap the pattern closes and its verified sources, durably, without
narrating "this repair round" as the actor. The fact that Patterns 7–8 were added in response to a named
critic gap (`critic-review.md` §0.2) is not lost — it is preserved here and in §5 above (round-1 log) and
in the structural report §0 (§6.3 above, now durable).

### 6.14 Pattern 7 worked-slice header — "this repair round" (pre-round-2)

> **Our instantiation (worked slice) — honestly flagged as an ABSENT worked slice, not a fabricated
> one.** A repository-wide search this repair round (`grep -in "watermark\|backpressure\|high_water\|
> pause_writing\|resume_writing" src/kombu_pyamqp_threadsafe/*.py`, 2026-07-14) found **no** watermark
> pair, no pause/resume-equivalent callback, and no explicitly bounded producer-side queue on the
> publish/write path.

**Disposition:** "this repair round" dropped; the grep command, its date, and its (negative) result are
preserved verbatim.

### 6.15 Pattern 8 heading and blocknote (pre-round-2)

> ### Pattern 8 (added 2026-07-14 repair): Start-Timing & Lifecycle Ownership — Lazy-on-First-Use vs.
> Explicit `start()`, Named and Owned
>
> > Added this repair round to close the second half of the same coverage gap (`references/
> > critic-review.md` §0.2): the bounded context (§1) named "lazy-on-first-use vs. explicit `start()`,
> > lifecycle owner, daemon vs. non-daemon, naming" as first-class scope, but Pattern 1 only answered
> > *which family* owns, not *when* ownership begins. Sources verified 2026-07-14, `references/
> > web-verification-2026-07-14.md` §3 (S19–S23).

**Disposition:** same treatment as §6.13 above, applied to Pattern 8's heading and blocknote.

### 6.16 Pattern 8 worked-slice — "Verified this repair round" (pre-round-2)

> thread's own call to `drain_events()`. Verified this repair round by file read and repository-wide
> search (`src/kombu_pyamqp_threadsafe/__init__.py`; `grep -n "daemon\|Thread(" src/
> kombu_pyamqp_threadsafe/__init__.py` found no `Thread(...)` construction and no `daemon=` flag anywhere
> in the module, 2026-07-14): this repository's own library code never spawns an OS thread of its own.

**Disposition:** "this repair round" dropped, "Verified by file read" retained; grep command, date, and
result preserved verbatim.

### 6.17 §6 Typical errors intro — rows 11–12 round-tie (pre-round-2)

> Symptom → why → fix → source. Beginner and experienced-practitioner-from-stale-practice mistakes
> together (D7); AI-specific rows marked. Rows 1–10 are faithfully carried from `references/
> theses-antitheses.md` §4 (full NQD anti-theses there), not re-derived here. Rows 11–12 are new,
> added directly in this 2026-07-14 repair round alongside Patterns 7–8 — not yet backfilled into
> `theses-antitheses.md` §4 (curator-mandate boundary, see `references/quality-record-2026-07-14.md` §5).

**Disposition:** "are new, added directly in this 2026-07-14 repair round alongside Patterns 7–8" →
"correspond to Patterns 7–8". The substantive fact (rows 11–12 map to Patterns 7–8, lack Phase-2
backfill, curator-mandate boundary) is preserved.

### 6.18 §6 rows 11–12 — "(added 2026-07-14)" tags (pre-round-2)

> | 11 (added 2026-07-14) | A write path has a queue in front of the socket but no bound and no
> producer-facing signal — it just grows | … |
> | 12 (added 2026-07-14) | A background thread is spun up as an invisible side effect of an unrelated
> call (e.g. the first `publish()`), undocumented | … |

**Disposition:** the "(added 2026-07-14)" tag dropped from both row numbers; row content unchanged.

### 6.19 §7 SE-14 — "исправлено по верификации" was/became narrative (pre-round-2)

> SE-14 | ~~psycopg2/libpq: caller must supply external mutual exclusion; no owning thread or
> library-provided crossing primitive~~ **исправлено по верификации 2026-07-14: было "caller must supply
> external mutual exclusion, no library-provided primitive"; стало "raw libpq (C API) requires the
> caller to serialize access, but psycopg2 itself locks the shared connection internally — the
> Python-level caller does NOT need to supply an external mutex; what psycopg2 still lacks is a
> Pattern-2-shaped crossing-into-an-owner's-loop primitive, not locking as such"**, source
> `references/web-verification-2026-07-14.md` §1 row S14 | psycopg2/libpq docs [S14] | fact / `verified
> 2026-07-14, https://www.postgresql.org/docs/current/libpq-threading.html` (libpq) +
> `https://github.com/psycopg/psycopg2/discussions/1652` (psycopg2 internal locking); parked as
> Tradition | Adopted: Pattern 5 counterexample (CE3) only, corrected form

**Disposition:** same rule as §6.9. Rewritten to state only the current, corrected claim plus the
`web-verification` pointer; "was X / стало Y" narrative and "corrected form" trailing note dropped from
`DPF.md`; original wording preserved verbatim above.

### 6.20 §8 Names — "Thread affinity without ownership" row (pre-round-2)

> **Thread affinity without ownership (contrast term)** | A resource not handed to any owner thread/turn,
> with no library-provided reconnect-idempotency guard to reclaim (**исправлено по верификации
> 2026-07-14**: was "the caller must supply external mutual exclusion themselves" — for psycopg2
> specifically that overstated it, since psycopg2 locks the shared connection internally; corrected to
> the boundary that actually holds, see Pattern 5 CE3 and `references/web-verification-2026-07-14.md`) |
> This competency's subject — kept only as the CE3 boundary marker

**Disposition:** same rule as §6.9/§6.19; rewritten to the current, corrected definition plus pointer.

### 6.21 §6 row 7 and §8 header — remaining "this run" occurrences (pre-round-2)

> CE2; verified this run (kombu 5.6.2 source read)

> Candidates for `project/glossary.md` — **not migrated** here; this project has no `glossary.md` at the
> time of this run (confirmed absent, `source-pack.md` open provenance question #4).

> grounded_in | FPF `E.4.DPF` | meta | Canon skeleton, `CC-DPF.1–9`, publication order — grepped live
> this run (lines 66066–66434)

**Disposition:** "this run" → "by file read" / "at the time of writing" / "2026-07-14" respectively
(durable phrasing, same facts, no run-tie).

### 6.22 §11 — status paragraph, stale "pending Phase 6" (pre-round-2)

> **Declared status of this package: `seedOnly`** (self-declared, per `CC-DPFDA.8`) pending Phase 6 —
> independent `guardian` completeness-critic pass and `E.4.DPF.DA` package-adequacy scoring (11
> coordinates D1–D11 + PFM subpass). Averaging pattern quality does not substitute for that pass
> (`CC-DPFDA.4`); this package should not be relied on as `admissibleForDeclaredDPFUse` by any role until
> Phase 6 completes and updates this status line (only the critic may do so, Mode C). Phase-by-phase
> history of what has run for this package (Phases 0–5, and this 2026-07-14 repair round) is in
> `references/quality-record-2026-07-14.md`, not narrated here.

**Disposition:** "pending Phase 6" / "until Phase 6 completes" was stale by round 2 (same fact as §6.2/
§6.4/§6.5) — Phase 6 has run twice, and this package remains `repairBeforeDPFUse` per the r1 re-check,
not because Phase 6 hasn't happened. The self-declared `seedOnly` label itself is **left unchanged**
(Mode C: only the critic edits it) — but the surrounding narrative is rewritten to stop asserting Phase 6
has not run, and points instead to `references/critic-review.md` and
`references/critic-review-2026-07-14-r1.md` for the actual current verdict, without the curator stating
that verdict itself.

### 6.23 §11 — "Closed this round" / "New, opened this round" gap bullets (pre-round-2)

> **Closed this round:** write-side backpressure and start-timing/lifecycle-ownership/naming — named in
> the bounded context (§1) but not operationalized into a pattern — are now Patterns 7–8 (§4), added
> 2026-07-14. Source-pack open questions #1 (S1–S13 web-verification) is **largely closed**: 11 of 13
> confirmed as stated, one sharpened, one adjacent claim (S14) corrected — see `references/
> web-verification-2026-07-14.md`.
>
> […]
>
> **New, opened this round:** Patterns 7–8's sources (S16–S23) have no formal Phase-1 `CorpusLedger` /
> Phase-2 `Thesis`/`NQD` backfill yet (curator-mandate boundary, `references/
> quality-record-2026-07-14.md` §5) — addressed to `architect`/`facilitator` for a future full pipeline
> pass, not resolved here.

**Disposition:** "Closed this round:" / "New, opened this round:" round-tie labels dropped; the
underlying facts (backpressure/start-timing now covered by Patterns 7–8, S1–S13 largely web-verified,
S16–S23 lack Phase-1/2 backfill) are preserved as plain gap-list bullets, indistinguishable in kind from
the other (already-durable) bullets in the same list.

### 6.24 §11 — "not re-verified this round" (pre-round-2)

> The AI-in-domain slice (S15, Pattern 6, typical errors #1–#5 as an "AI-specific" framing) remains
> explicitly weaker evidence than T1–T4 — no single citable paper, not a fetchable document, therefore
> not re-verified this round; a targeted search for published empirical studies of LLM-generated
> concurrency bugs remains the named repair (source-pack open question #2).

**Disposition:** "not re-verified this round" → "not re-verified" (the claim was never verified, in any
round — dropping the round-tie does not change the fact).

### 6.25 Artifacts § — source-pack.md row-count and "this round" labels (pre-round-2)

> [`references/source-pack.md`](references/source-pack.md) — Phase 3: provenance registry (33 rows:
> 25 pre-repair + 8 new for Patterns 7–8's sources S16–S23, added 2026-07-14), retired premises (RP-1),
> 5 open provenance questions addressed to `architect`/`facilitator`.
>
> [`references/critic-review.md`](references/critic-review.md) — Phase 6: independent guardian
> completeness-critic + `E.4.DPF.DA` verdict (`repairBeforeDPFUse`, D11 below floor), the actual gate
> this repair round is closing.
>
> [`references/web-verification-2026-07-14.md`](references/web-verification-2026-07-14.md) — this
> round: S1–S14 web-verification ledger, S16–S23 new-source ledger.
>
> [`references/quality-record-2026-07-14.md`](references/quality-record-2026-07-14.md) — this round:
> process-state moved out of `DPF.md` (PFM7), repair log.

**Disposition:** same treatment as §6.7 for the source-pack row-count (dropped, replaced with `S1–S23`);
"the actual gate this repair round is closing" / "this round:" labels dropped from the other three
bullets, replaced with plain descriptions. `references/critic-review-2026-07-14-r1.md` — not previously
listed in Artifacts at all — is added as a new bullet (not a residue removal, a genuine gap-fill: the
file this very repair responds to was missing from the carrier's own map, a `PFM3` discoverability
defect, fixed alongside the residue cleanup since it is directly adjacent).

### 6.26 Carrier note — "the original ... run" / "A ... repair round" framing (pre-round-2)

> Literature sources S1–S14 were originally admitted through recall (the original Phase 1–5 authoring run
> explicitly withheld WebSearch/WebFetch by customer decision). A 2026-07-14 repair round performed a
> first web-verification pass against live sources for S1–S14 (`references/web-verification-2026-07-14.md`);

**Disposition:** reworded to state the same two facts (recall-only admission originally; a dated
web-verification pass later checked S1–S14) without "the original ... run" / "A ... repair round"
self-reference framing.

### 6.27 Conformance checklist — stale "Phase 6 status: not run" (pre-round-2)

> **Phase 6 status:** **not run.** No independent `guardian` completeness-critic pass and no
> `E.4.DPF.DA` package-adequacy scoring (D1–D11 + PFM subpass) have been performed against this package.
> Per `CC-DPFDA.8`, sections being complete does not promote a `stage-0` package past `seedOnly` on its
> own.
>
> \> conformance: CC-DPF.1–9 sections present and self-checked (assembler, this run, 2026-07-14);
> \> E.4.DPF.DA: **seedOnly** — Phase 6 (guardian, independent of this assembly) not yet run.

**Note — this exact block was already superseded once** (round 1 replaced it with the paragraph captured
below as the round-1→round-2 pre-edit state; that round-1 text is what round 2 actually found and moved,
not this original block, which round 1 already condensed per §4 above in this file). The round-1→round-2
pre-edit paragraph, moved now:

> **Phase 6 status:** **not run** (self-declared status, unchanged by this curator per Mode C — see
> `references/critic-review.md` for the independent guardian's actual Phase-6 findings and verdict, and
> `references/quality-record-2026-07-14.md` for this round's repair log). No independent `guardian`
> completeness-critic pass and no `E.4.DPF.DA` package-adequacy scoring (D1–D11 + PFM subpass) have been
> folded back into this status line. Per `CC-DPFDA.8`, sections being complete does not promote a
> `stage-0` package past `seedOnly` on its own.

**Disposition:** "**not run**" was stale by round 2 (Phase 6 has run twice — same fact as §6.2/§6.4/§6.5/
§6.22). Rewritten to point to both `critic-review.md` and `critic-review-2026-07-14-r1.md` for the
actual findings/verdict without asserting "not run", and to drop "(assembler, this run, 2026-07-14)" /
"this round's" round-tie phrasing. **The one final conformance line itself** (`> conformance: CC-DPF.1–9
… E.4.DPF.DA: seedOnly — Phase 6 … not yet folded back into this status line`) was found accurate as
written (it correctly states the verdict has not been folded back into the self-declared line, which
remains true and is exactly the Mode C-correct state) and was **left unchanged** — this is the one
admissible final conformance line the repair-list rule asks to preserve.

---

### Repair round 2 — log (2026-07-14)

- **Trigger:** `references/critic-review-2026-07-14-r1.md` (Phase 6 re-check, guardian, 2026-07-14) —
  verdict `repairBeforeDPFUse`, **D5 = 3 below floor 4** (PFM7 regressed vs round 0: round 1's own
  repair-item #1 was not achieved — a new repair-changelog narrative layer was introduced instead of
  being consolidated away). `gate_passed = false`. D11 was separately confirmed repaired (3→4) and is
  **not** touched this round (no-proposal coordinate, not part of the repair list).
- **Actor / role:** `DPF-KNOWLEDGE-CURATION` curator (Sonnet), executing `dpf-authoring` SKILL.md
  **Mode C — Ремонт по repair-спискам**, circle 2 of a maximum of 2 (last circle).
- **Scope actually executed — repair-list item #1 only** (`critic-review-2026-07-14-r1.md` §4, "Наименьшие
  правки", item 1 — the only item tied to a coordinate below floor, D5). Items 2 (Phase-1/2 CorpusLedger/
  NQD backfill for S16–S23) and 3 (execute ≥1 heterogeneous case as fact) were explicitly marked by the
  critic as **not blocking the floor** / **enrichment, not blocking**, and item 2 is explicitly named as
  owned by a different role ("research/`DPF-ADVERSARIAL-REVIEW`-Bridge, не curator") — both left untouched
  this round, per the task's own instruction to execute only the repair proposals for below-floor
  coordinates, and per `DPF-KNOWLEDGE-CURATION` Pattern 5 (steward bounded to format, not domain content).
- **What this round did:** moved all process-run/repair-changelog residue named by the critic (and the
  same-class residue found by re-running the critic's own grep patterns for consistency) from `DPF.md`
  into this file, verbatim (§§6.1–6.27 above); left every durable per-claim trust-cue
  (`verified <date>, <URL>` / `verified by file read` / `pretrain recall, не верифицирован`) unchanged in
  `DPF.md`, per the critic's own explicit distinction (`critic-review-2026-07-14-r1.md` §1, PFM7 row);
  fixed the internal 32-vs-33 row-count inconsistency by removing the disputed count from `DPF.md`
  entirely rather than re-deriving a new number (§6.7); added the previously-unlisted
  `critic-review-2026-07-14-r1.md` to the Artifacts section (§6.25) as a discoverability fix.
- **What this round explicitly did NOT do (non-scope, honestly flagged):**
  - Did not rewrite any pattern body's substantive content (Patterns 1–8 keep their principle/
    instantiation/counterexample/anti-pattern/conformance/connections text; only their surrounding
    process-narrative headers/blocknotes were reworded).
  - Did not touch `source-pack.md`, `sota-research.md`, or `theses-antitheses.md` bodies.
  - Did not perform Phase-1 `CorpusLedger` or Phase-2 `Thesis`/`NQD` backfill for S16–S23 (repair-list
    item 2 — out of curator mandate, named above).
  - Did not execute any heterogeneous case as fact (repair-list item 3 — enrichment, not blocking).
  - Did not change the package's self-declared status line (`seedOnly`) or the final conformance line —
    both remain the critic's exclusive province, Mode C.
  - Did not perform new web verification — all trust-cues/URLs from `references/
    web-verification-2026-07-14.md` are carried forward unchanged; no new sources were checked this round.
- **Next step:** independent `guardian` re-check (`DPF-ADVERSARIAL-REVIEW`) of this round's repair against
  `critic-review-2026-07-14-r1.md`'s reopen-conditions (D5/PFM7 re-scored; if D5 ≥ 4 and PFM7 no longer
  FAILs, status may move to `admissibleForDeclaredDPFUse`). Per Mode C this is the **last** circle
  (maximum 2); if PFM7/D5 still fails after this round, the package's status is a facilitator/Founder
  decision outside the ремонт loop, not a third automatic circle.
