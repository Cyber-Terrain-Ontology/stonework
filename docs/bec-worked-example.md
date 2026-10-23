# Worked Example: a Business Email Compromise, as Plans

*First cut, 2026-10-22, from a conversation between Ryan Hohimer and Claude. For
discussion: the example uses only terms STONEWORK has today, and the gaps it runs into
are listed at the end as proposals, not changes.*

The Turtle is [`examples/bec-t1114-003.ttl`](../examples/bec-t1114-003.ttl). It passes the
`financial` SHACL profile, and every triple already satisfies its property's declared domain
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
| 15 Sep | From a lookalike of the supplier's address, the actor replies to a real invoice thread: "we've changed banks". | `EmailMessage`, `EmailAddress` |
| 16 Sep | The AP clerk enters the payment with the new bank details. The callback the process requires is never made. The controller approves, and releases a $186,400 wire to a mule account. | The business process and its execution |
| 30 Sep | The supplier asks why it hasn't been paid. An incident is declared and an analyst opens an investigation. | `Incident`, `Investigation` |
| 30 Sep | Two hypotheses: a forwarding rule on the controller's mailbox, and one on the clerk's. The analyst runs a detection plan built from ATT&CK's DET0576. The first is confirmed, the second refuted. | `Hypothesis` ×2, `DetectionPlan`, `Sighting` |
| 30 Sep – 1 Oct | The containment plan runs: the rule is removed, sessions revoked, external auto-forwarding blocked (by automation), and the exposed mail reviewed. | `ControlPlan` and its execution |

## The four pieces

### 1. The business process: paying a supplier by wire

`ex:bp-supplier-wire` is a `stonework:Playbook`, `performedBy` the organization (the Agent
responsible for it), version 3.2. Four Steps:

1. **Enter the invoice and payment request** (AP clerk). Output Variable `bankDetailsChanged`.
2. **Verify changed bank details by callback** (AP clerk). It `implements` the organization's
   own control `ex:control-callback`, a `stonework:Control` ("FIN-07: a change to a payee's bank
   details is verified by phone, at a number already on file"). Output `callbackVerified`.
3. **Approve the payment** (controller).
4. **Release the wire** (controller).

Transitions: from Step 1 to Step 2 when `bankDetailsChanged` is true, straight to Step 3 when
it's false, and from Step 2 to Step 3 when `callbackVerified` is true.

**The execution.** `bankDetailsChanged` is bound to true, so the plan's own guard required the
callback. There are executions for Steps 1, 3 and 4 (Step 1 has the actor's email as its
input; Step 4 `produces` the `FinancialTransaction`), and **none for Step 2**:
`callbackVerified` stays unbound. That gap is the finding, and the graph can find it:

```sparql
# Steps that a plan's own guards required, but that were never executed.
SELECT ?run ?required ?after WHERE {
  ?run stonework:executionOf ?plan .
  ?plan stonework:hasStep ?from , ?required .
  ?tr stonework:fromStep ?from ; stonework:toStep ?required ;
      stonework:guardVariable ?v ; stonework:guardLiteralValue ?g .
  ?v stonework:boundToLiteral ?g .                       # the guard was satisfied
  ?doneFrom stonework:correspondsToStep ?from .
  FILTER NOT EXISTS { ?x stonework:correspondsToStep ?required }
  ?required stonework:stepOrder ?ro .                    # and the plan went on anyway
  ?later stonework:correspondsToStep ?ls .
  ?ls stonework:isStepOf ?plan ; stonework:stepOrder ?lo ; skos:prefLabel ?after .
  FILTER(?lo > ?ro)
}
```

→ `ex:exe-supplier-wire`, `ex:wstep-verify`, then "Approve the payment" and "Release the
wire".

**Who.** `Role`s for the controller and the AP clerk, with `RoleAssignment`s in the context of
the organization. Executions name their performers with `performedBy`. What the plan can't
say yet is which role each Step belongs to (proposal 2).

### 2. The hypotheses

Both are tested by the Investigation (`testsHypothesis`), and each predicts the output Variable
of one search Step, with `predictedType stonework:Sighting`, meaning "this search will produce
a sighting of the technique":

| Hypothesis | Confidence | Variable bound to | Status |
|---|---|---|---|
| A forwarding rule on the controller's mailbox | 70 | `ex:sighting-controller-rule` | Confirmed |
| A forwarding rule on the clerk's mailbox | 30 | `false` | Refuted |

**Negative evidence is first-class.** The search of the clerk's mailbox is an execution like
any other, with its times, its performer and its output: `ex:log-clerk-search`, the saved
query and its empty result for 90 days. The refuted hypothesis points to it the same way the
confirmed one points to its evidence:

```sparql
SELECT ?hypothesis ?status ?result ?evidence WHERE {
  ?inv stonework:testsHypothesis ?h .
  ?h skos:prefLabel ?hypothesis ; stonework:hasHypothesisStatus ?status ;
     stonework:predictsVariable ?v .
  ?step stonework:hasOutputVariable ?v .
  ?search stonework:correspondsToStep ?step ; stonework:hasOutput ?log .
  ?log skos:prefLabel ?evidence .
  OPTIONAL { ?v stonework:boundTo ?b } OPTIONAL { ?v stonework:boundToLiteral ?bl }
  BIND(COALESCE(?b, ?bl) AS ?result)
}
```

This may make the `supportsHypothesis` / `refutesHypothesis` properties discussed earlier
unnecessary: the plan's execution already connects a hypothesis to its evidence.

### 3. The detection plan

`ex:detplan-forwarding` is a `stonework:DetectionPlan` that `implements` ATT&CK's detection
strategy **DET0576** ("Email Forwarding Rule Abuse Detection Across Platforms"), which the
CTI Encyclopedia says `detects` T1114.003. Three Steps:

1. **Search the audit log, controller's mailbox:** `New-InboxRule` / `Set-InboxRule` setting
   `ForwardTo`, `ForwardAsAttachmentTo` or `RedirectTo`, 90 days. It `implements` ATT&CK's
   analytic **AN1591** (Office Suite: "Creation of email forwarding/redirect rules in Exchange
   Online via New-InboxRule or transport rule cmdlets…").
2. **The same search, clerk's mailbox.** Also implements AN1591.
3. **Contain the mailbox.** It `implements` the control plan below, which is how the
   DetectionPlan's own definition says a confirmed violation is handed on.

Transitions from Steps 1 and 2 to Step 3 are guarded by `guardType stonework:Sighting`.

Each executed Step is an `Investigation` (the plan-execution recipe's choice for assessment
plans) that `correspondsToStep` it, `actsOn` the mailbox account, and `hasOutput` its log. The
controller search `produces` the `Sighting`: `sightedObject` T1114.003, `sightedBy` the
analyst, `sightedAt` the email tenant, `evidencedBy` the `New-InboxRule` audit record. The
whole Investigation `executionOf` the DetectionPlan, `investigates` the Incident, and is
Closed with outcome Confirmed.

### 4. The control plan

`ex:ctlplan-forwarding` is a `stonework:ControlPlan`, "Contain a malicious forwarding rule".
It `implements` NIST SP 800-53 **AC-4** (Information Flow Enforcement), which the
Encyclopedia says `mitigatesAttackPattern` T1114.003. Four Steps:

1. Disable and remove the rule, keeping a copy as evidence. *(analyst)*
2. Revoke the account's sessions and reset its credentials. *(analyst)*
3. Block automatic forwarding to external domains at the transport layer. *(automation)*
4. Review what was forwarded, and warn the suppliers and customers it exposed. *(analyst and
   controller)*

Its execution `correspondsToStep` the DetectionPlan's Step 3 and is `executionOf` the
ControlPlan, so it's both "the containment step of the investigation" and "a run of our
containment plan".

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
Hypothesis ──predictsVariable──▶ Variable ──boundTo──▶ Sighting ──sightedObject──▶ T1114.003
```

That matches the gradient in [technique-modeling.md](technique-modeling.md): the technique is
the method, and plans are its realizations, offensive, detective or defensive. The business
process is a plan of the same kind, and the attack and the business process meet at one Step
that wasn't executed.

Three kinds of performer appear: people (the clerk, the controller, the analyst), the
organization (responsible for the business process), and software (the automation that
applied the transport rule).

## Gaps, as proposals

Numbered for discussion; nothing here is in the ontology yet.

1. **A Hypothesis has no direct link to what it's about.** Here it reaches T1114.003 only
   after the fact, through its Variable's binding, or through the plan's Step and DET0576. An
   untested hypothesis, or one tested without a plan (allowed since 0.11.0), has no link at
   all. Proposal: a property from Hypothesis to its subject (the technique, actor or
   vulnerability it's about).

2. **A Step can't say which Role performs it.** Executions have performers, but the plan can't
   say "Step 2 is the AP clerk's". With it, the graph could answer *whose* step was skipped,
   and check segregation of duties (the person who enters a payment isn't the one who approves
   it). Proposal: Step → Role.

3. **No agent for plain software.** `AIAgent` is for systems with autonomous decision-making;
   the automation that applies a transport rule isn't one. The example uses a
   `DigitalIdentity` (its service account), which is a persona rather than the actor.
   Proposal: a software-agent class beside `AIAgent`, or a scope note saying which to use.

4. **The plan classes have no common parent, so properties stop at `Playbook`.**
   `performedBy`, `triggeredBy` and `playbookVersion` take a `Playbook`; a `ControlPlan`,
   `InvestigationPlan` or `DetectionPlan` can't have an owner, a version or a triggering
   event. That's Ryan's observation in ontology form: these are all plans. Proposal: a
   `stonework:Plan` class (aligned with `prov:Plan` and P-Plan's `p:Plan`) under `Behavior`,
   over the Step-structured classes (`Playbook`, `ControlPlan`, `InvestigationPlan`, and
   perhaps `Procedure`), with those properties moved to it. Techniques, tactics and controls
   stay Behaviors that plans implement.

5. **Is a business process a Playbook?** `Playbook`'s definition ("…in response to a specific
   type of event, incident, or operational need") admits it, but nobody calls the supplier
   payment process a playbook. Options: leave it as a Playbook; a subclass such as
   `BusinessProcess`; or, with proposal 4, a sibling under `Plan`.

6. **A skipped step is only an absence.** Today "the callback wasn't done" is the lack of an
   execution, which can't be told apart from "it was done but not recorded". Investigators,
   insurers and prosecutors need the deviation as a finding with its own evidence (the
   clerk's statement, the phone records). Options: an execution record with a status
   (performed, skipped, failed), or an analyst's finding (a `QualifiedAssertion`) that the step
   was not performed.

7. **Plans are executed once.** `boundTo` is functional and a Variable belongs to the plan, so
   each plan can be executed only once: the supplier payment process, run 400 times a year,
   would need a Variable per run. Step executions also aren't tied to the plan execution they
   belong to, so the skipped-step query can't tell one run from another. This example avoids
   both by giving the DetectionPlan one Step per mailbox and by having a single payment run.
   P-Plan handles it by binding each run's own entity to the plan's Variable
   (`p:correspondsToVariable`) and grouping step executions under the plan execution.
   This is the largest structural question here. Proposal: discuss adopting P-Plan's pattern.

8. **ATT&CK mitigations aren't Behaviors.** M1042, M1047 and M1060 are `Countermeasure` /
   `CourseOfAction` / `Mitigation`, so a ControlPlan that `implements` one would make a
   reasoner classify the mitigation as a `Behavior`. That's not an inconsistency (STONEWORK
   declares almost no disjoint classes) but it's a silent reclassification. NIST controls are
   already Behaviors, which is why this example's ControlPlan implements AC-4. Options: make
   `Mitigation` a `Behavior`, as `Control` is; or link a ControlPlan to a mitigation with a
   different property.

Smaller things:

- No class for an inbox or mailbox rule (STIX has none either); the example uses
  `DigitalArtifact`.
- The email's sender and recipients are in prose; `stones:fromRef` and `stones:toRefs` could
  carry them, once their alignment with `stonework:EmailMessage` is checked.
- `ex:control-callback` is an organization-defined control. If financial controls (callback
  verification, dual approval, payee-change holds) recur across cases, they may deserve their
  own catalogue, perhaps in the financial module.
