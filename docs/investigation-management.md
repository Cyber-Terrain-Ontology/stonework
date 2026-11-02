# Investigations as first-class records

*Added in STONEWORK 0.11.0.*

An investigation is at the centre of cyber security work: an analyst opens one, gathers
intelligence and evidence about something, tests hypotheses, and closes it with a
conclusion. `stonework:Investigation` already defined the activity; 0.11.0 adds what an
investigation needs as a record of work, so that its status, the people working it and its
outcome are STONEWORK facts rather than one tool's private bookkeeping.

## An investigation, end to end

```turtle
ex:inv-2026-114
    a stonework:Investigation ;
    skos:prefLabel "Outlook NTLM leak against finance hosts"@en ;
    stonework:investigates          ex:cve-2023-23397-activity ;
    stonework:examines              ex:unit42-report ;          # intelligence considered
    stonework:collects              ex:pcap-0412 ;              # evidence collected
    stonework:testsHypothesis       ex:hyp-apt28 ;
    stonework:leadInvestigator      ex:analyst-rh ;
    stonework:performedBy           ex:analyst-rh , ex:analyst-jg ;
    stonework:hasPriority           stonework:priorityHigh ;
    stonework:hasInvestigationStatus  stonework:investigationStatusClosed ;
    stonework:hasInvestigationOutcome stonework:investigationOutcomeConfirmed ;
    stonework:startedAtTime "2026-04-12T09:00:00Z"^^xsd:dateTime ;
    stonework:endedAtTime   "2026-04-22T17:00:00Z"^^xsd:dateTime ;
    stonework:producesReport        ex:inv-2026-114-report .
```

## What was added, and why

| Term | Kind | Why |
|---|---|---|
| `InvestigationStatus`, `hasInvestigationStatus` | Category scheme, functional property | Lifecycle: Open, Active, On Hold, Closed. Follows the `IncidentStatus` pattern. |
| `InvestigationOutcome`, `hasInvestigationOutcome` | Category scheme, functional property | How it ended: Confirmed, Benign, False Positive, Inconclusive. "Closed" alone doesn't say. Distinct from a Hypothesis's status: one investigation can confirm some hypotheses and refute others. |
| `PriorityLevel`, `hasPriority` | Category scheme, functional property | Critical, High, Medium, Low, for an Investigation or Incident. Priority orders work; `ImpactLevel` and `RiskLevel` assess consequence and likelihood. |
| `leadInvestigator` | Functional, ⊑ `performedBy` | `performedBy` already relates any Process to its Agents; the lead is the one accountable. Roles in a period or context use `RoleAssignment`. |
| `examines` | Object property | The intelligence an investigation considers: reports, bulletins, imported STIX bundles. `collects` stays for digital artifacts collected as evidence. |
| `testsHypothesis` | Object property | A direct link to the hypotheses, which before were reachable only through a plan's Variables. |
| `mergedInto` | Functional | When two investigations turn out to be the same matter, the merged one keeps its record and points to the survivor. |
| `refersTo` | Object property | An intelligence object to the canonical entity it refers to (a vendor's T1059 to ATT&CK's), without `owl:sameAs`. See below. |

**Changed for analysts' judgments:** `opinionOf` may now target a `QualifiedAssertion`, so an analyst can confirm or reject one proposed link (an `Opinion` with `stones:opinion` agree or disagree). `HypothesisShape` no longer requires a predicted `Variable`: a hypothesis an investigation tests directly need not belong to a plan; at most one Variable is still enforced.

**Changed:** `investigates` / `investigatedBy` no longer restrict the subject to Campaign,
Incident, MalwareSample or ThreatActor. The union range rejected nothing; it only made OWL
infer that any other subject (a vulnerability, a product's exposure, an activity cluster)
belonged to the union.

## Reviews of records

*Added in STONEWORK 0.15.0. The design and the alternatives it rejected are in
[record-review.md](record-review.md).*

An analyst working through an investigation's records records what they looked at as a
`stonework:Review`, part of the investigation, with a `ReviewFinding` of relevant or not
relevant:

```turtle
ex:review-0917
    a stonework:Review ;
    stonework:partOfExecution  ex:inv-2026-114 ;
    stonework:performedBy      ex:analyst-rh ;
    stonework:hasInput         ex:signin-0412 , ex:signin-0413 ;
    stonework:hasReviewFinding stonework:reviewFindingNotRelevant ;
    stonework:endedAtTime      "2026-04-14T15:20:00Z"^^xsd:dateTime .
```

Not relevant is relative to this investigation, and says nothing about whether the records
are true or benign: that would be an `Opinion`.

## Validation

`InvestigationShape` holds the functional properties to at most one value each (violations).
`InvestigationOutcomeShape` warns when an investigation has an outcome but isn't Closed, or
has no `endedAtTime`: incomplete, not malformed. `ReviewShape` requires a Review's one
finding, at least one input and the execution it is part of, and warns when it names no
analyst or end time.

## `refersTo` rather than `owl:sameAs`

STIX objects from different publishers often describe the same technique, CVE or malware
family under different STIX IDs. They are different STIX objects: `stones:stixId` is
functional, so `owl:sameAs` between two of them makes the data inconsistent, and with a
reasoner it would also merge each publisher's names, dates and markings onto the other.
`skos:exactMatch` avoids the merge but makes both ends `skos:Concept`s. `refersTo` says only
that the object refers to the canonical entity. A link found by a heuristic, such as an ID
parsed from an object's name, should carry its method and confidence through a
`QualifiedAssertion` or `hasProvenance`.

Evidence raises the same question. A parsed audit log names the tenant it came from, and the
organization's plan names its own tenant as a Step's target: two individuals for one thing.
The log's tenant `refersTo` the organization's. Because `refersTo` is neither symmetric nor
transitive and merges nothing, a check that compares an execution's target with its Step's
follows it explicitly, and an analyst who retracts the link retracts nothing else with it.
Two candidate links can also stand side by side until one is judged, which `owl:sameAs` would
turn into one merged individual.
