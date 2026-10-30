# STONEWORK Plan / Execution Model

How STONEWORK models a *plan* (what is intended), its *execution* (what actually
happened), and the *scientific-method* bridge between them — predicted outcomes
tested against actual ones. Worked example: ATT&CK T1003.001 (OS Credential
Dumping: LSASS Memory), encoded at `examples/operation-plan-t1003-001.ttl`.

For where this deep machinery sits in the larger picture — the
Tactic → Technique → Procedure → Plan → Execution gradient, and when the
lightweight `Process executionOf Technique` path is enough — see
[`technique-modeling.md`](technique-modeling.md).

---

## 1. The parti

The organizing idea, reduced to its essentials:

```
  PLAN side (Plan, a Behavior)                  EXECUTION side (CyberActivity)
  "what is intended"                             "what actually happened"

  Plan ◀──────────────────executionOf──────────────── run (Process / Investigation)
   └─ Step ◀────────────correspondsToStep──────┐         ▲
       │                                       │   partOfExecution
  hasInputVariable /                           └──── step execution
  hasOutputVariable                                  ▲          ▲
       ▼                                          boundIn   usedBinding (a later
   Variable ◀──bindingOf── VariableBinding ───────┘          step's execution)
       ▲                   boundTo / boundToLiteral
  predictsVariable
       │
   Hypothesis ──hasHypothesisStatus──▶ Pending / Confirmed / Refuted
```

Two independent splits, layered on top of each other:

- **Plan vs. Execution.** A `Plan` is a specification (a `Playbook`,
  `OperationPlan`, `ControlPlan`, `InvestigationPlan`/`DetectionPlan`,
  `BusinessProcess`, `Procedure` or `ThreatScenario`); a `CyberActivity`
  (`Process` or `Investigation`) is one run of it (`executionOf`), and each
  Step's execution is linked back via `correspondsToStep` and grouped under
  its run with `partOfExecution`. A Plan can be run any number of times; the
  values its Variables take in each run are `VariableBinding`s (section 2a).
  Since `stonework:Step` is itself declared `a stonework:Behavior`, this same
  pattern applies at any depth of a Plan's decomposition — not just the top level.
- **Predicted vs. Actual.** A `Hypothesis` names, in advance, what a `Variable`
  is expected to resolve to; an execution later binds that `Variable` to what
  actually happened, in a `VariableBinding` for that run. Comparing the two is what a `Transition`'s guard properties
  test, and what `hasHypothesisStatus` records explicitly.

**Production vs. assessment**, the other axis this session added: executing a
`Playbook`/`OperationPlan`/`ControlPlan` changes state in the world (an effect);
executing an `InvestigationPlan`/`DetectionPlan` produces a judgment about
something that already exists (an `Analysis` or `Assessment`).

---

## 2. T1003.001 — the executed trace

Three candidate procedures are tried in order until one succeeds. In this
trace, comsvcs.dll was blocked by EDR; procdump.exe succeeded on retry;
Mimikatz was never needed.

The run is `ex:run-opplan-t1003-001` (an `Operation`, `executionOf` the
OperationPlan); each attempt's execution is `partOfExecution` it, and each
sub-step's execution is `partOfExecution` its attempt.

```
step-attempt-comsvcs ──[false]──▶ step-attempt-procdump ──[SecurityCondition]──▶ step-credential-access-achieved
  var-comsvcs-outcome                var-procdump-outcome
  binding: false (blocked by EDR)    binding: cond-procdump-credential-material (success)
  hyp-comsvcs-outcome: REFUTED       hyp-procdump-outcome: CONFIRMED
```

The full branch structure — five `Transition`s, only two taken in this trace:

| Transition | From Step | Guard | To Step | Taken? |
|---|---|---|---|---|
| `t-comsvcs-to-procdump` | `step-attempt-comsvcs` | `guardLiteralValue false` on `var-comsvcs-outcome` | `step-attempt-procdump` | **Yes** |
| `t-procdump-success` | `step-attempt-procdump` | `guardType SecurityCondition` on `var-procdump-outcome` | `step-credential-access-achieved` | **Yes** |
| `t-comsvcs-success` | `step-attempt-comsvcs` | `guardType SecurityCondition` on `var-comsvcs-outcome` | `step-credential-access-achieved` | No — comsvcs failed |
| `t-procdump-to-mimikatz` | `step-attempt-procdump` | `guardLiteralValue false` on `var-procdump-outcome` | `step-attempt-mimikatz` | No — procdump succeeded first |
| `t-mimikatz-success` | `step-attempt-mimikatz` | `guardType SecurityCondition` on `var-mimikatz-outcome` | `step-credential-access-achieved` | No — never reached |

`var-mimikatz-outcome` is declared but has no `VariableBinding` in this run:
the absence of a binding *is* the forensic record that this branch was never
attempted.

---

## 2a. Runs, bindings and data flow (0.12.0)

Before 0.12.0, `boundTo` and `boundToLiteral` were said of the Variable
itself, and were functional, so a plan could be executed only once. A
Variable now belongs to the plan, and each value it takes is a
`VariableBinding`:

```turtle
ex:binding-procdump-outcome a stonework:VariableBinding ;
    stonework:bindingOf ex:var-procdump-outcome ;   # the plan's Variable
    stonework:boundIn   ex:act-attempt-procdump ;   # the execution that bound it
    stonework:boundTo   ex:cond-procdump-credential-material .
```

- **One binding per producing execution.** `boundIn` names the execution of
  the Step that outputs the Variable (or the run itself, for an input supplied
  when it starts). A Step executed three times in a retry loop binds its
  outputs three times in the same run.
- **Data flow between Steps** goes through a shared Variable, as in P-Plan:
  one Step declares it with `hasOutputVariable`, a later Step with
  `hasInputVariable`. In a run, the later Step's execution names the binding
  it received with `usedBinding` (mirroring `prov:used`); after a loop there
  are several candidates, so this is recorded rather than inferred from times.
- **Guards** are tested against the binding the from-Step's execution
  produced. **Hypotheses** are judged against the binding in the Investigation
  that tests them; when one run binds the Variable more than once, the Step's
  own execution tests the Hypothesis.
- **Why a binding node rather than P-Plan's pattern alone.** In P-Plan the
  run's own entity carries `p-plan:correspondsToVariable`. That works for an
  individual but not for a literal (`callbackVerified = false`), which can't
  carry properties; a binding treats both the same way.

The BEC worked example ([`bec-worked-example.md`](bec-worked-example.md))
runs one business process three times and one search Step twice, and shows
the queries this makes possible.

## 2b. Who performs a Step, and deviations (0.12.0)

- **Expected performers** are on the plan: a Step's `performerRole` names the
  Role whose holder should do it (BPMN's lane; PROV's `prov:hadRole`). Any one
  of several Roles will do; dual control is two Steps. `separatedFrom`
  (symmetric) says two Steps must be done by different Agents in any one run.
- **Actual performers** are on the execution, as observed. When the evidence
  shows only an identity (an account in a log), `performedBy` is that
  `DigitalIdentity`; its holder is reached through `accountOf` or
  `attributedToAgent`. When someone else used the identity, the execution
  keeps it as performer and names the Agent believed responsible with
  `attributedTo`.
- **Checks have three answers**: conforms, a deviation, or undetermined (no
  performer, an identity with no known holder, or an identity whose use is
  attributed to someone else). Someone using a role holder's own account passes
  the role and separation checks, so checks over logs never prove a run
  conformed.
- **A Deviation is a finding, not an absence.** A query can show that a
  required Step has no execution in a run; a `Deviation` (⊑
  `QualifiedAssertion`) records the analyst's finding that it wasn't done, or
  was done by the wrong Role, by the same Agent as a separated Step, out of
  order, or through a misused identity, with `evidencedBy` its evidence. The
  Investigation that establishes it `produces` it. Executions carry no
  status: there's no execution of a skipped Step, and a failed one has an
  outcome in its output Variable.

---

## 3. Entity-relationship diagram — one full vertical slice

The procdump thread end-to-end, since it's the one that actually resolved.
Every edge below is a real property in `ontologies/stonework.ttl`.

**Plan structure:**

```
ex:opplan-t1003-001 (OperationPlan)
  └─hasStep─▶ ex:step-attempt-procdump (Step, stepOrder 2)
                └─implements─▶ ex:proc-procdump (Procedure)
                                  ├─hasStep─▶ ex:step-procdump-locate-lsass (Step, stepOrder 1)
                                  └─hasStep─▶ ex:step-procdump-run (Step, stepOrder 2)
```

**Execution + Hypothesis bridge:**

```
ex:step-attempt-procdump ◀─correspondsToStep─ ex:act-attempt-procdump (Process)
        │                                                ▲
        │                                             boundIn
        │                                                │
        ├─hasOutputVariable─▶ ex:var-procdump-outcome ◀─bindingOf─ ex:binding-procdump-outcome (VariableBinding)
        │                            │                                        │
        │                            │       ex:cond-procdump-credential-material ◀─boundTo─┘ (SecurityCondition)
        │                            │                    ▲
        │                            │                    │ produces
        │                            │           ex:act-procdump-run (Process)
        │                            │                    │
        │                            │            correspondsToStep
        │                            │                    ▼
        │                            │           ex:step-procdump-run (Step)
        │                            │
        └────────────────────────────┴◀─predictsVariable── ex:hyp-procdump-outcome (Hypothesis)
                                                                predictedType: SecurityCondition
                                                                confidence: 75
                                                                hasHypothesisStatus: Confirmed
```

The comsvcs thread has the identical shape, except its binding ends in
`boundToLiteral false` instead of `boundTo` a `SecurityCondition`, and
`hyp-comsvcs-outcome`'s `hasHypothesisStatus` is `Refuted`.

---

## 4. Provenance: technique attribution vs. forensic attribution

Two different questions, both now answerable from the graph:

**"Which technique was this?"** — a real but *indirect* chain, mediated
through the Step/Procedure structure rather than a direct edge on the
Activity:

```
ex:act-attempt-procdump ─correspondsToStep─▶ ex:step-attempt-procdump ─implements─▶ ex:proc-procdump ─implements─▶ cti-enc:attack-pattern--65f2d882-...
```

`stonework:implements` (domain/range `Behavior`→`Behavior`) is deliberately
reused at both the Step→Procedure and Procedure→Technique levels, so this
chain falls out of the Plan structure for free — no Activity needs its own
edge to the technique.

**"Who did it, when, and against what?"** — this was previously missing, and
is now on every executed `Process` individual in the example:

```
ex:act-procdump-run
  stonework:attributedTo   ex:threat-actor        # who
  stonework:startedAtTime  "2026-08-01T14:00:17Z"  # when it began
  stonework:endedAtTime    "2026-08-01T14:00:45Z"  # when it ended
  stonework:actsOn         ex:rtproc-lsass         # what it acted on
  stonework:produces       ex:cond-procdump-credential-material
```

`stonework:attributedTo` has no closed `rdfs:domain`/`rdfs:range` — it's a
direct lift of the STIX 2.1 `attributed-to` relationship-type shortcut, and
`develop` established (commit `510915c`) that these shortcuts can't carry an
enforceable domain/range: STIX itself doesn't schema-constrain which
SDO/SCO types appear on them, and closed domain/range on properties like
this previously caused confirmed RDFS++ entailment corruption in
AllegroGraph. In practice the object is typically a `stonework:Agent`, most
often a `ThreatActor` in the adversarial case — but `CyberActivity` is a
general occurrence class covering offensive, defensive, and neutral
activities alike, so the performer need not be adversarial (a defender
running a `ControlPlan`, or an analyst running an `InvestigationPlan`, is
equally in scope). `stonework:actsOn` (mirrors `prov:used`) points at the
concrete technical asset an activity operated against — `ex:host-target`
(a `Host`) for the enumeration steps, `ex:rtproc-lsass` (a `RuntimeProcess`)
for the steps that acted directly on lsass.exe — and is deliberately
distinct from `stonework:targets`, which (also per `510915c`) is likewise an
open, STIX-lifted shortcut for higher-level strategic targeting (a Sector,
a Location) by a Campaign/ThreatActor, not a specific technical asset one
execution step touched. `actsOn` is purpose-built with a controlled
domain/range instead, the same way `mitigatesAttackPattern` is purpose-built
against the open `mitigates`.

---

## 5. What was added to STONEWORK to support this

### New classes

| Class | Superclass | Purpose |
|---|---|---|
| `stonework:InvestigationPlan` | `Behavior` | Assessment-plan counterpart to `Playbook`; executing one produces an `Investigation`. |
| `stonework:Hypothesis` | `IntelligenceProduct` | A falsifiable prediction about what a `Variable` will resolve to. |
| `stonework:HypothesisStatus` | `Category` (in `categories.ttl`) | Vocabulary class for the confirm/refute lifecycle. |

`stonework:DetectionPlan` was re-subclassed from `Behavior` to
`InvestigationPlan` — it's the narrow "is this a violation?" triage case;
`InvestigationPlan` is the general case (forensic analysis, malware analysis,
vulnerability assessment, ...).

### New properties

| Property | Domain → Range | Purpose |
|---|---|---|
| `stonework:correspondsToStep` | `CyberActivity` → `Step` (functional) | Links an executing Activity to the Step it's the concrete performance of. Mirrors `p-plan:correspondsToStep`. |
| `stonework:executionOf` / `stonework:hasExecution` | `CyberActivity` ↔ `Behavior` | Links an overall execution to its plan; complements the finer-grained Step link rather than replacing it. |
| `stonework:predictsVariable` | `Hypothesis` → `Variable` | Which Variable's eventual binding this Hypothesis predicts. |
| `stonework:predictedType` | `Hypothesis` → `rdfs:Class` | Predicted *class* of outcome (mirrors `guardType`) — the common case, since a Hypothesis formed before execution usually can't name a specific not-yet-constructed individual. |
| `stonework:predictedValue` | `Hypothesis` → `owl:Thing` | Predicted specific individual (mirrors `boundTo`) — rare case. |
| `stonework:predictedLiteral` | `Hypothesis` → `rdfs:Literal` | Predicted scalar (mirrors `boundToLiteral`). |
| `stonework:confidence` | domain unset → `xsd:integer` | 0–100 confidence used by Hypotheses and STIX-derived intelligence objects. |
| `stonework:hasHypothesisStatus` | `Hypothesis` → `HypothesisStatus` (in `categories.ttl`) | Explicit `Pending`/`Confirmed`/`Refuted` status — not inferred from which Transition fired. |
| `stonework:produces` | `CyberActivity` → `CyberEntity` | General "this activity constructed this thing" link. |
| `stonework:actsOn` | `CyberActivity` → `CyberEntity` | The asset/artifact an activity operated against. Mirrors `prov:used`. |
| `stonework:startedAtTime` / `stonework:endedAtTime` | `CyberActivity` → `xsd:dateTime` (functional) | When an activity began/ended. Mirror `prov:startedAtTime`/`prov:endedAtTime`. |

### Modified properties

| Property | Was | Now | Why |
|---|---|---|---|
| `stonework:attributedTo` | `CyberActivity` → `ThreatActor` | domain/range unset; `Agent` documented in scopeNote as the typical (not enforced) object type | Initially widened to `Agent` on this branch, since `CyberActivity` covers defensive/neutral activities too, not just adversarial ones. Reconciled against `develop` (merge commit `8a2be47`, pulling in `510915c`), which had independently removed domain/range from `attributedTo` and five other STIX relationship-type shortcut properties entirely — closed domain/range on a direct STIX lift caused confirmed RDFS++ entailment corruption in AllegroGraph and can't be accurate for arbitrary STIX 2.1 input regardless. The Agent-not-ThreatActor guidance survives as scopeNote prose instead of an enforced range. |

### Added in 0.12.0: a common Plan, and runs

| Term | Kind | Purpose |
|---|---|---|
| `stonework:Plan` | class, under `Behavior` | Common parent of every executable plan; aligned with `prov:Plan` and `p-plan:Plan`. |
| `stonework:BusinessProcess` | class, under `Plan` | An organization's routine work (paying a supplier), where attacks such as BEC succeed or fail. |
| `stonework:VariableBinding` | class | The value a Variable took in one execution. |
| `stonework:bindingOf` | `VariableBinding` → `Variable` (functional) | Which Variable. |
| `stonework:boundIn` | `VariableBinding` → `CyberActivity` (functional) | The execution that bound it. Mirrors `prov:wasGeneratedBy`. |
| `stonework:usedBinding` | `CyberActivity` → `VariableBinding` | A binding an execution received as input. Mirrors `prov:used`. |
| `stonework:partOfExecution` | `CyberActivity` → `CyberActivity` (functional) | A Step's execution to the run (or parent Step's execution) it belongs to. |
| `stonework:planVersion`, `stonework:planFormat` | `Plan` → string | Replace the deprecated `playbookVersion` and `playbookFormat`. |

| `stonework:performerRole` | `Step` → `Role` | The Role whose holder is expected to do the Step. |
| `stonework:separatedFrom` | `Step` ↔ `Step` (symmetric) | In any one run, the two Steps are done by different Agents. |
| `stonework:Deviation` | class, under `QualifiedAssertion` | An established finding that a run departed from its Plan. |
| `stonework:deviationRun` | `Deviation` → `Process` (functional) | The run. |
| `stonework:deviationStep` | `Deviation` → `Step` | The Step or Steps concerned. |
| `stonework:deviationExecution` | `Deviation` → `Process` | The executions concerned, if any. |
| `stonework:deviationKind` | `Deviation` → `DeviationKind` (functional; in `categories.ttl`) | Skipped, wrong role, same agent, out of order, misused identity. |

`evidencedBy` takes a `Deviation` as well as a `Sighting`.
`Playbook`, `ControlPlan`, `InvestigationPlan`, `Procedure` and
`ThreatScenario` moved from `Behavior` to `Plan`. `performedBy`,
`triggeredBy` and `triggersPlaybook` now take any Plan. `boundTo` and
`boundToLiteral` moved from `Variable` to `VariableBinding` (a breaking
change).

### Pre-existing machinery this pattern relies on

`Behavior`, `Step` (`hasStep`, `isStepOf`, `stepOrder`), `Transition`
(`fromStep`, `toStep`, `guardVariable`, `guardType`, `guardLiteralValue`,
`guardOperator`), `Variable` (`hasInputVariable`, `hasOutputVariable`),
`Procedure`/`Playbook`/`OperationPlan`,
`Process`/`Investigation`, `SecurityCondition`, `implements`.

**Deliberately not built yet:** Hypothesis revision/genealogy (a
`revisesHypothesis`-type property for "refuted → form a new Hypothesis" —
would matter for a multi-round investigation, not needed for this trace) and
a home for complex output artifacts (plots, time series) — neither
`DigitalArtifact` nor `IntelligenceProduct` is an exact fit.

---

## 6. Recipe — encoding another T-code

1. **Model the Plan.** Create a `stonework:OperationPlan` with `hasStep`
   pointing at one Step per candidate procedure attempt, plus a terminal
   "goal achieved" Step.
2. **Model each candidate Procedure.** A `stonework:Procedure` that
   `implements` the relevant `AttackTechnique`/CAPEC pattern from the CTI
   Encyclopedia; decompose it into its own Steps via `hasStep` if you want
   sub-step forensic depth.
3. **Declare the Variables.** Each Step you want to trace gets its outputs via
   `hasOutputVariable`; a Step that needs an earlier Step's result declares
   the same Variable with `hasInputVariable`. Values never go on the Variable
   itself, so a plan can be run again without overwriting earlier history.
4. **Wire Transitions.** `fromStep`/`toStep`, with `guardVariable` pointing
   at the *from*-Step's own Variable — `guardType` for "any successful
   outcome," `guardLiteralValue` for a specific scalar flag.
5. **(Optional) Model Hypotheses.** One `Hypothesis` per attempt-Step,
   `predictsVariable`-ing that Step's Variable, with `predictedType` (usual
   case) or `predictedValue`/`predictedLiteral`, plus a `confidence`.
6. **Encode the actual execution trace.** One `CyberActivity` for the run,
   `executionOf` the Plan. One more (`Process` for production plans,
   `Investigation` for assessment plans) per executed Step, via
   `correspondsToStep`, each `partOfExecution` the run or its parent Step's
   execution. For each value a Step's execution bound, a `VariableBinding`
   (`bindingOf`, `boundIn` that execution, `boundTo`/`boundToLiteral`); where a
   later execution received it, `usedBinding`. Set each tested Hypothesis's
   `hasHypothesisStatus` to `Confirmed`/`Refuted`. Link the Activity that
   built a result to it via `produces`. For forensic completeness, also set
   `attributedTo` (who), `startedAtTime`/`endedAtTime` (when), and `actsOn`
   (the concrete asset acted upon) on each executed Activity.
7. **Leave untaken branches alone.** A Step that was never attempted has no
   execution and no binding in that run, and a `Pending` (or absent)
   Hypothesis status: that absence is itself part of the forensic record.

---

## 7. Relationship to OASIS CACAO

[CACAO](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)
(Collaborative Automated Course of Action Operations) is OASIS's standard for
machine-readable security playbooks — JSON documents handed to a SOAR
orchestration engine for direct execution. Surface-level, it looks like it
covers the same ground as this pattern. It doesn't, and the differences are
informative.

**Where they converge — structural parallels arrived at independently:**

| CACAO concept | STONEWORK equivalent |
|---|---|
| `workflow` step, `on_success`/`on_failure`/`on_true`/`on_false` | `Step` + `Transition` (`fromStep`/`toStep`/`guardType`/`guardLiteralValue`) |
| `variables` (playbook- or step-scoped, typed) | `Variable` (`hasInputVariable`/`hasOutputVariable`), with each run's values as `VariableBinding`s |
| `agent` on a `command` (what executes it) | `stonework:attributedTo` |
| `target` on a `command` (what it acts against) | `stonework:actsOn` |
| `playbook_types` open vocabulary (`attack`, `investigation`, `detection`, `mitigation`, `prevention`, ...) | The production/assessment split — `OperationPlan` ≈ `attack`; `InvestigationPlan`/`DetectionPlan` ≈ `investigation`/`detection`; `ControlPlan` ≈ `mitigation`/`prevention` |

CACAO's own vocabulary independently landing on an offense/investigation/defense
split is external validation that this distinction isn't idiosyncratic to
STONEWORK — it's one the field converges on from multiple directions.

**Where they diverge:**

1. **Format and purpose.** CACAO is JSON, designed for a SOAR engine to
   execute directly — its center of gravity is *vendor interop for
   automation*. This pattern is native RDF/OWL, living inside the same graph
   as the CTI Encyclopedia — its center of gravity is *knowledge
   representation and reasoning*. A CACAO playbook is a document sent
   somewhere to be run; a STONEWORK `OperationPlan` is a graph node that can
   be SPARQL-queried, reasoned over, and semantically joined to CVE/CWE/
   ATT&CK data natively.
2. **Control flow is embedded, not addressable.** CACAO's `on_success`/
   `on_failure` are step-ID string references embedded inside the step
   object itself. `Transition` is a first-class RDF resource with its own
   URI — annotatable and independently referenceable. A `Hypothesis` can't
   attach to a CACAO branch; it can attach to `ex:t-comsvcs-to-procdump`.
3. **No epistemic layer.** CACAO has no concept of a predicted outcome
   distinct from an actual one, no confidence scoring, no confirm/refute
   status — it's a "do this, then do that" execution graph. `Hypothesis` /
   `predictsVariable` / `confidence` / `hasHypothesisStatus` have no CACAO
   counterpart.
4. **Technique attribution is a loose pointer, not a graph traversal.**
   CACAO references ATT&CK techniques via `external_references` — an ID
   sitting in a metadata field, not something traversable. The `implements`
   chain (§4) is a real property path a SPARQL query walks, landing on an
   actual `cti-enc:` individual embedded in the encyclopedia graph.
5. **Variables are key-values, not addressable resources.** A CACAO variable
   is `{name, type, value}` sitting inside a step, with no identity outside
   its containing document. A STONEWORK `Variable` is its own URI-bearing
   individual — which is exactly what makes `predictsVariable` possible at
   all.

**Positioning:** the same relationship this project already has with STIX
2.1 applies here — "supported import/export format, not the ceiling." A
CACAO playbook's `workflow` maps reasonably cleanly onto `Step`/`Transition`/
`Variable`, making CACAO a plausible *ingest* format. What it structurally
cannot provide is the execution-trace layer described in this document: what
a SOAR engine *actually did* when it ran that playbook — attributed,
timestamped, confirmed-or-refuted against what was expected, and joined
natively to the rest of the threat-intel graph.
