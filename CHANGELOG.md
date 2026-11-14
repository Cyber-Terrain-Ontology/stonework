# Changelog

## 0.20.0 (core): competing hypotheses

Alternatives are separate hypotheses. `competesWith` links two that answer the same question when the analyst does not accept both. Confirming one does not refute the other.

### Added

- `stonework:competesWith` (Hypothesis ↔ Hypothesis, symmetric, not transitive): stated, not inferred. With three alternatives, each pair is asserted. Not lineage (`splitFrom`, `absorbedInto`, `obsoletes`) and not a conjunction (`hypothesisPart`). `CompetesWithShape`: the object is a Hypothesis other than the subject. `CompetingConfirmedShape` warns when both rivals are confirmed.

### Changed

- Docs: [plan-execution-model.md](docs/plan-execution-model.md), [bec-worked-example.md](docs/bec-worked-example.md).

## 0.19.0 (core), categories 0.7.0: hypothesis lineage

A hypothesis that is split, merged, or replaced is kept. The new one points at the earlier one, and the earlier one is superseded unless it already reached a verdict.

### Added

- `stonework:splitFrom` (Hypothesis → Hypothesis, functional): this hypothesis is one of those produced by splitting that one. Several may name the same parent. `HypothesisShape`.
- `stonework:absorbedInto` (Hypothesis → Hypothesis, functional): this hypothesis was merged into that one. The absorbed record is kept. An Investigation still uses `mergedInto`, and `MergedIntoShape` rejects a subject of `mergedInto` that is not an Investigation.
- `stonework:obsoletes` (Hypothesis → Hypothesis, not transitive): the later hypothesis replaces the earlier one, including a refuted hypothesis a new one is formed from. After Dublin Core `replaces`. One hypothesis may obsolete more than one earlier hypothesis.
- `stonework:hypothesisStatusSuperseded` (in `categories.ttl`): set aside before a verdict, by a split, a merge, or a replacement. A hypothesis already confirmed or refuted keeps that status. Warnings when a hypothesis set aside by its lineage is still pending: `AbsorbedHypothesisStatusShape`, `SplitParentStatusShape`, `ObsoletedHypothesisStatusShape`.

### Changed

- Docs: [plan-execution-model.md](docs/plan-execution-model.md). The design log's deferred genealogy item is this.
- BEC worked example: the identity-control finding, the skipped-callback deviation, and the two role assignments cite the case file as `hasProvenance`, so the example passes the strict profile. The checker runs it against `financial-strict`.
- Credential-dump trace: the five leaf executions cite the endpoint log that shows them (`evidencedBy`). The checker fails if that file raises a warning.

## 0.18.0 (core): assessing whether a vulnerability was exploited

### Added

- `stonework:assessesExploitationOf` (CourseOfAction → Vulnerability): a course of action that determines whether the vulnerability was exploited, such as forensic triage or a compromise assessment, as distinct from `mitigatesVulnerability`, which addresses the vulnerability itself. For CISA's known-exploited catalog, whose entries can require forensic triage as well as a fix, and for advisories that say what to look for after patching. `AssessesExploitationOfShape`: the object is a Vulnerability. Fixtures for each.

### Changed

- `stonework:mitigatesVulnerability`: a scope note pointing to `assessesExploitationOf`.
- `stonework:OperationPlan`: `skos:altLabel "Attack plan"@en`, and a scope note sentence saying user interfaces may show it by that name, the phrase practitioners use for an adversary's procedures in order. The class keeps its name and IRI.

## 0.17.0 (core): calling a plan, and revising one

### Added

- `stonework:invokesPlan` (Step → Plan, functional): a Step whose performance is a run of another Plan, BPMN's call activity and CACAO's `playbook-action`. The execution of the Step is also `executionOf` the invoked Plan. `InvokesPlanShape`: at most one, a Plan, and not the Step's own Plan.
- `stonework:revisionOf` (Plan → Plan, not transitive): a new version of a Plan, after PROV-O's `wasRevisionOf`. A Plan with runs is revised rather than edited, and runs stay on the version they followed. `RevisionOfShape`, and a warning when a revision has no `planVersion` (`RevisionVersionShape`). Fixtures for each.

### Changed

- `stonework:implements` scope note: a Step that runs another Plan `invokesPlan` it; a Plan adapted from a template implements the template.
- BEC worked example: the detection plan's "Contain the mailbox" `invokesPlan` the containment plan, in place of `implements`.
- Docs: [plan-execution-model.md](docs/plan-execution-model.md) section 2e; proposal 23 in [bec-worked-example.md](docs/bec-worked-example.md).

## 0.16.0 (core): what the evidence reports, and personas

### Added

- `stonework:startedNotBefore` and `stonework:startedNotAfter` (CyberActivity → `xsd:dateTime`, functional): a window for a start the evidence bounds but doesn't give, such as a call a statement places between two logged events, in place of an estimated `startedAtTime`. After CIDOC CRM's begin of the begin and end of the begin (P82a, P82b).
- SHACL: the bounds in order, and containing `startedAtTime` if both are given (`ActivityWindowShape`); a warning for an execution placed in a run that rests on neither a record (`generatedFrom`) nor evidence (`evidencedBy`) (`ExecutionSupportShape`). Fixtures for each.

### Changed

- `stonework:evidencedBy` applies to any CyberActivity as well: an execution no record shows, established by a statement, a call record or a saved query, is evidencedBy them. Its scope note distinguishes recorded (`generatedFrom`) from reported (`evidencedBy` alone).
- BEC worked example: the 30 September callback rests on the clerk's statement and has a window, not a time.
- `stonework:attributedTo` scope note: a run's attribution covers its executions unless one is attributed otherwise, queried through the run rather than copied; while who is behind an activity is open, attribute it to a persona (a `DigitalIdentity` that isn't an Account), joined to an Agent with `attributedToAgent` once established.
- `ExecutionSupportShape`: an execution with executions of its own (a sub-run) rests on them, and doesn't warn.
- BEC worked example: every execution cites what it rests on. New artifacts the investigation would have: the bank portal's payment activity (`ex:log-bank-portal`), the containment's audit-log records (`ex:log-audit-containment`), and the review's notice to suppliers and customers (`ex:file-review-notice`). The example now validates without warnings.
- BEC worked example: the rule's creation, the mailbox control and the mail reads are attributed to one persona, the email and the incident to another; the attribution hypothesis is about the two. `ex:actor` has nothing attributed to it while the hypothesis is pending, and the actor's run is attributed to no one.

- `stonework:refersTo` covers evidence as well as intelligence: what a log or message names (a tenant, an account, a host) refers to the organization's own entity for it, such as a Plan Step's target. Definition and scope note only; the scope note now says why it isn't `owl:sameAs` for revision (nothing follows from it unless followed, so retracting it retracts nothing else). Docs: [investigation-management.md](docs/investigation-management.md).

## 0.15.0 (core), categories 0.6.0: reviews of records

An analyst working through an investigation's records can record that they looked at some and found them relevant, or not relevant, so the next analyst doesn't look through them again.

### Added

- `stonework:Review` (⊑ `Process`): an analyst's examination of records or artifacts, as part of an investigation. The records are `hasInput`, the investigation is the execution it is `partOfExecution`, the analyst is `performedBy`, and a Review can be the execution of an InvestigationPlan's triage Step (`correspondsToStep`). Follows the CASE investigative action.
- `stonework:ReviewFinding` scheme (relevant, not relevant) and `stonework:hasReviewFinding` (Review → `ReviewFinding`, functional; in `categories.ttl`). The finding applies to every input, so a mixed batch is two Reviews; a later Review of the same record supersedes an earlier one. "Not relevant" says nothing about whether a record is true or benign.
- SHACL: `ReviewShape` (exactly one finding, at least one input, part of an execution; warnings for no analyst or end time); fixtures for each.

### Changed

- Scope note on `stonework:Investigation`: its reviews of records are Reviews that are `partOfExecution` it.
- Docs: [record-review.md](docs/record-review.md), the design and the alternatives it rejected; proposal 20 in the BEC worked example.

## 0.14.0 (core), categories 0.5.0: outcomes and sign-in authentication

How an activity ended, and how a sign-in was authenticated.

### Added

- `stonework:hasOutcome` (CyberActivity → `ExecutionOutcome`, functional; in `categories.ttl`) and `stonework:outcomeDetail` (string): how any activity ended, as observed, and why, as the source reports it. A Step's `outcomeVariable` binds the same value in a run.
- `executionOutcomeInterrupted`: an activity that paused for something more, such as a further authentication step, and continues in another record (not in CACAO).
- `stonework:AuthenticatorType` scheme, after NIST SP 800-63B: password, PIN, recovery code, SMS code, voice call, email code, push approval, authenticator-app code, hardware OTP token, FIDO2 security key, platform passkey, smart card, client certificate, SSH key, API key or client secret, session token, federated assertion. `stonework:phishingResistant` marks the four bound to the site's origin.
- `stonework:AuthenticationFactor` scheme: knowledge, possession, inherence.
- `stonework:authenticatedWith` (CyberActivity → `AuthenticatorType`) and `stonework:authenticationFactor` (CyberActivity → `AuthenticationFactor`): what a sign-in presented, and the distinct factors checked, per activity. A replayed session token presents no factor.
- SHACL: `HasOutcomeShape`, `AuthenticatedWithShape`, `AuthenticationFactorShape`, `AuthenticatorTypeShape`; fixtures for each.

### Changed

- `stonework:performedBy` takes any `CyberActivity` (or a `Plan`), not only a `Process`: an `Event` parsed from a log record names the account that performed it without also being typed a `Process`.
- `stonework:hasInput` and `stonework:hasOutput` take any `CyberActivity`, for the same reason: a bank portal's release record has the wire as its output.
- Scope note on `stonework:Event`: an Event parsed from a record keeps `generatedFrom` and names its performer; placed in a run (`correspondsToStep`, `partOfExecution`), it stays an Event and is the Step's execution without changing type.
- **Breaking (released in 0.13.0 only):** the email sender-authentication categories are renamed so they can't be mistaken for sign-in authentication: `AuthenticationMethod` → `EmailAuthenticationMethod`, `hasAuthenticationMethod` → `hasEmailAuthenticationMethod`, `authenticationMethodScheme` and its individuals (`authenticationMethodSPF`, …) → `emailAuthenticationMethod…`.
- `ExecutionOutcome` covers any observed activity, not only executions of a Step.
- Examples: the BEC example's two sign-ins are authenticated with a session token and succeeded.

## 0.13.0 (core), categories 0.4.0, STIX framework 0.4.0: email evidence

An `EmailMessage` carries its headers as data, so a message taken from a mailbox is evidence that can be queried: who it claimed to be from, where replies went, which thread it joined, and what the receiving server's authentication checks found. Received headers are Events derived from the message, which is also how a parsed log record points back to its log. A mailbox rule, the artifact at the centre of T1114.003, has its own class.

### Added

- Email headers on `stonework:EmailMessage`: `hasFromAddress`, `hasSenderAddress` and `hasReturnPathAddress` (functional); `hasReplyToAddress`, `hasToAddress`, `hasCcAddress`, `hasBccAddress` (→ `EmailAddress`); `fromDisplayName`, `emailSubject`, `sentAtTime` and `messageId` (functional); `emailBody`; `inReplyTo` and `referencesMessage` (→ `EmailMessage`, the thread); `hasAttachment` (→ `File`). STIX has no Reply-To; it is a common step in business email compromise.
- `stonework:EmailAuthenticationResult` (⊑ `Assessment`), linked by `hasAuthenticationResult`: one SPF, DKIM, DMARC or ARC check, with `authenticatedDomain` and `authenticatedBy` (both functional). Its method and verdict are categories: `hasAuthenticationMethod` and `hasAuthenticationVerdict` (functional, in `categories.ttl`), with the `AuthenticationMethod` scheme (SPF, DKIM, DMARC, ARC) and the `AuthenticationVerdict` scheme (the RFC 8601 verdicts: pass, fail, soft fail, neutral, none, temporary error, permanent error, policy).
- `stonework:MailboxRule` (⊑ `DigitalArtifact`): a rule a mailbox applies to the email it receives, as used for T1114.003 (Email Forwarding Rule) and T1564.008 (Email Hiding Rules). `ruleOfMailbox` (→ `UserAccount`, functional); conditions `matchesKeyword` and `matchesSender`; actions `forwardsTo` and `redirectsTo` (→ `EmailAddress`), `movesToFolder`, `deletesMessage` and `marksAsRead`; state `ruleEnabled` and `hiddenFromUser` (all functional). Its creation is an activity that `produces` it; later changes act on it.
- `stonework:usedUserAgent` (`CyberActivity` or `NetworkTraffic` → `UserAgent`): the client a sign-in or other activity presented.
- STIX framework: `stones:fromRef`, `senderRef`, `toRefs`, `ccRefs`, `bccRefs`, `date` and `messageId` are subproperties of the STONEWORK header properties.
- SHACL: `EmailMessageShape`, `EmailAuthenticationResultShape`, `GeneratedFromShape`, `MailboxRuleShape` and `UsedUserAgentShape`; fixtures for each.

### Changed

- `stonework:generatedFrom` takes any `DigitalArtifact`, not only a `Log` or `NetworkTraffic`: a Received hop is generated from its EmailMessage. Scope note: the link stays when the Event is assigned to a Step, and `externalId` on the Event names the record within the artifact.
- `stonework:hasSourceAddress` and `stonework:hasDestinationAddress` take any `CyberActivity` as well as `NetworkTraffic`: the client of a sign-in, the sending server of a hop. Scope note: an address's location is said with `locatedAt` on the `IPAddress`.
- `stonework:ruleName` and `stonework:ruleContent` apply to a `MailboxRule` as well as a `DetectionRule`.
- Scope note on `stonework:EmailMessage` lists its header properties and how a Received hop is recorded.
- Examples: the BEC example's bank-change email has its headers, the genuine invoice it replies to, SPF, DKIM and DMARC passes for the lookalike domain, and its Received hop; its forwarding rule is a `MailboxRule` with its keywords, forwarding address and folder; the rule's creation and the two sign-ins record their client address, its country, and their user agent. The worked example's queries find replies from a different domain than the message they answer, rules that forward outside the mailbox's domain while hiding the original, and unattributed activity from an address attributed activity came from.

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
