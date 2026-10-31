# Worked Example: a Business Email Compromise, as Plans

*First cut 2026-10-22, from a conversation between Ryan Hohimer and Claude; revised
2026-10-30 for STONEWORK 0.12.0, which adds `stonework:Plan`, `BusinessProcess`, per-run
Variable bindings, the Roles that perform Steps, deviations as findings, and parallel
branches, messages between plans, default branches, step outcomes and targets, and playbook
types, what a hypothesis is about and its parts, who controlled an identity when, and ATT&CK
mitigations as Behaviors (proposals 1, 2, 4 to 10, 12 and 13 to 16 below). The gaps it still runs into are
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
| 2 Sep, 03:14 | With the controller's stolen credentials, the actor creates a hidden inbox rule: mail mentioning an invoice, a payment or a wire is forwarded to an outside address and moved to RSS Feeds. | `Process` `executionOf` T1114.003 and Step 1 of the actor's `OperationPlan`, `performedBy` the controller's mailbox account, `attributedTo` the actor, `produces` the rule |
| 9 Sep | An ordinary payment: the supplier's August invoice, to the account on file. | A run of the business process |
| 15 Sep | From a lookalike of the supplier's address, the actor replies to a real invoice thread: "we've changed banks". | `EmailMessage`, `EmailAddress`; the execution of the actor's sending Step, whose output the 16 Sep run uses |
| 16 Sep | The AP clerk enters the September payment with the new bank details. The callback the process requires is never made. The controller approves, and releases a $186,400 wire to a mule account. | A second run, with no execution of the callback Step |
| 1 Oct | The clerk's statement and the phone system's call records show that the callback wasn't made, rather than made and not recorded. | A `Deviation` of kind *skipped*, with its evidence |
| 30 Sep, morning | The actor asks for another invoice to be paid to the same account. This time the clerk calls the supplier at the number on file: it hasn't changed banks, and hasn't been paid for September. | A third run, stopped at the callback |
| 30 Sep | An incident is declared and an analyst opens an investigation. | `Incident`, `Investigation` |
| 30 Sep | Two hypotheses: a forwarding rule on the controller's mailbox, and one on the clerk's. The analyst runs a detection plan built from ATT&CK's DET0576, whose search Step runs once for each mailbox. The first is confirmed, the second refuted. | `Hypothesis` ×2, `DetectionPlan`, `Sighting`; and a compound hypothesis whose parts are the activity and the attribution |
| 30 Sep – 1 Oct | The containment plan runs: the rule is removed, sessions revoked, external auto-forwarding blocked (by automation), and the exposed mail reviewed. | `ControlPlan` and its execution |

## The five pieces

### 1. The business process: paying a supplier by wire

`ex:bp-supplier-wire` is a `stonework:BusinessProcess`, `performedBy` the organization (the
Agent responsible for it), `planVersion` 3.2. Four Steps:

1. **Enter the invoice and payment request** (`performerRole` AP clerk). Input `paymentRequest`,
   `suppliedBy` the Supplier role: it comes from outside the organization (see piece 5). Output
   Variables `bankDetailsChanged` and `payeeBankDetails` (the account the request names).
2. **Verify changed bank details by callback** (AP clerk). Input `payeeBankDetails`: the
   account Step 1 recorded is what the callback checks. Output `callbackVerified`. The Step
   `implements` the organization's own control `ex:control-callback`, a `stonework:Control`
   ("FIN-07: a change to a payee's bank details is verified by phone, at a number already on
   file").
3. **Approve the payment** (controller).
4. **Release the wire** (controller).

Each Step's `performerRole` names the Role whose holder is expected to do it, as a BPMN lane
does. Step 1 is `separatedFrom` Step 3: whoever enters a payment may not approve it.

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

**From an absence to a finding.** The query finds that the run has no execution of the
callback, which shows only that none was recorded. The finding that it wasn't done is
`ex:dev-0916-callback`, a `stonework:Deviation` (a `QualifiedAssertion`) that the
Investigation `produces`: `deviationKind` *skipped*, `deviationRun` the 16 September run,
`deviationStep` the callback, and `evidencedBy` the clerk's statement and the call records.
The control that failed is reached through the Step, and the role whose step it was through
`performerRole`:

```sparql
SELECT ?run ?kind ?step ?role ?control ?evidence WHERE {
  ?d a stonework:Deviation ; stonework:deviationRun ?run ;
     stonework:deviationKind/skos:prefLabel ?kind ;
     stonework:deviationStep ?s ; stonework:evidencedBy ?e .
  ?s skos:prefLabel ?step .
  OPTIONAL { ?s stonework:performerRole/skos:prefLabel ?role }
  OPTIONAL { ?s stonework:implements/skos:prefLabel ?control }
  ?e skos:prefLabel ?evidence .
}
```

→ the 16 September run, *Skipped*, the callback, the AP clerk's, FIN-07, on the statement
and on the call records. The other kinds are *wrong role*, *same agent*, *out of order* and
*misused identity*. A Deviation names the executions it concerns with `deviationExecution`,
except for a skipped Step, which has none.

**Who, and through which identity.** `Role`s for the controller and the AP clerk, with
`RoleAssignment`s in the context of the organization. Executions name their performers with
`performedBy`, as observed. When the evidence shows only an identity, the performer is that
identity: the bank's portal records that the controller's bank-portal login
(`ex:acct-controller-bank`) released the wire, and the audit log that the controller's
mailbox account created the forwarding rule. The person behind an identity is reached
through `accountOf` (or `attributedToAgent`). When someone else used the identity, the
activity keeps the identity as its performer and names who is believed responsible with
`attributedTo`: the rule's creation is `performedBy` the controller's mailbox account and
`attributedTo` the actor.

This matters because the checks see identities. Each execution is checked against its Step's
`performerRole`, and each run against `separatedFrom`, with three possible answers:

```sparql
# Was each step execution done by a holder of the Step's role?
SELECT ?run ?step ?performer ?result WHERE {
  ?run stonework:executionOf ?plan .
  ?plan stonework:hasStep ?s .
  ?s stonework:performerRole ?role ; skos:prefLabel ?step .
  ?exe stonework:correspondsToStep ?s ; stonework:partOfExecution ?run .
  OPTIONAL { ?plan stonework:performedBy ?ctx }
  OPTIONAL { ?exe stonework:performedBy ?performer }
  OPTIONAL { ?performer stonework:accountOf|stonework:attributedToAgent ?holder }
  BIND(COALESCE(?holder, ?performer) AS ?agent)
  BIND(
    IF(!BOUND(?performer), "undetermined: no performer",
    IF(!BOUND(?holder) && EXISTS { ?performer a/rdfs:subClassOf* stonework:DigitalIdentity },
       "undetermined: identity with no known holder",
    IF(EXISTS { ?exe stonework:attributedTo ?other FILTER(?other != ?agent) },
       "undetermined: attributed to another agent",
    IF(EXISTS { ?ra stonework:rolePlayer ?agent ; stonework:assignedRole ?role ;
                    stonework:roleContext ?ctx },
       "conforms", "wrong role")))) AS ?result)
}
```

In this example every execution conforms, and Steps 1 and 3 had different performers in
both runs that reached approval. (Tested against variants of the example: a clerk who
approves is reported as *wrong role* and *same agent*, an unattributed account and a release
attributed to the actor as *undetermined*.) "Undetermined" is deliberate. A check that can't
resolve a performer to a person, or whose identity may have been misused, mustn't report
the run as conforming. And no check over logs can see the commonest BEC move, an actor
working through a role holder's own account: the role is right, and the separation can even
look right. That is what the *misused identity* kind is for, established by an analyst from
evidence such as sign-ins from an unfamiliar address.

One thing the example shows without meaning to: the controller both approves and releases.
Many organizations accept that, and this one's plan doesn't forbid it, so no check flags it,
but it's the single point where one stolen login moves money. A plan that wanted dual
control would make Step 4 `separatedFrom` Step 3.

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

**What each is about.** `stonework:hypothesisAbout` links each hypothesis to T1114.003 and
to the mailbox account it names. It may have several values, and carries no roles: it is for
finding hypotheses, not for judging them.

**A compound hypothesis, and which part failed.** The investigation's real question is
bigger than either search: *the actor who sent the bank-change email diverted the wire by
reading the controller's mail through a forwarding rule*. That is two claims, tested in
different ways:

| Hypothesis | Confidence | Status |
|---|---|---|
| The email's sender diverted the wire through a forwarding rule (the compound) | 60 | Pending |
| ↳ A forwarding rule on the controller's mailbox (the activity) | 70 | Confirmed, by the search |
| ↳ The rule's creator sent the bank-change email (the attribution) | 60 | Pending |

The compound has both as `stonework:hypothesisPart`: it holds only if every part holds. The
search can confirm the activity; only attribution evidence can settle who set the rule, and
the rule was created through the controller's own account and the email came from an address
registered to no one known. So the compound stays pending, and the table says why. Had the
attribution been refuted (someone else set the rule), the compound would be refuted, the
refuted part would say which claim failed, and the confirmed activity would survive for a new
hypothesis. Alternatives, such as "the actor or an insider", are competing hypotheses, not
parts of one.

The compound's status and confidence are stated, not inferred, so a query checks them
against the parts:

```sparql
SELECT ?compound ?part ?problem WHERE {
  ?c stonework:hypothesisPart+ ?p ; skos:prefLabel ?compound ;
     stonework:hasHypothesisStatus ?cs .
  ?p skos:prefLabel ?part ; stonework:hasHypothesisStatus ?ps .
  OPTIONAL { ?c stonework:confidence ?cc } OPTIONAL { ?p stonework:confidence ?pc }
  BIND(IF(?cs = stonework:hypothesisStatusConfirmed
          && ?ps != stonework:hypothesisStatusConfirmed,
          "confirmed, but this part is not",
       IF(?ps = stonework:hypothesisStatusRefuted
          && ?cs != stonework:hypothesisStatusRefuted,
          "this part is refuted, but the compound is not",
       IF(BOUND(?cc) && BOUND(?pc) && ?cc > ?pc,
          "more confident than this part", ""))) AS ?problem)
  FILTER(?problem != "")
}
```

→ nothing here. With the attribution refuted and the compound left pending, it returns "this
part is refuted, but the compound is not"; with the compound marked confirmed at 90, it
returns "confirmed, but this part is not" and "more confident than this part".

A compound is about whatever its parts are about, so "everything hypothesized about
T1114.003" follows the parts:

```sparql
SELECT DISTINCT ?hypothesis ?status WHERE {
  ?h stonework:hypothesisPart*/stonework:hypothesisAbout ?t .
  ?t stonework:attackId "T1114.003" .
  ?h skos:prefLabel ?hypothesis ; stonework:hasHypothesisStatus ?status .
}
```

→ all three: the two mailbox hypotheses and the compound.

### 3. The detection plan

`ex:detplan-forwarding` is a `stonework:DetectionPlan` that `implements` ATT&CK's detection
strategy **DET0576** ("Email Forwarding Rule Abuse Detection Across Platforms"), which the
CTI Encyclopedia says `detects` T1114.003. Its `hasPlaybookType` is *detection*. Four Steps:

1. **Search the audit log for forwarding rules on a mailbox:** `New-InboxRule` /
   `Set-InboxRule` setting `ForwardTo`, `ForwardAsAttachmentTo` or `RedirectTo`, 90 days.
   Input `mailbox`, output `forwardingRuleFound`. It `implements` ATT&CK's analytic
   **AN1591** (Office Suite: "Creation of email forwarding/redirect rules in Exchange Online
   via New-InboxRule or transport rule cmdlets…").
   Its `outcomeVariable` is `searchOutcome`: whether the search worked (*succeeded*, *failed*
   or *timed out*), kept apart from what it found.
2. **Contain the mailbox.** It `implements` the control plan below, which is how the
   DetectionPlan's own definition says a confirmed violation is handed on.
3. **Escalate to the mail administrator**, if the audit log couldn't be searched.
4. **Record a negative result.**

Three Transitions leave Step 1, one for each way a search can end:

- to Step 2, guarded by `guardType stonework:Sighting` on `forwardingRuleFound`: a rule was
  found;
- to Step 3, guarded by `guardValue stonework:executionOutcomeFailed` on `searchOutcome`:
  the search didn't work (CACAO's `on_failure`);
- to Step 4, the Step's `defaultTransition`: neither guard held, so the search worked and
  found nothing. The default carries no guard, so the plan doesn't have to spell out "not a
  Sighting and not failed".

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

Both searches bind `searchOutcome` to *succeeded*: the clerk's found nothing, but it worked.
**Did each search take the right branch?** The guarded Transition whose guard held, or else
the default; and was it followed, by an execution that used the search's output?

```sparql
SELECT ?execution ?branch ?taken WHERE {
  ?s stonework:defaultTransition ?d .
  ?e stonework:correspondsToStep ?s ; skos:prefLabel ?execution .
  OPTIONAL {                                       # a guarded Transition that held
    ?t stonework:fromStep ?s ; stonework:guardVariable ?gv ; stonework:toStep ?gto .
    ?b stonework:bindingOf ?gv ; stonework:boundIn ?e .
    { ?t stonework:guardValue ?g . ?b stonework:boundTo ?g }
    UNION { ?t stonework:guardType ?gt . ?b stonework:boundTo ?bo . ?bo a/rdfs:subClassOf* ?gt }
    UNION { ?t stonework:guardLiteralValue ?gl . ?b stonework:boundToLiteral ?gl } }
  ?d stonework:toStep ?dto .
  BIND(COALESCE(?gto, ?dto) AS ?next)              # otherwise, the default
  ?next skos:prefLabel ?branch .
  BIND(IF(EXISTS { ?x stonework:correspondsToStep ?next ; stonework:usedBinding ?ub .
                   ?ub stonework:boundIn ?e }, "yes", "no execution found") AS ?taken)
} ORDER BY ?execution
```

→ the clerk's search: "Record a negative result", yes; the controller's: "Contain the
mailbox", yes. Had the clerk's search failed, the branch would be "Escalate to the mail
administrator", with no execution found: a candidate *skipped* Deviation.

### 4. The control plan

`ex:ctlplan-forwarding` is a `stonework:ControlPlan`, "Contain a malicious forwarding rule".
It `implements` NIST SP 800-53 **AC-4** (Information Flow Enforcement), which the
Encyclopedia says `mitigatesAttackPattern` T1114.003. Its `hasPlaybookType` is *mitigation*.
Its input Variable `accountToContain` is bound, in each run, to the account whose mailbox has
the rule. Four Steps, two of them in parallel:

```
Disable and remove the rule, keeping a copy as evidence      splitKind parallel
  ├─► Revoke the account's sessions and reset its credentials     ─┐
  └─► Block automatic forwarding to external domains              ─┤
Review what was forwarded, and warn those it exposed  ◄────────────┘  joinKind parallel
```

The rule is removed first, so the evidence is kept before anything else changes. The
credential reset (the analyst) and the transport block (automation) don't depend on each
other, so the plan doesn't put them in an order: the removal's `splitKind` is
`flowKindParallel`, and both of its Transitions are taken. The review (the analyst and the
controller) waits for both: its `joinKind` is `flowKindParallel`. Written as a sequence, the
plan would claim an order nobody intends, and a run that blocked forwarding before resetting
the credentials would look out of order.

**Targets.** The credential reset's `stepTarget` is the Variable `accountToContain`: whatever
account the run is containing. The transport block's is the mail tenant itself, the same in
every run. A run is checked by comparing each execution's `actsOn` with the target:

```sparql
SELECT ?run ?step ?expected ?actual ?verdict WHERE {
  ?e stonework:correspondsToStep ?s ; stonework:partOfExecution ?run .
  ?s stonework:stepTarget ?t ; skos:prefLabel ?step .
  OPTIONAL { ?t a stonework:Variable .                        # a Variable: its value
             ?b stonework:bindingOf ?t ; stonework:boundIn ?run ;  # in this run
                stonework:boundTo ?bound }
  BIND(IF(EXISTS { ?t a stonework:Variable }, ?bound, ?t) AS ?expected)
  OPTIONAL { ?e stonework:actsOn ?actual }
  BIND(IF(!BOUND(?expected) || !BOUND(?actual), "undetermined",
       IF(?actual = ?expected, "conforms", "wrong target")) AS ?verdict)
} ORDER BY ?run ?step
```

→ both conform: the reset acted on the controller's mailbox account, the run's value of
`accountToContain`, and the block on the mail tenant. Had the reset been run against the
clerk's account, it would be *wrong target*, a Deviation kind; with no binding of
`accountToContain`, *undetermined*.

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

**Did the review wait for both branches?** A parallel join is checked against the branches
taken in the same run: each incoming Transition whose from-Step has an execution in the run,
and whose guard, if any, held against that execution's binding.

```sparql
# Did each parallel join wait for every branch taken in its run?
SELECT ?run ?join ?branch ?ended ?started ?verdict WHERE {
  ?j stonework:joinKind stonework:flowKindParallel ; skos:prefLabel ?join .
  ?je stonework:correspondsToStep ?j ; stonework:partOfExecution ?run .
  ?t stonework:toStep ?j ; stonework:fromStep ?f .            # an incoming Transition
  ?fe stonework:correspondsToStep ?f ; stonework:partOfExecution ?run .
  ?f skos:prefLabel ?branch .
  FILTER (NOT EXISTS { ?t stonework:guardVariable ?any }      # taken: unguarded,
    || EXISTS { ?t stonework:guardVariable ?gv .              # or its guard held
        ?b stonework:bindingOf ?gv ; stonework:boundIn ?fe .
        { ?t stonework:guardLiteralValue ?gl . ?b stonework:boundToLiteral ?gl }
        UNION
        { ?t stonework:guardType ?gt . ?b stonework:boundTo ?bo .
          ?bo a/rdfs:subClassOf* ?gt } })
  OPTIONAL { ?fe stonework:endedAtTime ?ended }
  OPTIONAL { ?je stonework:startedAtTime ?started }
  BIND(IF(!BOUND(?ended) || !BOUND(?started), "undetermined",
       IF(?started >= ?ended, "conforms", "out of order")) AS ?verdict)
} ORDER BY ?run ?join ?branch
```

→ the reset ended 16:05:00 and the block 16:06:04 on 30 September; the review started at
16:30. Both rows conform. A review started at 16:06:00 would be *out of order* against the
block, and a branch with no recorded end time gives *undetermined*. (The guard test here is
equality only; `guardOperator` would extend it.)

A join can only wait for branches that were performed, so a branch the split took but the
run never performed needs its own query. It's a candidate *skipped* Deviation:

```sparql
SELECT ?run ?split ?missing WHERE {
  ?s stonework:splitKind stonework:flowKindParallel ; skos:prefLabel ?split .
  ?se stonework:correspondsToStep ?s ; stonework:partOfExecution ?run .
  ?t stonework:fromStep ?s ; stonework:toStep ?m .            # an outgoing Transition
  FILTER (NOT EXISTS { ?t stonework:guardVariable ?any }      # taken (as above)
    || EXISTS { ?t stonework:guardVariable ?gv .
        ?b stonework:bindingOf ?gv ; stonework:boundIn ?se .
        { ?t stonework:guardLiteralValue ?gl . ?b stonework:boundToLiteral ?gl }
        UNION
        { ?t stonework:guardType ?gt . ?b stonework:boundTo ?bo .
          ?bo a/rdfs:subClassOf* ?gt } })
  FILTER NOT EXISTS { ?x stonework:correspondsToStep ?m ; stonework:partOfExecution ?run }
  ?m skos:prefLabel ?missing .
}
```

→ nothing here. With the block's execution removed, it returns the block; with the block's
Transition guarded on a binding that didn't hold, it returns nothing, since that branch was
never taken.

**ATT&CK mitigations.** The transport block also `implements` ATT&CK M1042, *Disable or
Remove Feature or Program*, which the Encyclopedia links to T1114.003 alongside AC-4; and the
business process's callback Step implements M1060, *Out-of-Band Communications Channel*, as
well as FIN-07. A mitigation is a `Behavior`, like a NIST control, so this is the same
`implements` that links a plan to a control. Which of the technique's mitigations does the
organization carry out, and where?

```sparql
SELECT ?id ?mitigation ?step ?plan WHERE {
  ?t stonework:attackId "T1114.003" .
  ?m stonework:mitigatesAttackPattern ?t ; stonework:attackId ?id ; skos:prefLabel ?mitigation .
  OPTIONAL { ?s stonework:implements ?m ; skos:prefLabel ?step .
             OPTIONAL { ?s stonework:isStepOf ?p . ?p skos:prefLabel ?plan } }
} ORDER BY ?id
```

→ M1041, *Encrypt Sensitive Information*: none; M1042: "Block automatic forwarding to
external domains at the transport layer", in the containment plan; M1047, *Audit*: none;
M1060: "Verify changed bank details by callback", in the business process. The two empty rows
are the technique's mitigations nothing here implements.

### 5. The actor's plan, and the message that crosses into ours

`ex:opplan-bec` is a `stonework:OperationPlan`, "Divert a supplier payment by email": the
actor's plan as the investigation reconstructs it, with `hasPlaybookType` *attack*. Three Steps,
in order:

1. Create a hidden forwarding rule on a finance mailbox. It `implements` T1114.003.
2. Read the forwarded invoice threads, and pick an invoice that is due.
3. Send a bank-change request from a lookalike address. Output `paymentRequest`.

Its run, `ex:run-actor-op`, is `attributedTo` the actor. The rule's creation on 2 September is
the execution of Step 1, and the email sent on 15 September is the execution of Step 3, whose
output is the email.

**A message is data flow between two plans.** Step 3's output Variable, `paymentRequest`, is
the input Variable of the business process's first Step. Within a plan, a shared Variable is
ordinary data flow; between plans, it's a message from one participant to another (BPMN's
message flow between pools). Control never crosses: a `Transition` stays inside its plan, so
the actor can hand the organization a payment request but can't make the clerk do anything
with it. In the 16 September run, the binding of `paymentRequest` is `boundIn` the actor's
sending execution, and the clerk's "enter the invoice" execution records `usedBinding` of it.

**When the sender's plan isn't modelled,** `stonework:suppliedBy` names the Role whose
holders supply the value: `paymentRequest` is `suppliedBy` the Supplier role. The value is
then bound in the execution that received it.

`paymentRequest` therefore has two possible sources: a real supplier, and the actor's plan.
The clerk's Step can't tell them apart, which is exactly why the business process has the
callback Step and the FIN-07 control. The graph shows that reasoning directly.

**Attack surface:** the Steps that take input from outside their own plan, and where it can
come from:

```sparql
SELECT ?step ?input ?kind ?source WHERE {
  ?s stonework:hasInputVariable ?v ; stonework:isStepOf ?plan ; skos:prefLabel ?step .
  ?v stonework:variableName ?input .
  { ?v stonework:suppliedBy ?r .  ?r skos:prefLabel ?source .
    BIND("participant" AS ?kind) }
  UNION
  { ?o stonework:hasOutputVariable ?v ; stonework:isStepOf ?other ; skos:prefLabel ?source .
    BIND(IF(EXISTS { ?other a stonework:OperationPlan }, "adversary plan", "another plan")
         AS ?kind) }
  FILTER(!BOUND(?other) || ?other != ?plan)
} ORDER BY ?step ?kind
```

→ "Enter the invoice and payment request | paymentRequest | adversary plan | Send a
bank-change request from a lookalike address" and "… | participant | Supplier".

**Messages received in runs:** a binding made in an execution of another plan.

```sparql
SELECT ?run ?receiver ?message ?sender ?sentBy WHERE {
  ?re stonework:usedBinding ?b ; stonework:partOfExecution ?run ;
      stonework:correspondsToStep ?rs .
  ?rs stonework:isStepOf ?rp ; skos:prefLabel ?receiver .
  ?b stonework:boundIn ?se ; stonework:boundTo ?m .
  ?se stonework:correspondsToStep ?ss .
  ?ss stonework:isStepOf ?sp ; skos:prefLabel ?sender .
  FILTER(?sp != ?rp)
  ?m skos:prefLabel ?message .
  OPTIONAL { ?se stonework:attributedTo ?a . ?a skos:prefLabel ?sentBy }
}
```

→ run-wire-0916 | Enter the invoice and payment request | Email: "Updated remittance details"
| Send a bank-change request from a lookalike address | Unidentified BEC actor.

The 9 September request, from the real supplier, isn't recorded as a binding here, and nor is
the actor's second request on 30 September; the example keeps to the run that matters.

**Who controlled the account, and when.** The rule was created through the controller's own
mailbox account, so the logs name the account, not the actor. `ex:ctl-actor-mailbox` is a
`stonework:IdentityControl`: the actor controlled that account from the rule's creation on 2
September until the credential reset on 30 September, with confidence 80, evidenced by the
New-InboxRule record and the sign-in log. It isn't exclusive: the controller kept using the
account the whole time. So every execution performed through the account in the interval, and
not already attributed, needs review:

```sparql
SELECT ?execution ?when ?controller WHERE {
  ?c a stonework:IdentityControl ; stonework:controlledIdentity ?id ;
     stonework:controllingAgent ?a ; stonework:validFrom ?from .
  OPTIONAL { ?c stonework:validUntil ?until }
  ?e stonework:performedBy ?id ; stonework:startedAtTime ?when ; skos:prefLabel ?execution .
  FILTER(?when >= ?from && (!BOUND(?until) || ?when < ?until))
  FILTER NOT EXISTS { ?e stonework:attributedTo ?anyone }
  ?a skos:prefLabel ?controller .
} ORDER BY ?when
```

→ the 12 September sign-in at 03:40 from the rule's IP address, and the 16 September sign-in
from the controller's workstation, both with "Unidentified BEC actor". The rule's creation is
in the interval too, but it's already attributed. Review sorts the two: the first is the actor
reading the mail, the second is the controller.

## What it shows about plans

Every link from this case to T1114.003 goes through a plan or a plan's execution, and none
needs the technique itself to be a plan:

```
attacker's Process ──executionOf──────────────────────────────────▶ T1114.003
DetectionPlan ──implements──▶ DET0576 ──detects───────────────────▶ T1114.003
  Step ──implements──▶ AN1591 (an analytic of DET0576)
ControlPlan ──implements──▶ AC-4 ──mitigatesAttackPattern─────────▶ T1114.003
  Step ──implements──▶ M1042 ──mitigatesAttackPattern─────────────▶ T1114.003
Hypothesis ──predictsVariable──▶ Variable ◀──bindingOf── VariableBinding
                                   ──boundTo──▶ Sighting ──sightedObject──▶ T1114.003
```

That matches the gradient in [technique-modeling.md](technique-modeling.md): the technique is
the method, and plans are its realizations, offensive, detective or defensive. Since 0.12.0
they share one parent, `stonework:Plan`, and the business process is one of them: the attack
and the business process meet at one Step that a run went on without.

Four kinds of performer appear: people (the clerk, the controller, the analyst), the
organization (responsible for the business process), software (the automation that applied
the transport rule), and identities standing in for people (the logins the logs record).

The plan model covers much of the ground of BPMN (processes, tasks, sequence flows with
conditions, data objects), and the skipped-step query is what process mining calls
conformance checking: comparing a run's event trace against the process model. What BPMN
lacks, and STONEWORK adds, is the adversary's plan beside the organization's, and the
hypothesis-and-evidence layer.

## Gaps, as proposals

Numbered for discussion. Proposals 1, 2, 4 to 10, 12 and 13 to 16 are done in 0.12.0;
the rest are not in the ontology yet.

1. **Done in 0.12.0: what a hypothesis is about, and its parts.** `stonework:hypothesisAbout`
   (Hypothesis → anything, not functional) links a hypothesis to the technique, actor,
   account, asset or event it concerns, for finding hypotheses. It has no roles, so a claim
   whose parts can fail separately ("X is doing Y": the activity and the attribution) is a
   compound with `stonework:hypothesisPart` (Hypothesis → Hypothesis): it holds only if every
   part holds, each part has its own test, status and confidence, and the refuted parts say
   which claim failed. Conjunction only; alternatives are competing hypotheses. The
   compound's status stays explicit, checked against its parts by a query.

2. **Done in 0.12.0: a Step names the Role that performs it.** `stonework:performerRole`
   (Step → Role; BPMN's lane), so the graph answers *whose* step was skipped. A holder of any
   one of the Roles listed may do the Step; dual control is two Steps. Segregation of duties is
   `stonework:separatedFrom` (symmetric, Step ↔ Step): in any one run, the two Steps are
   performed by different Agents. Roles alone can't enforce that, since one person can hold
   both. Runs record performers as observed, often an identity, and the checks resolve an
   identity to its holder through `accountOf` or `attributedToAgent`, reporting
   *undetermined* when they can't.

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

6. **Done in 0.12.0: a deviation is a finding with its own evidence.** `stonework:Deviation`
   (⊑ `QualifiedAssertion`), with `deviationRun` (functional), `deviationStep`,
   `deviationExecution`, `deviationKind` (functional; *skipped*, *wrong role*, *same agent*,
   *out of order*, *misused identity*, *wrong target*) and `evidencedBy`, whose domain now takes a Deviation
   as well as a Sighting. Queries propose candidates; the Deviation is the analyst's finding,
   so "not done" is told apart from "not recorded" by its evidence. Executions don't get a
   status: a skipped execution would be a record of something that never happened, and a
   failed one (the callback was tried and nobody answered) is an execution whose outcome is
   its output Variable.

7. **Done in 0.12.0: a plan can be run any number of times.** Each run is the execution that
   is `executionOf` the plan; its Steps' executions are `partOfExecution` it; and each value
   is a `VariableBinding` (`bindingOf` the Variable, `boundIn` the execution that bound it,
   `boundTo` or `boundToLiteral` the value). A later Step's execution records the binding it
   received with `usedBinding`. This follows P-Plan's pattern, with a binding node so that
   literal values are handled the same way as individuals. `boundTo` and `boundToLiteral` no
   longer go on the Variable itself.

8. **Done in 0.12.0: ATT&CK mitigations are Behaviors.** `stonework:Mitigation` (and so
   `CourseOfAction` and `attack:Mitigation`) is now a `Behavior` as well as a
   `Countermeasure`, as `Control` already was: a specification of how to act. A ControlPlan
   or Step that `implements` an ATT&CK mitigation no longer makes a reasoner reclassify the
   mitigation, and one property links plans to NIST controls and ATT&CK mitigations alike.
   Detection logic (`DetectionRule`, `Signature`) stays out of `Behavior`.

9. **Done in 0.12.0: parallel branches.** `stonework:splitKind` and `stonework:joinKind`
   (Step → `FlowKind`: exclusive or parallel, both defaulting to exclusive, the meaning
   Transitions already had). A parallel split takes every outgoing Transition whose guard
   holds, so guarded Transitions give BPMN's inclusive split as well as its parallel one; a
   parallel join waits for every branch taken in the run. There are no gateway nodes: as in
   YAWL, the split or join belongs to the Step, and a BPMN gateway maps onto the Step next to
   it. `precededByStep` now says a Step follows all of its predecessors, so a plain dependency
   graph expresses parallel work without guards. The containment plan uses both properties.

10. **Done in 0.12.0: messages between participants.** A message is data flow between Steps
    of different Plans: the sending Step's output Variable is the receiving Step's input
    Variable, and in a run the receiving execution records `usedBinding` of the sender's
    binding. Control (`Transition`) never crosses Plans. When the sender's plan isn't
    modelled, `stonework:suppliedBy` (Variable → Role) names who supplies the value. No
    `MessageFlow` class: the Variables already say it. The channel (email, phone, an
    authenticated portal) matters for risk and is parked.

11. **A ThreatScenario and an OperationPlan are close.** Both are adversary plans: one held as
    a hypothesis, the other believed to exist. A link between them ("this operation matches
    that scenario") may be wanted later. Parked; the example now has an OperationPlan,
    reconstructed by the investigation, but no ThreatScenario.

12. **Done in 0.12.0: who controlled an identity, and when.** `stonework:IdentityControl`
    (⊑ `QualifiedAssertion`, like `RoleAssignment`) records that an Agent
    (`stonework:controllingAgent`) controlled a DigitalIdentity (`stonework:controlledIdentity`)
    from `validFrom` to `validUntil`, with evidence (`evidencedBy`), provenance and confidence.
    It sits between `attributedToAgent` (whose the identity is, timeless) and `attributedTo`
    (who did one thing). Control isn't exclusive, so the executions through the identity in the
    interval that aren't yet attributed are the ones to review; the query is in section 5. No
    timeless projection property, since it would lose the interval.

Proposals 13 to 19 came from comparing plans with OASIS CACAO 2.0 (see
[plan-execution-model.md §7](plan-execution-model.md#7-relationship-to-oasis-cacao)). Each is
something a CACAO playbook could say that a STONEWORK plan couldn't, so importing it would
lose it. The four small ones, 13 to 16, are done; 17 to 19 remain.

13. **Done in 0.12.0: a default branch.** `stonework:defaultTransition` (Step → Transition,
    functional) is the Transition taken when no other outgoing Transition's guard holds: CACAO's
    switch `default` and BPMN's default flow. It sits on the Step, so a Step has at most one.

14. **Done in 0.12.0: an outcome Variable.** `stonework:outcomeVariable` (functional, ⊑
    `hasOutputVariable`) marks the output Variable that records whether an execution
    worked, and its values come from a new `ExecutionOutcome` scheme: *succeeded*, *failed*,
    *timed out*. A new guard, `stonework:guardValue` (Transition → any individual,
    functional), tests "is this individual", which `guardType` and `guardLiteralValue`
    couldn't; it mirrors `predictedValue`. CACAO's `on_success` and `on_failure` are
    Transitions guarded on the outcome Variable.

15. **Done in 0.12.0: targets on a Step.** `stonework:stepTarget` (Step → CyberEntity) is what
    a Step is meant to act on: a specific entity, or a Variable whose value in the run is the
    target. It mirrors `actsOn` on the run, as `performerRole` mirrors `performedBy`. An
    execution that acted on something else is a new Deviation kind, *wrong target*.

16. **Done in 0.12.0: playbook types.** A `PlaybookType` scheme with CACAO's eight types
    (attack, detection, engagement, investigation, mitigation, notification, prevention,
    remediation), applied with `stonework:hasPlaybookType` (Plan → PlaybookType, not
    functional). No new classes: the existing Plan subclasses have properties of their own,
    and engagement and notification plans don't. The scope note maps each subclass to its
    type; the type is stated, not inferred, because a ControlPlan can be any of three.

17. **Guards test one Variable.** A CACAO `condition` is a STIX Patterning expression, so it
    can combine tests with AND, OR and NOT across several variables. A STONEWORK guard
    compares one Variable with one value or class. Proposal: discuss whether to carry the
    expression as a literal (simple, but not queryable), allow several guards on one
    Transition joined by AND (covers most cases), or model expressions as nodes.

18. **No exception path for a whole plan.** CACAO's `workflow_exception` names where control
    goes when a step fails and has no `on_failure` of its own. STONEWORK has no plan-level
    fallback, so every failure path has to be drawn as Transitions. Proposal: a property from
    a Plan to the Step (or Plan) that handles any failure not otherwise handled.

19. **No delays or timeouts.** CACAO steps can wait before starting (`delay`) and fail after a
    time limit (`timeout`, which invokes `on_failure`). A STONEWORK plan has no durations, so
    it can't say "if the supplier hasn't called back within a day, escalate". This matters for
    business processes as well as playbooks. Proposal: discuss durations on Steps, and
    whether a timeout is a guard on time elapsed or a separate kind of Transition.

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
