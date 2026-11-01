# Changelog

## 0.13.0 (core), categories 0.4.0, STIX framework 0.4.0: email evidence

An `EmailMessage` carries its headers as data, so a message taken from a mailbox is evidence that can be queried: who it claimed to be from, where replies went, which thread it joined, and what the receiving server's authentication checks found. Received headers are Events derived from the message, which is also how a parsed log record points back to its log. A mailbox rule, the artifact at the centre of T1114.003, has its own class.

### Added

- Email headers on `stonework:EmailMessage`: `hasFromAddress`, `hasSenderAddress` and `hasReturnPathAddress` (functional); `hasReplyToAddress`, `hasToAddress`, `hasCcAddress`, `hasBccAddress` (→ `EmailAddress`); `fromDisplayName`, `emailSubject`, `sentAtTime` and `messageId` (functional); `emailBody`; `inReplyTo` and `referencesMessage` (→ `EmailMessage`, the thread); `hasAttachment` (→ `File`). STIX has no Reply-To; it is a common step in business email compromise.
- `stonework:EmailAuthenticationResult` (⊑ `Assessment`), linked by `hasAuthenticationResult`: one SPF, DKIM, DMARC or ARC check, with `authenticatedDomain` and `authenticatedBy` (both functional). Its method and verdict are categories: `hasAuthenticationMethod` and `hasAuthenticationVerdict` (functional, in `categories.ttl`), with the `AuthenticationMethod` scheme (SPF, DKIM, DMARC, ARC) and the `AuthenticationVerdict` scheme (the RFC 8601 verdicts: pass, fail, soft fail, neutral, none, temporary error, permanent error, policy).
- `stonework:MailboxRule` (⊑ `DigitalArtifact`): a rule a mailbox applies to the email it receives, as used for T1114.003 (Email Forwarding Rule) and T1564.008 (Email Hiding Rules). `ruleOfMailbox` (→ `UserAccount`, functional); conditions `matchesKeyword` and `matchesSender`; actions `forwardsTo` and `redirectsTo` (→ `EmailAddress`), `movesToFolder`, `deletesMessage` and `marksAsRead`; state `ruleEnabled` and `hiddenFromUser` (all functional). Its creation is an activity that `produces` it; later changes act on it.
- STIX framework: `stones:fromRef`, `senderRef`, `toRefs`, `ccRefs`, `bccRefs`, `date` and `messageId` are subproperties of the STONEWORK header properties.
- SHACL: `EmailMessageShape`, `EmailAuthenticationResultShape`, `GeneratedFromShape` and `MailboxRuleShape`; fixtures for each.

### Changed

- `stonework:generatedFrom` takes any `DigitalArtifact`, not only a `Log` or `NetworkTraffic`: a Received hop is generated from its EmailMessage. Scope note: the link stays when the Event is assigned to a Step, and `externalId` on the Event names the record within the artifact.
- `stonework:hasSourceAddress` and `stonework:hasDestinationAddress` take an `Event` as well as `NetworkTraffic`: the client of a sign-in, the sending server of a hop.
- `stonework:ruleName` and `stonework:ruleContent` apply to a `MailboxRule` as well as a `DetectionRule`.
- Scope note on `stonework:EmailMessage` lists its header properties and how a Received hop is recorded.
- Examples: the BEC example's bank-change email has its headers, the genuine invoice it replies to, SPF, DKIM and DMARC passes for the lookalike domain, and its Received hop; its forwarding rule is a `MailboxRule` with its keywords, forwarding address and folder. The worked example's queries find replies from a different domain than the message they answer, and rules that forward outside the mailbox's domain while hiding the original.

## 0.12.0 (core), categories 0.3.0: plans and runs; exploit evidence

Two strands of work. **Plans and runs:** a common parent for plans, and per-run Variable values, so a plan can be executed any number of times; the Roles that perform Steps; deviations from a plan as findings with evidence; parallel branches; messages between plans; default branches, step outcomes and targets; playbook types; what a hypothesis is about, with compound hypotheses made of parts; who controlled an identity, and when; and ATT&CK mitigations as Behaviors that plans implement. See [docs/plan-execution-model.md](docs/plan-execution-model.md) and the revised [BEC worked example](docs/bec-worked-example.md) (proposals 1, 2, 4 to 10, 12 and 13 to 16).

**Exploit evidence:** vocabulary for vulnerability exploit evidence that does not fit the EPSS probability alone, without naming a catalog vendor in the identifier.

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
- `stonework:IdentityControl` (⊑ `QualifiedAssertion`), with `stonework:controllingAgent` and `stonework:controlledIdentity` (both functional): that an Agent controlled a DigitalIdentity from `validFrom` to `validUntil`, with evidence. Not exclusive of the identity's holder, so the unattributed executions through it in the interval are the ones to review.
- `stonework:defaultTransition` (functional, Step → Transition): the Transition taken when no other outgoing guard holds (CACAO's switch default, BPMN's default flow).
- `stonework:guardValue` (functional, Transition → any individual): a guard that tests identity with an individual; mirrors `predictedValue`.
- `stonework:outcomeVariable` (functional, ⊑ `hasOutputVariable`): the output Variable recording whether an execution succeeded, failed or timed out (CACAO's on_success / on_failure).
- `stonework:stepTarget` (Step → CyberEntity): what a Step is meant to act on, an entity or a Variable bound in the run; the plan-level counterpart of `actsOn`.
- `stonework:hasPlaybookType` (Plan → PlaybookType; in `categories.ttl`): CACAO 2.0's playbook types, several allowed.
- Categories: `stonework:DeviationKind` scheme (Skipped, Wrong role, Same agent, Out of order, Misused identity, Wrong target); `stonework:ExecutionOutcome` scheme (Succeeded, Failed, Timed out); `stonework:PlaybookType` scheme (Attack, Detection, Engagement, Investigation, Mitigation, Notification, Prevention, Remediation); `stonework:FlowKind` scheme (Exclusive, Parallel).
- SHACL: `VariableBindingShape` (exactly one Variable and execution, exactly one value), `PartOfExecutionShape`, `UsedBindingShape`, `DeviationShape` (exactly one run and kind, at least one Step), `PerformerRoleShape`, `SeparatedFromShape`, `SplitKindShape`, `JoinKindShape`, `SuppliedByShape`, `DefaultTransitionShape`, `OutcomeVariableShape`, `StepTargetShape`, `HasPlaybookTypeShape`, `HypothesisPartShape`, `IdentityControlShape`, and `guardValue` at most once on `TransitionShape`; fixtures for each.
- `stonework:epssPercentile` and `stonework:metricEpssPercentile`. The percentile is the rank of an EPSS probability, not a second probability.
- `stonework:metricReportedExploited`. A source report that a vulnerability was exploited, including reports that name a threat actor, ransomware, or a botnet. Catalog membership stays `stonework:metricKevMembership`.
- `stonework:ExploitationReportKind` (`exploited`, `threat-actor`, `ransomware`, `botnet`) and `stonework:hasExploitationReportKind` on the observation. A named actor, malware, or botnet is the observation's `stonework:assertionObject`. That property is single-valued, so each named actor or malware is its own observation, even when the kind is the same.
- `stonework:ExploitMaturity` (`poc`, `weaponized`, in that order) and `stonework:hasExploitMaturity`. One maturity per subject: the vulnerability's highest known maturity (a convenience projection), or one exploit reference's own maturity. Dated history is not recorded yet.
- `stonework:AffectedStatus` (`affected`, `unaffected`, `unknown`, `fixed`, `under-investigation`) and functional `stonework:hasAffectedStatus` on `stonework:VulnerabilityAssessment`.
- SHACL: `EpssPercentileShape`, the same 0.0–1.0 bound as `epssScore`; `ExploitMaturityShape` and `ExploitationReportKindShape`, at most one value per subject. These are SHACL limits rather than `owl:FunctionalProperty`, so two sources that disagree are reported, not merged by a reasoner.

### Changed

- **Breaking:** `stonework:boundTo` and `stonework:boundToLiteral` take a `VariableBinding`, not a `Variable`. `VariableShape` now rejects either on a Variable.
- `Playbook`, `ControlPlan`, `InvestigationPlan`, `Procedure` and `ThreatScenario` are subclasses of `Plan` rather than directly of `Behavior` (still Behaviors).
- `stonework:performedBy`, `stonework:triggeredBy` and `stonework:triggersPlaybook` take any `Plan`, not only a `Playbook`.
- `stonework:evidencedBy` takes a `Deviation` or an `IdentityControl` as well as a `Sighting`.
- `stonework:Mitigation` (and so `CourseOfAction` and `attack:Mitigation`) is a subclass of `Behavior` as well as `Countermeasure`, as `Control` is, so a ControlPlan or Step can `implements` an ATT&CK mitigation without a reasoner reclassifying it. `ControlPlan` implements a Control or a Mitigation.
- Scope notes on `stonework:Variable` and `stonework:Transition`: data flow between Steps of different Plans is a message between participants; control flow never crosses Plans.
- Scope note on `stonework:precededByStep`: a Step with several values follows all of them, and Steps with no path between them may be performed in parallel.
- Scope notes on `performedBy` and `attributedToAgent`: an execution names its performer as observed, often an identity; an identity used by someone other than its holder stays the performer, and the Agent responsible is `attributedTo`.
- Scope notes on `Behavior`, `Step`, `Process`, `Variable`, `Transition`, `Hypothesis` and `executionOf` describe runs and bindings. A Hypothesis is judged by its Variable's binding in the Investigation that tests it.
- Examples: the T1003.001 trace has a run, nested step executions and bindings; the BEC example runs its business process three times and its search Step once per mailbox, gives each business Step its Role, records the wire's release by the controller's bank-portal login, records the skipped callback as a Deviation, and runs its containment plan's credential reset and transport block as parallel branches joined before the review, and adds the actor's `OperationPlan`, whose sending Step outputs the payment request the business process takes as input. Its detection search has an outcome Variable, a failure branch and a default branch; its containment Steps name their targets; its plans carry playbook types. Its hypotheses say what they're about, and a compound hypothesis splits the activity (confirmed) from the attribution (pending). The actor's control of the controller's mailbox account is an `IdentityControl` from 2 to 30 September, and two sign-ins in that interval await review. Its transport block implements ATT&CK M1042 and its callback Step M1060.
- `stonework:VersionedProduct` is a `stonework:CyberEntity`, the same root as `stonework:Product`. A release stays disjoint from its product line.
- `stonework:metricKevMembership` and `stonework:isKnownExploited` are no longer defined as CISA-only. The catalog is the observation's `stonework:hasProvenance`.
- `stonework:url` has no domain, so a framework entity's page (an ATT&CK technique's, for one) doesn't make the entity a `stonework:OnlineReference`.
- `stonework:controlFamily` allows a family code ("AC") as well as a name.

### Deprecated

- `stonework:playbookVersion` and `stonework:playbookFormat`: now sub-properties of `planVersion` and `planFormat`.

### Framework alignment

Framework properties that already had a STONEWORK term are now tied to it (from the framework-vs-STONEWORK gap audit):

- `nist:family` ⊑ `stonework:controlFamily`
- `attack:alias` ⊑ `stones:aliases` ⊑ `skos:altLabel`
- `attack:url` ⊑ `stonework:url`
- `cpe:lastModified` ⊑ `stonework:modified`
- `cve:references` ⊑ `stonework:references`


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
