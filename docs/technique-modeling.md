# Modeling Techniques and Behaviors

How STONEWORK layers *what an adversary (or defender, or launderer) does* — from
a high-level objective down to a concrete executed trace — and how deep to model
at each layer. Complements [`plan-execution-model.md`](plan-execution-model.md),
which covers the Step / Transition / Variable / Hypothesis machinery in detail;
this document is the layer map and the "how much to build" guidance.

---

## 1. The gradient

`stonework:Behavior` is the plan-specification / method-specification bucket (a
BFO generically dependent continuant, aligned with IAO plan specification). Its
subclasses form a gradient from abstract objective to concrete directive:

```
  Tactic          objective — what is being achieved            no step structure
    │  hasTechnique
    ▼
  Technique       method — the approach, in general terms       no step structure
    │  implements / procedureFor  (0..N)
    ▼
  Procedure       one realization path for one Technique        prose, or Step-decomposed
    │  implements  (a Plan's Step implements a Procedure)  (0..N)
    ▼
  Playbook /      objective-scoped orchestration of several     Step + Transition + Variable
  OperationPlan / Procedures/Techniques with branching & retry
  ControlPlan
    │  executionOf / correspondsToStep
    ▼
  ───────────────────────────────────────────────────────────────────────────────
  Process /       what actually happened                        CyberActivity (occurrent)
  CyberActivity   attributed, timestamped, acts-on
```

The cardinalities matter: **one Technique has zero-to-many Procedures, and a
Procedure has zero-to-many Plans that invoke it.** A Technique is not a plan and
does not become one — the step structure lives one or two layers below it.

### The same gradient, three domains

| Layer | Offensive (ATT&CK) | Defensive (D3FEND / controls) | Illicit finance (FATF) |
|---|---|---|---|
| Objective | `OffensiveTactic` (Credential Access) | `DefensiveTactic` (Detect, Isolate) | `LaunderingStage` (Placement, Layering) |
| Method | `AttackTechnique` (T1003.001) | `DefendTechnique` / `Control` (NIST AC-2) | `IllicitFinanceTechnique` (structuring) |
| Realization | `Procedure` (comsvcs.dll MiniDump) | `ControlPlan` | `Procedure` (a specific mule cash-out routine) |
| Orchestration | `OperationPlan` | `Playbook` / `DetectionPlan` | `Playbook` |
| Execution | `Process` | `Process` / `Investigation` | `CyberActivityCluster` of `FinancialTransaction` |

Whatever depth policy applies to ATT&CK applies equally to the other two columns.

---

## 2. Why a Technique is not a Plan

An ATT&CK technique's content is a *capability statement* — "adversaries may
access credential material stored in LSASS process memory" plus a list of tools.
It has no inherent ordered, branched step sequence. That sequence only exists
once a concrete realization is chosen:

- T1003.001 via **comsvcs.dll MiniDump** — one Procedure
- T1003.001 via **procdump.exe** — a different Procedure
- T1003.001 via **Mimikatz `sekurlsa::logonpasswords`** — a third

Three Procedures, one Technique. Collapsing the Technique into a plan would force
a single canonical step sequence that MITRE deliberately does not specify, and
would break the "many realizations of one method" fan-out that queries rely on.

Roughly 200 ATT&CK techniques and 450 sub-techniques have no single canonical
executable procedure — they have dozens of tool-specific ways. "Technique = Plan"
imposes a one-to-one the domain does not support.

---

## 3. Two execution paths — lightweight and deep

### Lightweight: `Process executionOf Technique`

The common case for sightings, incident timelines, and threat reports. No
Procedure, no Plan, no Step:

```turtle
ex:act-cred-dump
    a stonework:Process ;
    stonework:executionOf     cti-enc:attack-pattern--T1003.001 ;
    stonework:attributedTo    ex:apt-group ;
    stonework:actsOn          ex:host-dc01 ;
    stonework:startedAtTime   "2026-08-01T14:02:00Z"^^xsd:dateTime .
```

"This actor performed T1003.001 against DC01 at this time." That is a complete,
useful assertion. It can be elaborated into a Step-decomposed Plan later — adding
`correspondsToStep`, Procedures, Hypotheses — **without retracting the
`executionOf` triple**. Nothing about the lightweight form blocks going deeper.

### Deep: Plan / Step / Procedure / Hypothesis

For adversary emulation, red-team planning, forensic reconstruction, and
predicted-vs-actual analysis. This is the machinery in
[`plan-execution-model.md`](plan-execution-model.md): an `OperationPlan` with
`hasStep`, `Transition` guards, per-Step output `Variable`s, `Hypothesis`
predictions, and one `CyberActivity` per executed Step via `correspondsToStep`.
The worked example is `examples/operation-plan-t1003-001.ttl`.

Use the deep path when the branching, the retry logic, or the gap between what
was expected and what happened is itself the thing being modeled.

---

## 4. How deep to populate

Depth is a governance decision as much as a modeling one (see the 2026-08-01
design log, §5–6).

| Content | Shared CTI knowledge graph | Enterprise / red-team graph |
|---|---|---|
| Tactic, Technique — abstract | Yes | Yes |
| ATT&CK "procedure example" — a `Procedure` with a prose `description`, `procedureFor` a Technique, `attributedTo` an actor, no Steps | Yes — this is the bulk of ingested procedure data | Yes |
| Step-decomposed `Procedure` (Atomic Red Team atomic, Caldera ability) | Case by case | Yes |
| Executable-depth `OperationPlan` for an offensive technique | **No** — dual-use risk | Yes — the enterprise builds its own for emulation |
| `ControlPlan` derived from published control text (e.g. NIST) | Yes, where the source text is specific enough | Enterprise customizes its own |
| `ControlPlan` / implementation for a monetized catalog (e.g. CIS benchmarks) | **No** — not ours to redistribute | Enterprise licenses the source or builds its own |

The default for the shared graph is **abstract methods plus prose procedure
examples**. Step-decomposed depth and executable plans are added deliberately,
where they are valuable and permitted — not generated wholesale.

---

## 5. What is deliberately left alone

- **The `AttackPattern` / `Technique` / `AttackTechnique` structure.**
  `stonework:AttackTechnique` multiply-inherits from `stonework:AttackPattern`
  (the CAPEC-and-ATT&CK-spanning shape) and `stonework:CyberTechnique`. This is a
  known awkwardness, but it carries real weight — a single query can span CAPEC
  taxonomy entries and ATT&CK techniques — and practitioners already reason
  fluently in ATT&CK terms. Revisiting it would ask the community to rethink a
  vocabulary they know cold, for a modeling nicety. Not now.
- **A `Transition` individual-valued guard.** Guards test a class
  (`guardType`) or a scalar (`guardLiteralValue`); there is no guard analogous to
  `Hypothesis`'s `predictedValue` (a specific individual). Add one only if a real
  case needs it.
- **Hypothesis revision genealogy**, and a home for complex output artifacts —
  both noted as deferred in `plan-execution-model.md`.
