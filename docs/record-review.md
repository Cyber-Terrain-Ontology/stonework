# Design: an analyst's review of records

*Designed 2026-11-01 and released in STONEWORK 0.15.0 (categories 0.6.0). Proposal 20 in
[bec-worked-example.md](bec-worked-example.md#gaps-as-proposals).*

## The gap

An investigation starts with more records than matter. The BEC case's seven evidence files
parse into 677 records: sign-ins, mailbox audit entries, portal actions, call records,
messages. Most are routine: other staff signing in, the clerk's ordinary mail. An analyst
works through them, places the ones that matter in runs of a plan, attributes them,
and decides that the rest have nothing to do with the case.

STONEWORK can record every one of those judgments except the last. "I looked at these and
they don't matter here" has no term, so the work is lost: the next analyst, or the same one
next week, looks through the same records again, and nothing says which records were looked
through and which were never opened.

None of the terms that already exist fit:

- **`Opinion`** is "an analyst's stance on the correctness or credibility of information"
  (STIX's opinion: agree to disagree). A sign-in record that doesn't matter here is still
  correct, so calling it an Opinion would bend the term.
- **`examines`** and **`collects`** relate an Investigation to intelligence products and to
  DigitalArtifacts. Records are mostly Events, and these properties say what an investigation
  used, not what it concluded about it.
- **A status on the record itself** (an Event marked "dismissed") loses who decided, when,
  and for which investigation. The same sign-in can be noise in one investigation and the
  key record in another.

## Proposal

Record a review as an activity in the investigation, the way the investigation's other
work is recorded, and add one category for what it found.

### New terms

```turtle
stonework:Review
    a owl:Class ;
    rdfs:subClassOf stonework:Process ;
    skos:prefLabel "Review"@en ;
    skos:definition "An analyst's examination of records or artifacts, as part of an
        investigation, ending in a judgment of whether they are relevant to it."@en ;
    skos:scopeNote "The records reviewed are stonework:hasInput; the investigation is the
        execution the review is stonework:partOfExecution (and, when the investigation follows
        an InvestigationPlan, the Step it carries out is stonework:correspondsToStep); the
        analyst is stonework:performedBy; when, stonework:startedAtTime and
        stonework:endedAtTime. What it found is stonework:hasReviewFinding, which applies to
        every input: records found relevant and records found not relevant are two Reviews.
        A later Review of the same record in the same investigation supersedes an earlier
        one; both stay as the record of the work."@en .

stonework:ReviewFinding               # categories.ttl, a Category scheme
    skos:definition "A classification of what a review found about the records it
        examined, relative to the investigation it is part of."@en .

stonework:reviewFindingRelevant
    skos:definition "The records bear on the investigation and are kept for analysis."@en .
stonework:reviewFindingNotRelevant
    skos:definition "The records were examined and do not bear on the investigation. They
        are not judged false or benign, only not relevant here."@en .

stonework:hasReviewFinding
    a owl:ObjectProperty , owl:FunctionalProperty ;
    rdfs:subPropertyOf stonework:categorizedBy ;
    rdfs:domain stonework:Review ;
    rdfs:range stonework:ReviewFinding .
```

That's one class, one scheme with two values, and one property. Everything else
(`partOfExecution`, `performedBy`, `hasInput`, the times) already exists, and since 0.14.0
`hasInput` and `performedBy` take any activity, so a Review can take Events, Files and Logs
as inputs.

### Example

```turtle
ex:review-0917
    a stonework:Review ;
    stonework:partOfExecution  ex:inv-bec-t1114-003 ;
    stonework:performedBy      ex:analyst-rh ;
    stonework:hasInput         ex:signin-0412 , ex:signin-0413 , ex:signin-0419 ;
    stonework:hasReviewFinding stonework:reviewFindingNotRelevant ;
    stonework:endedAtTime      "2026-10-31T15:20:00Z"^^xsd:dateTime ;
    skos:note "Routine sign-ins by payroll staff, all from the office network."@en .
```

### Why an activity

- **Who, when and where come with it.** The analyst, the time and the investigation are the
  properties every Process already has, so nothing new is needed for them.
- **It fits the plan model.** An investigation is the run of an InvestigationPlan. A plan
  with a "triage the sign-ins" Step is carried out by Reviews that `correspondsToStep` it, so
  the skipped-step query can show triage that was never done, like any other Step.
- **It mirrors the established model.** CASE/UCO, the forensic community's ontology, records
  an examiner's work as an `InvestigativeAction`: performer, the objects acted on and the
  results, with times. A Review is the same pattern, narrowed to one judgment.
- **It is evidence-neutral.** "Not relevant" says nothing about whether the record is true,
  benign or malicious. That keeps it apart from `Opinion` (correctness), from
  `InvestigationOutcome` (how the whole investigation ended) and from `Incident` triage
  (whether something adverse happened).

### Rejected alternatives

| Alternative | Why not |
|---|---|
| Record nothing; filters hide records | Simplest, but leaves no record of the work: another analyst can't tell reviewed from unopened. |
| A category on the record (`hasTriageDisposition`) | Loses who, when and which investigation; a record can matter to one investigation and not another. |
| A `QualifiedAssertion` subclass, like `Deviation` | Workable, but a review is something done, not a claimed relationship, and as an activity it gets performer, times and Step correspondence for free. `Deviation` and `IdentityControl` claim facts about the world; a review records the analyst's work. |
| A finding per record (a node for each record and its finding) | Exact, but heavy: dismissing 70 sign-ins would add 70 nodes. Two Reviews (relevant, not relevant) cover a mixed batch. |

### Validation

- `ReviewShape`: at least one `hasInput`; exactly one `hasReviewFinding`; a
  `partOfExecution` (the investigation, or the execution of one of its Steps). Violations.
- Warnings: no `performedBy`; no `endedAtTime` (a later review can't be ordered without it).
- A query, not a shape: a record whose latest Review in an investigation is *not relevant*
  but which is placed in one of that investigation's runs, attributed, or cited as evidence.
  That's a contradiction to resolve: one of the two judgments is wrong.

### STIX

STIX 2.1 has no equivalent. On export a Review could become a Note with `object_refs` to the
records and the finding as its content, or it could be left out. It's an analyst's working
record, not shared intelligence, so leaving it out is the default.

## In Moai

The Records tab gets two actions on a selection, "Not relevant"
and "Relevant". Each is an analyst action like the others: one Review in its own graph, undone
by deleting it. The status filter gains *Reviewed: not relevant*, hidden by default, and each
record shows its latest finding. The contradiction query joins the case's checks.

## Release

STONEWORK 0.15.0 (core: `Review`; categories 0.6.0: `ReviewFinding`, `hasReviewFinding`),
with `ReviewShape` and a section in [investigation-management.md](investigation-management.md).
