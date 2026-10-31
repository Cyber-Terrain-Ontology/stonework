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
  order, through a misused identity, or against the wrong target, with
  `evidencedBy` its evidence. The
  Investigation that establishes it `produces` it. Executions carry no
  status: there's no execution of a skipped Step, and a failed one has an
  outcome in its output Variable.

## 2c. Plans as programs: sequence, branching, loops, parallel branches (0.12.0)

A plan's control flow has the three constructs any sequential program needs,
plus the one a plan for a team needs:

| Construct | How a plan says it |
|---|---|
| Sequence | A `Transition` (fromStep → toStep), `precededByStep`, or `stepOrder` for a plain numbered list |
| Conditional branching | A guarded `Transition`: `guardVariable`, with `guardType`, `guardLiteralValue` or `guardValue` and optionally `guardOperator`; a Step's `defaultTransition` for "otherwise"; `outcomeVariable` for whether a Step worked |
| Looping | A `Transition` back to a Step already reached; each pass is its own execution with its own bindings |
| Parallel branches | `splitKind` and `joinKind` on a Step, or a `precededByStep` dependency graph |

Sequence, branching and looping say what may happen next; they assume one
thread of control. Parallel branches say what doesn't depend on what. A plan
carried out by several people or systems needs that: written as a sequence,
two independent Steps claim an order nobody intends, and a run that did them
the other way round would look like an out-of-order deviation. The join is
the part that matters most: "don't warn the suppliers until both the reset
and the block are done" is a real control requirement.

- **`splitKind`** (Step → `FlowKind`): when the Step finishes, *exclusive*
  takes exactly one outgoing Transition, one whose guard holds; *parallel*
  takes every one whose guard holds, as concurrent branches. An unguarded
  Transition always holds, so a parallel split with unguarded Transitions is
  BPMN's parallel gateway and one with guarded Transitions is its inclusive
  gateway.
- **`joinKind`** (Step → `FlowKind`): *exclusive* lets the Step start as soon
  as one incoming Transition is taken; *parallel* makes it wait until the
  execution of every Step it's entered from, by a Transition taken in the
  same run, has ended. "Taken in the same run" is read from the record, so a
  join after an inclusive split waits only for the branches that started.
- **Both default to exclusive**, the meaning Transitions had before, so
  existing plans are unchanged.
- **No gateway nodes.** As in YAWL, a split or join is a property of the Step
  it belongs to, so every Step stays a unit of action. A BPMN gateway maps
  onto the `splitKind` or `joinKind` of the Step next to it.
- **Without guards, `precededByStep` is enough.** A Step with several
  `precededByStep` values follows all of them, and Steps with no path
  between them may run in parallel.

Two checks against a run follow from this. A parallel join whose execution
started before a taken branch's execution ended is a candidate *out-of-order*
`Deviation`, and an undetermined one if either time is missing. A branch a
parallel split took, with no execution in the run, is a candidate *skipped*
`Deviation`. The [BEC worked example](bec-worked-example.md#4-the-control-plan)
has both queries.

## 2d. Messages between plans (0.12.0)

Plans belong to participants: an organization's business process, its
playbooks, a supplier's own process, an adversary's operation. Between them,
only data passes:

- **Control flow stays inside a plan.** A `Transition` never leaves its Plan.
  One participant can't make another's Step run; it can only send something
  that Step takes as input.
- **A message is data flow that crosses Plans.** The sending Step declares a
  Variable with `hasOutputVariable`, the receiving Step (in another Plan)
  declares the same Variable with `hasInputVariable`, and in a run the
  receiving execution records `usedBinding` of the binding made in the
  sending execution. This is BPMN's message flow between pools, with no new
  terms: a query tells a message from internal data flow by comparing the
  two Steps' `isStepOf`.
- **`suppliedBy`** (Variable → Role) is for a sender whose plan isn't
  modelled (BPMN's black-box pool): the value comes from a holder of that
  Role, such as a supplier or a customer, and is bound in the execution that
  received it.

A Variable can have both: a payment request is `suppliedBy` the supplier,
and an adversary's OperationPlan can produce one too. The Steps whose inputs
come from outside the organization are its attack surface for messages, and
an adversary Step that outputs the same Variable is an attack path into it.
The [BEC worked example](bec-worked-example.md#5-the-actors-plan-and-the-message-that-crosses-into-ours)
has both queries. How a message travels (email, phone, an authenticated
portal) matters for its risk and is not modelled yet.

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
| `stonework:deviationKind` | `Deviation` → `DeviationKind` (functional; in `categories.ttl`) | Skipped, wrong role, same agent, out of order, misused identity, wrong target. |
| `stonework:hypothesisAbout` | `Hypothesis` → anything | What a hypothesis concerns, for finding it; several values, no roles. |
| `stonework:hypothesisPart` | `Hypothesis` → `Hypothesis` | A claim a compound hypothesis is the conjunction of; refuted parts say which claim failed. |
| `stonework:IdentityControl` | class, under `QualifiedAssertion` | That an Agent controlled a DigitalIdentity during an interval (`validFrom`, `validUntil`), with evidence; not exclusive of the holder. |
| `stonework:controllingAgent` | `IdentityControl` → `Agent` (functional) | Who controlled it. |
| `stonework:controlledIdentity` | `IdentityControl` → `DigitalIdentity` (functional) | The identity, such as a UserAccount. |
| `stonework:defaultTransition` | `Step` → `Transition` (functional) | The Transition taken when no other outgoing guard holds. |
| `stonework:guardValue` | `Transition` → any individual (functional) | A guard that tests identity with an individual, such as a category value. |
| `stonework:outcomeVariable` | `Behavior` → `Variable` (functional; ⊑ `hasOutputVariable`) | The output Variable whose value is an `ExecutionOutcome`: succeeded, failed, timed out. |
| `stonework:stepTarget` | `Step` → `CyberEntity` | What a Step is meant to act on: an entity, or a Variable whose value in the run is the target. |
| `stonework:hasPlaybookType` | `Plan` → `PlaybookType` (in `categories.ttl`) | CACAO's eight playbook types; several allowed. |
| `stonework:splitKind` | `Step` → `FlowKind` (functional; in `categories.ttl`) | Exclusive (one outgoing Transition) or parallel (every one whose guard holds). Default exclusive. |
| `stonework:suppliedBy` | `Variable` → `Role` | The participants who supply a value from outside the Plan, when their own plan isn't modelled. |
| `stonework:joinKind` | `Step` → `FlowKind` (functional; in `categories.ttl`) | Exclusive (start on any incoming Transition) or parallel (wait for every branch taken in the run). Default exclusive. |

`evidencedBy` takes a `Deviation` or an `IdentityControl` as well as a `Sighting`.
`Mitigation` (and so `CourseOfAction`) is a `Behavior` as well as a
`Countermeasure`, so a ControlPlan or Step `implements` an ATT&CK
mitigation as it does a NIST control.
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

*Checked against CACAO Security Playbooks Version 2.0, Committee Specification 01
(27 November 2023), the latest version; revised 2026-10-31 for 0.12.0.*

[CACAO](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)
(Collaborative Automated Course of Action Operations) is OASIS's standard for
machine-readable security playbooks: JSON documents shared between
organizations and run by orchestration tools. It covers the plan. STONEWORK
covers the plan too, and also what happened when it was run, which CACAO
leaves out: the spec says that deciding whether a step succeeded, failed or
completed "is implementation specific and is out of scope for this
specification", and it has no object for a run.

### Control flow: structured blocks vs. a graph

Both are programs in the sense of §2c, with sequence, branching, looping and
parallel branches. They differ in shape:

- **CACAO is block-structured.** Its control steps (`if-condition`,
  `while-condition`, `switch-condition`, `parallel`) own their branches. Each
  branch MUST end at its own `end` step, and control then returns to the step
  that opened it, which carries on through its `on_completion` (or
  `on_success` / `on_failure`). A `parallel` step waits for all its branches;
  a `while-condition` runs its `on_true` branch while its condition holds.
  This is structured programming: every block has one way in and one way out.
- **STONEWORK is a graph.** Steps are actions linked by `Transition`s; a
  guard on a Transition is a branch, a Transition back to an earlier Step is
  a loop, and `splitKind` / `joinKind` mark parallel branches. There are no
  control nodes, and nothing requires the graph to be well nested.

So every CACAO workflow can be written in STONEWORK, but only a well-nested
STONEWORK plan can be written in CACAO.

### How each CACAO construct maps

| CACAO 2.0 | STONEWORK | Fit |
|---|---|---|
| `playbook` | `Playbook` (⊑ `Plan`) | Good |
| `playbook_types` (attack, detection, engagement, investigation, mitigation, notification, prevention, remediation; several allowed) | `hasPlaybookType`, with the same eight values; the Plan subclasses correspond (`OperationPlan` attack, `DetectionPlan` detection, `InvestigationPlan` investigation, `ControlPlan` mitigation, prevention or remediation) | Exact |
| `workflow` (steps keyed by ID), `workflow_start` | `hasStep`; the start is the Step no Transition enters | Good |
| `start` / `end` steps | Implicit | Generated on export |
| `action` step: `commands`, `agent`, `targets` | `Step`; `performerRole` for who should do it; `stepTarget` for what it should act on (an entity, or a Variable bound in the run), checked against `actsOn` on the execution | Partial: commands have no STONEWORK form |
| `owner` on a step (a STIX Identity, "the owner or responsible party") | Closest is `performerRole`, but that names a Role, not a party | Partial |
| `playbook-action` (`playbook_id`, `playbook_version`) | A Step that `implements` another Plan; its execution is `executionOf` that Plan; `planVersion` | Good |
| `on_completion` | Unguarded `Transition` | Exact |
| `on_success` / `on_failure` | Transitions guarded with `guardValue` on the Step's `outcomeVariable` (*succeeded*, *failed*, *timed out*) | Good |
| `if-condition` (`condition`, `on_true`, `on_false`) | Exclusive split: one guarded Transition, and one guarded on the opposite | Partial: CACAO conditions are STIX Patterning expressions; a STONEWORK guard compares one Variable with one value |
| `switch-condition` (`switch`, `cases`, optional `default`) | Exclusive split, one guarded Transition per case (`guardValue` or `guardLiteralValue`); the `default` case is the Step's `defaultTransition` | Good |
| `while-condition` (`condition`, `on_true`) | A guarded Transition back to an earlier Step | Good; each pass is its own execution |
| `parallel` (`next_steps`, waits for all) | `splitKind parallel` on the Step before, `joinKind parallel` on the Step its `on_completion` names | Good |
| `workflow_exception` (where a failure goes when a step has no `on_failure`) | None | Gap |
| `delay`, `timeout` (milliseconds; a timeout invokes `on_failure`) | None | Gap |
| `playbook_variables`, `step_variables`, `in_args`, `out_args` | `Variable`, `hasInputVariable`, `hasOutputVariable`; at run time `VariableBinding` and `usedBinding` | Good. CACAO variables are reassigned as the playbook runs; STONEWORK keeps every value as its own binding. `external` (passed in by the caller) is a Plan's `hasInputVariable`; `constant` has no equivalent |
| `agent_definitions`, `target_definitions` (group, individual, organization, location, sector; http-api, linux, net-address, security-category, ssh) | `Role` for the expected performer; `performedBy` and `actsOn` on executions | Different on purpose: CACAO names the executor; STONEWORK separates the Role a plan expects from the identity a run observed |
| `created_by` (a STIX Identity), `markings` (TLP 2.0, IEP), `signatures`, `authentication_info_definitions` | STONES provenance and markings | Signatures and authentication carried as opaque content |
| `external_references` (how a step or playbook cites ATT&CK) | `implements`, a property path to the Encyclopedia's own technique, analytic or control | STONEWORK is stronger: a traversable link, not a cited ID |

### What only STONEWORK has

- **Runs.** A run is an execution that is `executionOf` the plan, with its
  Steps' executions `partOfExecution` it and each value a `VariableBinding`.
  A plan run many times keeps every run apart, so runs can be compared step
  by step.
- **Checks against the plan, and deviations.** Skipped Steps, wrong Roles,
  segregation of duties (`separatedFrom`), joins that didn't wait, and
  misused identities, each recorded as a `Deviation` with its evidence.
  Checks answer conforms, deviates or undetermined, because a log often shows
  only an account.
- **Hypotheses.** A predicted outcome, separate from the actual one, with
  confidence and a confirmed / refuted status, what it's about, and parts
  that can be judged separately. CACAO has no epistemic layer.
- **Business processes as plans.** CACAO's playbooks are security
  orchestration; an organization's routine work, where attacks such as BEC
  succeed or fail, is outside its scope.
- **Addressable edges.** A CACAO step has an ID, but its links are strings
  inside it. A `Transition` is a resource with its own IRI, so a Hypothesis or
  a Deviation can refer to it.

### Compatibility

- **CACAO into STONEWORK:** control flow maps almost without loss. Each
  control step folds into the splits, joins and guards of the Steps around
  it, and `end` steps disappear. Three things don't fit yet: compound
  conditions, `workflow_exception`, and delays and timeouts (proposals 17
  to 19 in the BEC example). Commands, authentication and signatures would
  be carried along unread.
- **STONEWORK into CACAO:** a well-nested plan exports, with Roles as
  `group` agents, a parallel split as a `parallel` step, and an inclusive
  split as a `parallel` step whose branches each open with an
  `if-condition`. A plan whose graph isn't well nested needs restructuring
  first. Runs, deviations, hypotheses and `separatedFrom` have no CACAO
  form, as expected for a plan format.

**Positioning:** the same relationship as STONEWORK has with STIX 2.1: a
supported import and export format, not the ceiling. The natural pairing is
a CACAO playbook as the plan and STONEWORK as the record of its runs, judged
against it and joined to the rest of the threat-intelligence graph.
