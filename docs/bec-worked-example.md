# Worked Example: a Business Email Compromise, as Plans

*First cut 2026-10-22, from a conversation between Ryan Hohimer and Claude; revised
2026-10-30 for STONEWORK 0.12.0, which adds `stonework:Plan`, `BusinessProcess` and
per-run Variable bindings (proposals 4, 5 and 7 below). The gaps it still runs into are
listed at the end as proposals, not changes.*

The Turtle is [`examples/bec-t1114-003.ttl`](../examples/bec-t1114-003.ttl). It passes the
`financial` SHACL profile, and every triple satisfies its property's declared domain
and range, so a reasoner would add no unexpected types.

## Why this example

Two ideas from the conversation:

- **Much of STONEWORK is plans.** Attacks, detections and mitigations all have planned forms.
  A Hypothesis is confirmed or refuted by whether the Steps of a plan, once executed, give the
  values it predicted.
- **"We have a plan to mitigate the problem if we are attacked with T1114.003"** is a
  legitimate statement, one an assessor, an insurer or a board asks about. It's different
  from "we executed the plan" and from "the plan worked".

And a third that came out of them: Steps are executed by systems, but also by people, and an
organization's business processes are plans too. In a business email compromise (BEC) the
attacker's technique is a system action, but the fraud succeeds or fails in a business
process: whether someone carried out the step that should have stopped it.

## The story

A small manufacturer pays its suppliers by wire. All names are illustrative.

| When | What happened | Modelled as |
|---|---|---|
| 2 Sep, 03:14 | With the controller's stolen credentials, the actor creates a hidden inbox rule: mail mentioning an invoice, a payment or a wire is forwarded to an outside address and moved to RSS Feeds. | `Process` `executionOf` T1114.003, `produces` the rule |
| 9 Sep | An ordinary payment: the supplier's August invoice, to the account on file. | A run of the business process |
| 15 Sep | From a lookalike of the supplier's address, the actor replies to a real invoice thread: "we've changed banks". | `EmailMessage`, `EmailAddress` |
| 16 Sep | The AP clerk enters the September payment with the new bank details. The callback the process requires is never made. The controller approves, and releases a $186,400 wire to a mule account. | A second run, with no execution of the callback Step |
| 30 Sep, morning | The actor asks for another invoice to be paid to the same account. This time the clerk calls the supplier at the number on file: it hasn't changed banks, and hasn't been paid for September. | A third run, stopped at the callback |
| 30 Sep | An incident is declared and an analyst opens an investigation. | `Incident`, `Investigation` |
| 30 Sep | Two hypotheses: a forwarding rule on the controller's mailbox, and one on the clerk's. The analyst runs a detection plan built from ATT&CK's DET0576, whose search Step runs once for each mailbox. The first is confirmed, the second refuted. | `Hypothesis` ×2, `DetectionPlan`, `Sighting` |
| 30 Sep – 1 Oct | The containment plan runs: the rule is removed, sessions revoked, external auto-forwarding blocked (by automation), and the exposed mail reviewed. | `ControlPlan` and its execution |

## The four pieces

### 1. The business process: paying a supplier by wire

`ex:bp-supplier-wire` is a `stonework:BusinessProcess`, `performedBy` the organization (the
Agent responsible for it), `planVersion` 3.2. Four Steps:

1. **Enter the invoice and payment request** (AP clerk). Output Variables `bankDetailsChanged`
   and `payeeBankDetails` (the account the request names).
2. **Verify changed bank details by callback** (AP clerk). Input `payeeBankDetails`: the
   account Step 1 recorded is what the callback checks. Output `callbackVerified`. The Step
   `implements` the organization's own control `ex:control-callback`, a `stonework:Control`
   ("FIN-07: a change to a payee's bank details is verified by phone, at a number already on
   file").
3. **Approve the payment** (controller).
4. **Release the wire** (controller).

Transitions: from Step 1 to Step 2 when `bankDetailsChanged` is true, straight to Step 3 when
it's false, and from Step 2 to Step 3 when `callbackVerified` is true.

**Three runs.** Each run is a `Process` that is `executionOf` the plan; each Step's execution
is `partOfExecution` its run; and each value a Step's execution bound is a
`VariableBinding` (`bindingOf` the Variable, `boundIn` that execution):

| Run | `bankDetailsChanged` | Callback | Result |
|---|---|---|---|
| `ex:run-wire-0909` | false | not required | paid to the account on file |
| `ex:run-wire-0916` | true | **no execution** | $186,400 wired to the mule account |
| `ex:run-wire-0930` | true | executed; `callbackVerified` false | stopped; the fraud is discovered |

**Data flow.** In the 30 September run, the callback's execution records
`usedBinding ex:b0930-details`: the account Step 1 bound in that run, which it went on to
check. In the 16 September run, Step 1 bound the mule account (`ex:b0916-details`) and no
execution in that run used it. The value the control existed to check was never checked.

**The skipped step is a finding the graph can find, one run at a time:**

```sparql
# Steps that a plan's own guards required, but that a run went on without.
SELECT ?run ?required ?after WHERE {
  ?run stonework:executionOf ?plan .
  ?plan stonework:hasStep ?from , ?required .
  ?tr stonework:fromStep ?from ; stonework:toStep ?required ;
      stonework:guardVariable ?v ; stonework:guardLiteralValue ?g .
  ?doneFrom stonework:correspondsToStep ?from ; stonework:partOfExecution ?run .
  ?b stonework:bindingOf ?v ; stonework:boundIn ?doneFrom ;
     stonework:boundToLiteral ?g .                       # the guard held in this run
  FILTER NOT EXISTS { ?x stonework:correspondsToStep ?required ;
                         stonework:partOfExecution ?run }
  ?required stonework:stepOrder ?ro .                    # and the run went on anyway
  ?later stonework:correspondsToStep ?ls ; stonework:partOfExecution ?run .
  ?ls stonework:stepOrder ?lo ; skos:prefLabel ?after .
  FILTER(?lo > ?ro)
}
```

→ `ex:run-wire-0916`, `ex:wstep-verify`, then "Approve the payment" and "Release the
wire". The 9 September run isn't reported, because its guard sent it straight to approval;
nor is the 30 September run, because its callback was made. Before 0.12.0 the plan could
hold only one run's values, so the query couldn't tell the runs apart.

**Who.** `Role`s for the controller and the AP clerk, with `RoleAssignment`s in the context of
the organization. Executions name their performers with `performedBy`. What the plan can't
say yet is which role each Step belongs to (proposal 2).

### 2. The hypotheses

Both predict the output Variable of the detection plan's search Step, `forwardingRuleFound`,
with `predictedType stonework:Sighting`, meaning "this search will produce a sighting of the
technique". The search runs twice in one Investigation, once per mailbox, so the Variable has
two bindings in that run. Each hypothesis is therefore tested (`testsHypothesis`) by the
search execution for its mailbox, as well as listed on the Investigation, and judged by the
binding that execution produced:

| Hypothesis | Confidence | Binding | Status |
|---|---|---|---|
| A forwarding rule on the controller's mailbox | 70 | `ex:sighting-controller-rule` | Confirmed |
| A forwarding rule on the clerk's mailbox | 30 | `false` | Refuted |

**Negative evidence is first-class.** The search of the clerk's mailbox is an execution like
any other, with its times, its performer and its output: `ex:log-clerk-search`, the saved
query and its empty result for 90 days. The refuted hypothesis points to it the same way the
confirmed one points to its evidence:

```sparql
SELECT ?hypothesis ?status ?result ?evidence WHERE {
  ?search stonework:testsHypothesis ?h ; stonework:hasOutput ?log .
  ?h skos:prefLabel ?hypothesis ; stonework:hasHypothesisStatus ?status ;
     stonework:predictsVariable ?v .
  ?b stonework:bindingOf ?v ; stonework:boundIn ?search .
  ?log skos:prefLabel ?evidence .
  OPTIONAL { ?b stonework:boundTo ?bo } OPTIONAL { ?b stonework:boundToLiteral ?bl }
  BIND(COALESCE(?bo, ?bl) AS ?result)
}
```

This may make the `supportsHypothesis` / `refutesHypothesis` properties discussed earlier
unnecessary: the plan's execution already connects a hypothesis to its evidence.

### 3. The detection plan

`ex:detplan-forwarding` is a `stonework:DetectionPlan` that `implements` ATT&CK's detection
strategy **DET0576** ("Email Forwarding Rule Abuse Detection Across Platforms"), which the
CTI Encyclopedia says `detects` T1114.003. Two Steps:

1. **Search the audit log for forwarding rules on a mailbox:** `New-InboxRule` /
   `Set-InboxRule` setting `ForwardTo`, `ForwardAsAttachmentTo` or `RedirectTo`, 90 days.
   Input `mailbox`, output `forwardingRuleFound`. It `implements` ATT&CK's analytic
   **AN1591** (Office Suite: "Creation of email forwarding/redirect rules in Exchange Online
   via New-InboxRule or transport rule cmdlets…").
2. **Contain the mailbox.** It `implements` the control plan below, which is how the
   DetectionPlan's own definition says a confirmed violation is handed on.

The Transition from Step 1 to Step 2 is guarded by `guardType stonework:Sighting`.

The Investigation `ex:inv-bec` is the run: it is `executionOf` the DetectionPlan,
`investigates` the Incident, and is Closed with outcome Confirmed. It binds the `mailbox`
input twice, once for each mailbox in question. Step 1 is executed twice within it, and each
execution is an `Investigation` (the plan-execution recipe's choice for assessment plans)
that `correspondsToStep` the search, is `partOfExecution` the run, records the mailbox
binding it received with `usedBinding`, `actsOn` that mailbox account, and `hasOutput` its
log. The controller search `produces` the `Sighting`: `sightedObject` T1114.003, `sightedBy`
the analyst, `sightedAt` the email tenant, `evidencedBy` the `New-InboxRule` audit record.
Before 0.12.0 the example needed a separate Step per mailbox, because a Variable could hold
only one value.

### 4. The control plan

`ex:ctlplan-forwarding` is a `stonework:ControlPlan`, "Contain a malicious forwarding rule".
It `implements` NIST SP 800-53 **AC-4** (Information Flow Enforcement), which the
Encyclopedia says `mitigatesAttackPattern` T1114.003. Four Steps:

1. Disable and remove the rule, keeping a copy as evidence. *(analyst)*
2. Revoke the account's sessions and reset its credentials. *(analyst)*
3. Block automatic forwarding to external domains at the transport layer. *(automation)*
4. Review what was forwarded, and warn the suppliers and customers it exposed. *(analyst and
   controller)*

Its execution `ex:exe-contain` is three things at once: it `correspondsToStep` the
DetectionPlan's containment Step and is `partOfExecution` the Investigation (the containment
step of the investigation); it is `executionOf` the ControlPlan (a run of our containment
plan); and it records `usedBinding` the controller search's Sighting, the finding it acted
on. The executions of the ControlPlan's own Steps are `partOfExecution` it.

**"We have a plan if we're attacked with T1114.003"** is then a query that joins the
organization's plans to the Encyclopedia's facts:

```sparql
SELECT ?kind ?plan ?via WHERE {
  ?t stonework:attackId "T1114.003" .
  { ?plan a stonework:ControlPlan ; stonework:implements ?c .
    ?c stonework:mitigatesAttackPattern ?t .  BIND("respond" AS ?kind)  ?c skos:prefLabel ?via }
  UNION
  { ?plan a stonework:DetectionPlan ; stonework:implements ?d .
    ?d stonework:detects ?t .                BIND("detect" AS ?kind)   ?d stonework:attackId ?via }
}
```

→ "respond: `ex:ctlplan-forwarding` via AC-4" and "detect: `ex:detplan-forwarding` via DET0576".
Neither plan names the technique; both reach it through what they implement.

## What it shows about plans

Every link from this case to T1114.003 goes through a plan or a plan's execution, and none
needs the technique itself to be a plan:

```
attacker's Process ──executionOf──────────────────────────────────▶ T1114.003
DetectionPlan ──implements──▶ DET0576 ──detects───────────────────▶ T1114.003
  Step ──implements──▶ AN1591 (an analytic of DET0576)
ControlPlan ──implements──▶ AC-4 ──mitigatesAttackPattern─────────▶ T1114.003
Hypothesis ──predictsVariable──▶ Variable ◀──bindingOf── VariableBinding
                                   ──boundTo──▶ Sighting ──sightedObject──▶ T1114.003
```

That matches the gradient in [technique-modeling.md](technique-modeling.md): the technique is
the method, and plans are its realizations, offensive, detective or defensive. Since 0.12.0
they share one parent, `stonework:Plan`, and the business process is one of them: the attack
and the business process meet at one Step that a run went on without.

Three kinds of performer appear: people (the clerk, the controller, the analyst), the
organization (responsible for the business process), and software (the automation that
applied the transport rule).

The plan model covers much of the ground of BPMN (processes, tasks, sequence flows with
conditions, data objects), and the skipped-step query is what process mining calls
conformance checking: comparing a run's event trace against the process model. What BPMN
lacks, and STONEWORK adds, is the adversary's plan beside the organization's, and the
hypothesis-and-evidence layer.

## Gaps, as proposals

Numbered for discussion. Proposals 4, 5 and 7 are done in 0.12.0; the rest are not in the
ontology yet.

1. **A Hypothesis has no direct link to what it's about.** Here it reaches T1114.003 only
   after the fact, through its Variable's binding, or through the plan's Step and DET0576. An
   untested hypothesis, or one tested without a plan (allowed since 0.11.0), has no link at
   all. The 0.12.0 revision adds a second reason: when one search Step runs for several
   mailboxes, the hypothesis about the controller's mailbox is told apart from the one about
   the clerk's only by which execution tests it. Proposal: a property from Hypothesis to its
   subject (the technique, actor, vulnerability or asset it's about).

2. **A Step can't say which Role performs it.** Executions have performers, but the plan can't
   say "Step 2 is the AP clerk's". With it, the graph could answer *whose* step was skipped,
   and check segregation of duties (the person who enters a payment isn't the one who approves
   it). Proposal: Step → Role. BPMN calls this a lane.

3. **No agent for plain software.** `AIAgent` is for systems with autonomous decision-making;
   the automation that applies a transport rule isn't one. The example uses a
   `DigitalIdentity` (its service account), which is a persona rather than the actor.
   Proposal: a software-agent class beside `AIAgent`, or a scope note saying which to use.

4. **Done in 0.12.0: a common parent for plans.** `stonework:Plan`, under `Behavior` and
   aligned with `prov:Plan` and `p-plan:Plan`, is now the parent of `Playbook` (and
   `OperationPlan`), `ControlPlan`, `InvestigationPlan` (and `DetectionPlan`),
   `BusinessProcess`, `Procedure` and `ThreatScenario`. `performedBy`, `triggeredBy` and
   `triggersPlaybook` take any Plan, and `planVersion` and `planFormat` replace the
   deprecated `playbookVersion` and `playbookFormat`. Techniques, tactics and controls stay
   Behaviors that plans implement.

5. **Done in 0.12.0: a business process is a `stonework:BusinessProcess`,** a sibling of
   `Playbook` under `Plan`. Each run of it is a `stonework:Process`.

6. **A skipped step is only an absence.** Today "the callback wasn't done" is the lack of an
   execution, which can't be told apart from "it was done but not recorded". Investigators,
   insurers and prosecutors need the deviation as a finding with its own evidence (the
   clerk's statement, the phone records). Options: an execution record with a status
   (performed, skipped, failed), or an analyst's finding (a `QualifiedAssertion`) that the step
   was not performed. Process mining reports such a deviation as a finding about one trace,
   which supports the second option.

7. **Done in 0.12.0: a plan can be run any number of times.** Each run is the execution that
   is `executionOf` the plan; its Steps' executions are `partOfExecution` it; and each value
   is a `VariableBinding` (`bindingOf` the Variable, `boundIn` the execution that bound it,
   `boundTo` or `boundToLiteral` the value). A later Step's execution records the binding it
   received with `usedBinding`. This follows P-Plan's pattern, with a binding node so that
   literal values are handled the same way as individuals. `boundTo` and `boundToLiteral` no
   longer go on the Variable itself.

8. **ATT&CK mitigations aren't Behaviors.** M1042, M1047 and M1060 are `Countermeasure` /
   `CourseOfAction` / `Mitigation`, so a ControlPlan that `implements` one would make a
   reasoner classify the mitigation as a `Behavior`. That's not an inconsistency (STONEWORK
   declares almost no disjoint classes) but it's a silent reclassification. NIST controls are
   already Behaviors, which is why this example's ControlPlan implements AC-4. Options: make
   `Mitigation` a `Behavior`, as `Control` is; or link a ControlPlan to a mitigation with a
   different property.

9. **No parallel branches.** A Transition is a guarded sequence flow, so a plan can't say that
   Steps run side by side and join afterwards (BPMN's parallel gateway). The containment
   plan's Steps 1 to 3 could run in parallel. Proposal: discuss a split/join construct.

10. **No messages between participants.** The actor's email enters the business process as a
    Step's input, but nothing says it was sent from the actor's plan to the organization's
    (BPMN's message flow between pools). Proposal: discuss whether it's needed, or whether
    `hasInput` on the receiving execution is enough.

11. **A ThreatScenario and an OperationPlan are close.** Both are adversary plans: one held as
    a hypothesis, the other believed to exist. A link between them ("this operation matches
    that scenario") may be wanted later. Parked.

Smaller things:

- No class for an inbox or mailbox rule (STIX has none either); the example uses
  `DigitalArtifact`.
- The email's sender and recipients are in prose; `stones:fromRef` and `stones:toRefs` could
  carry them, once their alignment with `stonework:EmailMessage` is checked.
- `ex:control-callback` is an organization-defined control. If financial controls (callback
  verification, dual approval, payee-change holds) recur across cases, they may deserve their
  own catalogue, perhaps in the financial module.
- The release Step's execution links to the wire with `hasOutput`, not `produces`:
  `produces` takes a `CyberEntity`, and a `FinancialTransaction` is an activity.
