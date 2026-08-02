# Design Log — 2026-08-01: Plan/Execution Model, Provenance, and Content Governance

A record of the design conversation and decisions behind the `plan-execution-model`
branch (merged to `develop`/`main` this session). Complements
[`plan-execution-model.md`](plan-execution-model.md), which is the technical
pattern reference; this document is the rationale and decision history —
*why* things ended up shaped the way they did, and what was deliberately
deferred.

---

## 1. Completing the plan/execution model

Starting point: `plan-execution-model` already had `Step`/`Transition`/
`Variable` and the `OperationPlan`/`ControlPlan`/`DetectionPlan` split
drafted, plus a first pass at `examples/operation-plan-t1003-001.ttl` (ATT&CK
T1003.001 — LSASS credential dumping). Work this session:

- Added `stonework:correspondsToStep`, linking an executing `CyberActivity`
  back to the `Step` it performs — filled a gap the ontology's own
  `Step` scopeNote had already flagged as undefined.
- **The scientific method, formalized.** Long-standing personal interest,
  brought into the ontology: `stonework:Hypothesis` (predicted outcome),
  `predictsVariable`/`predictedType`/`predictedValue`/`predictedLiteral`
  (mirroring `boundTo`/`boundToLiteral` on the actual-result side),
  `confidence` (0–100, matching STIX), `hasHypothesisStatus` (kept explicit
  rather than inferred from which `Transition` fired). A key structural
  fact resolved an open design question for free: because `Step` is already
  declared `a stonework:Behavior`, one `predictsVariable` property covers
  hypotheses at *any* depth of a Plan's decomposition, not just the top
  level — no separate Plan-level vs. Step-level property was needed.
- **`InvestigationPlan` added as the assessment-plan counterpart to
  `Playbook`.** `DetectionPlan` was re-subclassed under it (was directly
  under `Behavior`) — it's the narrow "is this a violation?" triage case;
  `InvestigationPlan` is the general case (forensic analysis, malware
  analysis, vulnerability assessment).
- **Fixed a real bug in the T1003.001 example**, found by asking "does this
  actually preserve forensic history?": all three candidate-procedure
  attempts shared one `Variable` (`var-credential-outcome`) as their
  `Transition` guard. Rebinding it per attempt would have silently
  overwritten earlier attempts' results. Fixed by giving each attempt Step
  its own output `Variable`; the shared Variable was repurposed as the
  *Plan's* own top-level output.

Full technical detail, diagrams, and a recipe for encoding another ATT&CK
T-code: [`plan-execution-model.md`](plan-execution-model.md).

Commits: `672a28e`.

## 2. Forensic provenance

Prompted by a direct question: does the T1003.001 graph actually confirm
capturing provenance of the executed technique? Answer, after tracing it:
partially. The *technique-attribution* chain (`Activity` →
`correspondsToStep` → `Step` → `implements` → `Procedure` → `implements` →
`AttackPattern`) was real and traversable. But classical forensic
provenance — who, when, against what — was missing, and two of the three
gaps were ontology-level, not just missing instance data: no timestamp
property existed anywhere on `CyberActivity`, and `attributedTo`'s range
was hard-typed to `ThreatActor` (wrong — `CyberActivity` covers defensive
and neutral activities too; good, well-intentioned people perform
CyberActivities, not just adversaries).

Added `stonework:actsOn` (mirrors `prov:used`), `startedAtTime`/
`endedAtTime` (mirror `prov:startedAtTime`/`endedAtTime`), and widened
`attributedTo`'s range. Wired all three into every executed activity in the
T1003.001 example, with a new `ThreatActorGroup`, `Host`, and
`RuntimeProcess` individual to anchor them.

Commits: `2c709cb`.

## 3. Relationship to OASIS CACAO

Two separate conversations, worth distinguishing:

**Comparison/positioning** (documented in full in
[`plan-execution-model.md` §7](plan-execution-model.md#7-relationship-to-oasis-cacao),
commit `0092200`): real structural convergence (CACAO's `workflow`/
`on_success`/`on_failure` ≈ `Step`/`Transition`; CACAO `variables` ≈
`Variable`; CACAO's own `playbook_types` vocabulary — attack/investigation/
detection/mitigation — independently validates the production/assessment
Plan split arrived at in §1). Real divergence: CACAO has no epistemic layer
at all (no Hypothesis/predicted-vs-actual concept — this pattern's actual
novel contribution), its control flow is embedded step-ID references rather
than independently addressable, and its ATT&CK references are loose
pointers rather than a traversable graph chain. Positioned the same way
STIX 2.1 already is in this project: a plausible ingest format, not the
ceiling.

**Export feasibility** (T1003.001-shaped `OperationPlan` → CACAO JSON,
discussed but not built): genuinely constructible for a case shaped like
T1003.001 — the binary success/failure branching happens to map natively
onto CACAO's `on_success`/`on_failure` fields, no synthetic step needed.
Real gaps if this gets built: no executable command strings currently
captured on any `Step`/`Procedure` (would need a new datatype property);
object-valued `Variable` bindings (a `SecurityCondition` individual) don't
fit CACAO's flat `{type, value}` variable model without lossy flattening;
anything with more than two branches or a `guardOperator` comparison would
need synthesized `if-condition`/`switch-condition` steps, since our guard
lives on the `Transition` (edge) while CACAO's lives on the step (node);
and CACAO's `agent`/`target`/`created_by` are a different axis than
`attributedTo`/`actsOn` (automation-execution mechanism and document
authorship, vs. real-world responsibility) and would need a fixed
convention to populate. Separately, worth being explicit that exporting an
*offensive* `OperationPlan` to CACAO's `attack` type is a documentation/
adversary-emulation artifact (well-precedented — this is what Atomic Red
Team/Caldera-style content is), not something meant to be fired at a real
target by orchestration tooling; a `ControlPlan`/`DetectionPlan` export
wouldn't have that nuance and would be the more natural first target if the
actual goal is SOAR interop.

## 4. `develop`/`main` reconciliation — a process lesson

Before merging, checked rather than assumed the branch had been "purely
additive." It hadn't been. `develop` (commit `510915c`, predating this
session) had independently removed `rdfs:domain`/`rdfs:range` entirely from
six STIX relationship-type shortcut properties (`attributedTo`, `detects`,
`exploits`, `mitigates`, `targets`, `uses`) — a deliberate fix for
**confirmed RDFS++ entailment corruption in AllegroGraph** (multiple
`rdfs:domain`/`rdfs:range` triples on one property entail as an
intersection/AND, not the intended union/OR — a malware individual had been
entailed into both `IntrusionSet` and `AttackPattern` simultaneously, with
conflicting `stixType` literals asserted back onto it). This session's
provenance work (§2) had widened `attributedTo`'s range while keeping
domain/range closed — a real conflict with `develop`'s principle, made in
ignorance of it since the branch had never been diffed against `develop`.

Resolution: `git merge develop` into the feature branch (one real conflict,
exactly on `attributedTo`; confirmed via diff inspection that none of this
session's *other* new properties shared the multi-valued-domain/range
pattern that caused the bug, so the blast radius was narrow), resolved by
adopting `develop`'s open-domain/range principle with the Agent-vs-
ThreatActor guidance folded into scopeNote prose instead of an enforced
range (`8a2be47`), then a follow-up commit correcting `actsOn`'s scopeNote
and this documentation, both of which had cited `targets`' now-obsolete
closed domain/range (`47d4515`).

**Lesson for future long-lived feature branches:** check
`git log <base>..<feature>` *and* `git log <feature>..<base>` before
assuming a branch is purely additive relative to a base branch that may
have moved independently. A branch can be additive in its own diff while
still silently reintroducing something the base branch deliberately
removed.

**Final merge sequence** (no PR — small team, no review bandwidth, nothing
downstream consuming these concepts yet): `plan-execution-model` →
`develop` (clean fast-forward) → `main` (clean fast-forward) → branch
deleted, both locally and on `origin`, only after confirming all three
branches pointed at the identical commit (`47d4515`) so nothing was at risk
of being lost.

## 5. MVP scope for Moai / STONEWORK / the CTI Encyclopedia

A content-governance question surfaced a real policy, not just a technical
one — three different reasons landing on similar-looking restrictions:

| Content | Shared CTI Encyclopedia | Enterprise user-data graph |
|---|---|---|
| ATT&CK technique/procedure — abstract, narrative | Yes | — |
| ATT&CK technique — executable-depth `OperationPlan` | **No** — dual-use risk, same reasoning as Claude's own cyber safeguards | Yes — enterprise builds their own for red-team |
| NIST 800-53 Control — abstract | Yes | — |
| NIST Control — executable-depth `ControlPlan` | **Yes**, if NIST's own published text is specific enough to derive it — no IP encumbrance | Enterprise still customizes their own, referencing the Encyclopedia's version |
| CIS Control — abstract | Yes | — |
| CIS Control — executable implementation | **No** — CIS's monetized product, not ours to give away | Enterprise licenses CIS's own tooling, or builds their own |
| `ThreatScenario` (red-team), enterprise `ControlPlan` (blue-team) | — | Yes, referencing/extending Encyclopedia catalog entries |

Implications checked against `moai`'s own `CLAUDE.md` Phase 1 scope
("CTI Encyclopedia UI... no new ingest needed"), not proposed as a
contradiction of it:

- **STONEWORK (ontology):** already sufficient for MVP. Every class this
  policy needs (`AttackPattern`/`Procedure` for abstract ATT&CK,
  `Control`/`ControlPlan` for abstract-and-concrete NIST) already exists.
  This session's `OperationPlan`/`Transition`/`Hypothesis` depth is
  correctly scoped as an `examples/` proof-of-pattern, not a claim that the
  shared Encyclopedia should be populated that deep.
- **CTI Encyclopedia (data):** stay at abstract-catalog depth for ATT&CK
  and CIS. CIS executable-implementation content isn't a gap to fill — it's
  a boundary to hold, worth stating explicitly somewhere near
  `scripts/cis_to_ttl.py` in `skotarch` so it doesn't quietly get filled in
  later by someone who finds a CIS benchmark file and assumes more depth is
  strictly better. NIST-executable-depth is policy-approved and valuable,
  but is *new ingest* — a good Phase 1.5/Phase 2 target once
  `nist_to_ttl.py` is extended, not MVP-blocking.
- **Moai (UI):** no scope change — `CLAUDE.md`'s existing Phase 1 plan
  already covers browsing `Playbook`/`OperationPlan`/`ControlPlan`/
  `DetectionPlan`/`InvestigationPlan` as first-class STONEWORK entities.
- **Explicitly deferred, matching direction given this session:** the
  user-data graph holding enterprise-specific `OperationPlan`/`ControlPlan`/
  `ThreatScenario` instances is `moai-ingest` territory (already Phase 2),
  now for a second, independent reason beyond build sequencing — the
  content-governance line itself. Representing `AttackPattern` for test
  exercises and `DetectionPlan` for response is explicitly "after MVP."

## 6. Proposed, not yet built: content ownership/license

Follow-on from §5: how to make the CIS/NIST/ATT&CK governance distinction
*machine-checkable* rather than only institutional knowledge. Landed on a
design (not yet implemented) that turned out to mirror an existing
structural fact in the ontology: `stonework:attributedTo` (domain
`CyberActivity`) already answers "who *did* this" on the occurrent side:

- `stonework:ownedBy` (domain `CyberEntity`, range `Agent`) — the
  organization holding rights to a piece of content. Domain `CyberEntity`
  automatically covers `Control` and every `Behavior` subclass (`Playbook`/
  `OperationPlan`/`ControlPlan`/etc. are all `rdfs:subClassOf CyberEntity`),
  matching the "broader than Controls, relevant to Plans too" scope asked
  for, with no new classes needed on the Agent side (NIST/CIS/MITRE would
  each be an `Organization` individual).
- `stonework:hasLicenseType` + a `LicenseType` category in `categories.ttl`
  (individuals like `licenseTypePublicDomain`/`licenseTypeProprietary`/
  `licenseTypeOpen`), following the same `hasXType`/`XType` pattern already
  used for `MalwareType`/`InfrastructureType`/etc. Kept deliberately
  separate from `ownedBy` rather than one combined property — owner and
  license are correlated for CIS specifically but are independent axes in
  general, and a query might want to filter on either independently.

Deliberately distinguished from the existing `Provenance`/`authoredBy`
(domain `Provenance`, range `Agent`), which is a *different* concept —
bibliographic sourcing ("which report did we learn this fact from"), not
IP/governance status of the content itself. `Control`'s own scopeNote
already anticipated this concern in prose ("without embedding copyrighted
control text... referenced via citations rather than reproduced
verbatim") — this design turns that convention into something queryable.

**Open question, not yet resolved:** whether "source" should be a third,
separate concept from "owner" — a link to the specific cited document (e.g.
"NIST SP 800-53 Rev 5" as its own citable thing, closer to what
`Provenance`/`Publication` already models) rather than just the publishing
organization.

## 7. Open items carried forward

- `ownedBy`/`hasLicenseType` — designed, not built.
- Hypothesis revision/genealogy (a `revisesHypothesis`-type property for
  "refuted → form a new Hypothesis") — explicitly deferred.
- A home for complex output artifacts (plots, time series) — neither
  `DigitalArtifact` nor `IntelligenceProduct` is an exact fit; undecided.
- NIST-executable-depth `ControlPlan` ingest extending `nist_to_ttl.py` —
  policy-approved, not yet scheduled.
- Representing `AttackPattern` for test exercises and `DetectionPlan` for
  response, and the enterprise user-data graph generally — explicitly
  post-MVP.
