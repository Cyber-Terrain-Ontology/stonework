# Changelog

## 0.12.0 (core): plans and runs

A common parent for plans, and per-run Variable values, so a plan can be executed any number of times; the Roles that perform Steps; deviations from a plan as findings with evidence; parallel branches; messages between plans; default branches, step outcomes and targets; playbook types; and what a hypothesis is about, with compound hypotheses made of parts. See [docs/plan-execution-model.md](docs/plan-execution-model.md) and the revised [BEC worked example](docs/bec-worked-example.md) (proposals 1, 2, 4, 5, 6, 7, 9, 10 and 13 to 16).

### Added

- `stonework:Plan` (⊑ `Behavior`; aligned with `prov:Plan` and `p-plan:Plan`): the common parent of every executable plan.
- `stonework:BusinessProcess` (⊑ `Plan`): an organization's routine work, such as paying a supplier.
- `stonework:VariableBinding`, with `stonework:bindingOf` and `stonework:boundIn` (both functional): the value a Variable took in one execution.
- `stonework:usedBinding`: a binding an execution received as input (mirrors `prov:used`), for data flow between Steps.
- `stonework:partOfExecution` (functional): a Step's execution to the run, or the parent Step's execution, it belongs to.
- `stonework:planVersion` and `stonework:planFormat` (domain `Plan`).
- `stonework:performerRole` (Step → Role): the Role whose holder is expected to perform a Step.
- `stonework:separatedFrom` (symmetric, Step ↔ Step): segregation of duties; in any one run, the two Steps are performed by different Agents.
- `stonework:Deviation` (⊑ `QualifiedAssertion`): an established finding that a run departed from its Plan, with `stonework:deviationRun` (functional), `stonework:deviationStep`, `stonework:deviationExecution` and `stonework:deviationKind` (functional).
- `stonework:splitKind` and `stonework:joinKind` (both functional, Step → `FlowKind`; in `categories.ttl`): whether a Step's outgoing Transitions are alternatives or concurrent branches, and whether a Step entered by several Transitions waits for all of them. Both default to exclusive, the meaning Transitions already had.
- `stonework:suppliedBy` (Variable → Role): the participants who supply a value from outside the Plan, when their own plan isn't modelled (BPMN's message flow from a black-box pool).
- `stonework:hypothesisAbout` (Hypothesis → anything, not functional): what a hypothesis concerns, for finding it.
- `stonework:hypothesisPart` (Hypothesis → Hypothesis): the claims a compound hypothesis is the conjunction of, each judged separately, so a refuted compound shows which part failed.
- `stonework:defaultTransition` (functional, Step → Transition): the Transition taken when no other outgoing guard holds (CACAO's switch default, BPMN's default flow).
- `stonework:guardValue` (functional, Transition → any individual): a guard that tests identity with an individual; mirrors `predictedValue`.
- `stonework:outcomeVariable` (functional, ⊑ `hasOutputVariable`): the output Variable recording whether an execution succeeded, failed or timed out (CACAO's on_success / on_failure).
- `stonework:stepTarget` (Step → CyberEntity): what a Step is meant to act on, an entity or a Variable bound in the run; the plan-level counterpart of `actsOn`.
- `stonework:hasPlaybookType` (Plan → PlaybookType; in `categories.ttl`): CACAO 2.0's playbook types, several allowed.
- Categories: `stonework:DeviationKind` scheme (Skipped, Wrong role, Same agent, Out of order, Misused identity, Wrong target); `stonework:ExecutionOutcome` scheme (Succeeded, Failed, Timed out); `stonework:PlaybookType` scheme (Attack, Detection, Engagement, Investigation, Mitigation, Notification, Prevention, Remediation); `stonework:FlowKind` scheme (Exclusive, Parallel).
- SHACL: `VariableBindingShape` (exactly one Variable and execution, exactly one value), `PartOfExecutionShape`, `UsedBindingShape`, `DeviationShape` (exactly one run and kind, at least one Step), `PerformerRoleShape`, `SeparatedFromShape`, `SplitKindShape`, `JoinKindShape`, `SuppliedByShape`, `DefaultTransitionShape`, `OutcomeVariableShape`, `StepTargetShape`, `HasPlaybookTypeShape`, `HypothesisPartShape`, and `guardValue` at most once on `TransitionShape`; fixtures for each.

### Changed

- **Breaking:** `stonework:boundTo` and `stonework:boundToLiteral` take a `VariableBinding`, not a `Variable`. `VariableShape` now rejects either on a Variable.
- `Playbook`, `ControlPlan`, `InvestigationPlan`, `Procedure` and `ThreatScenario` are subclasses of `Plan` rather than directly of `Behavior` (still Behaviors).
- `stonework:performedBy`, `stonework:triggeredBy` and `stonework:triggersPlaybook` take any `Plan`, not only a `Playbook`.
- `stonework:evidencedBy` takes a `Deviation` as well as a `Sighting`.
- Scope notes on `stonework:Variable` and `stonework:Transition`: data flow between Steps of different Plans is a message between participants; control flow never crosses Plans.
- Scope note on `stonework:precededByStep`: a Step with several values follows all of them, and Steps with no path between them may be performed in parallel.
- Scope notes on `performedBy` and `attributedToAgent`: an execution names its performer as observed, often an identity; an identity used by someone other than its holder stays the performer, and the Agent responsible is `attributedTo`.
- Scope notes on `Behavior`, `Step`, `Process`, `Variable`, `Transition`, `Hypothesis` and `executionOf` describe runs and bindings. A Hypothesis is judged by its Variable's binding in the Investigation that tests it.
- Examples: the T1003.001 trace has a run, nested step executions and bindings; the BEC example runs its business process three times and its search Step once per mailbox, gives each business Step its Role, records the wire's release by the controller's bank-portal login, records the skipped callback as a Deviation, and runs its containment plan's credential reset and transport block as parallel branches joined before the review, and adds the actor's `OperationPlan`, whose sending Step outputs the payment request the business process takes as input. Its detection search has an outcome Variable, a failure branch and a default branch; its containment Steps name their targets; its plans carry playbook types. Its hypotheses say what they're about, and a compound hypothesis splits the activity (confirmed) from the attribution (pending).

### Deprecated

- `stonework:playbookVersion` and `stonework:playbookFormat`: now sub-properties of `planVersion` and `planFormat`.

## 0.11.0 (core), categories 0.2.0

Investigations as first-class records; see [docs/investigation-management.md](docs/investigation-management.md).

### Added

- `stonework:InvestigationStatus` scheme (Open, Active, On Hold, Closed) and `stonework:hasInvestigationStatus`.
- `stonework:InvestigationOutcome` scheme (Confirmed, Benign, False Positive, Inconclusive) and `stonework:hasInvestigationOutcome`.
- `stonework:PriorityLevel` scheme (Critical, High, Medium, Low) and `stonework:hasPriority`, for an Investigation or Incident.
- `stonework:leadInvestigator` (⊑ `stonework:performedBy`), `stonework:examines`, `stonework:testsHypothesis`, `stonework:mergedInto`.
- `stonework:refersTo`: an object to the canonical entity it refers to, in place of `owl:sameAs` (Discussion #90).
- SHACL: `InvestigationShape` (at most one status, outcome, lead, merge target), `InvestigationOutcomeShape` (warnings), `PriorityShape`; fixtures for each.

### Changed

- `stonework:investigates` / `stonework:investigatedBy`: the subject is no longer restricted to Campaign, Incident, MalwareSample or ThreatActor.
- `stonework:Investigation`'s scope note lists the properties that describe one.
- `stonework:opinionOf` may target a `stonework:QualifiedAssertion` as well as an `IntelligenceProduct`: an analyst's confirmation or rejection of one asserted link.
- `HypothesisShape`: a Hypothesis predicts at most one Variable, and need not predict one (a hypothesis tested directly by an Investigation).

Earlier releases are described in their pull requests and tags.
