# Design: alerts, subscriptions and watchlists

*Proposed 2026-11-07. Proposals 24 to 27 in
[bec-worked-example.md](bec-worked-example.md#gaps-as-proposals). Not in the ontology yet.*

## The gap

A small security operations center (SOC) subscribes to indicators of compromise from a
TAXII server or its threat intelligence platform. New indicators arrive every day and old
ones expire. The SOC loads the current ones into its firewall's watchlist, and when the
firewall sees traffic to or from one of them, an alert goes to an analyst, who triages it
and, if it's real, blocks the address and checks the internal host.

That loop is a detection plan and a control plan, and STONEWORK can already describe both.
What it can't describe are the things the loop runs on:

- **The alert.** The word every SOC uses has no STONEWORK term. `stonework:Event`'s scope note
  lists "alert" among the pre-triage occurrences, beside a raw log entry and a sensor
  observation, so the parts that make an alert an alert have nowhere to go: the rule that
  fired, its severity, and what triage decided.
- **The subscription.** `stonework:Feed` and `stonework:Publication` say where intelligence
  came from (they are `Provenance`). Nothing says that an organization was *receiving* a
  source, from when to when, by what channel.
- **The watchlist.** A firewall's block list or a SIEM's watchlist is one rule whose contents
  change daily. STONEWORK has the rule (`DetectionRule`) and the indicators, but not which
  indicators the rule held on which dates.
- **Arrival.** When an indicator reached the organization, as opposed to when it was
  published. The difference between the two is where the loop is slow.

The questions a SOC lead, a customer or an auditor asks are about the loop: did the new
indicators reach the watchlist, and how fast? Did each alert get triaged, by the right
person? Were expired indicators removed? Without these four, the answers depend on reading
tool logs by hand.

## Proposal 24: Alert

**`stonework:Alert`** ⊑ `stonework:SecurityObservation`: *a Sensor's record that what it
observed matched a DetectionRule, raised for a person's attention.*

A SecurityObservation is already "a time-bounded record produced by a security sensor or
automated tool capturing one or more cyber observables", so an Alert inherits the sensor
(`madeBySensor`), the time window and the observables. What it adds:

| Term | | Meaning |
|---|---|---|
| `stonework:triggeredBy` | Alert → DetectionRule | The rule that fired. A correlated alert names the correlation rule. |
| `stonework:matchedIndicator` | Alert → Indicator | For an indicator-matching rule, the indicator that matched. |
| `stonework:severity` | existing (string) | Widened to Alert. Kept a string, since tools score severity differently. |
| `stonework:hasAlertDisposition` | Alert → AlertDisposition (functional; in `categories.ttl`) | What triage decided. Absent until triaged. |
| `stonework:escalatedTo` | Alert → Incident | The incident it became part of. |

**`AlertDisposition`** scheme: *true positive* (the activity is malicious), *benign* (the rule
matched correctly, but the activity is expected: a scanner, an admin), *false positive* (the
rule matched in error), *duplicate* (another alert covers it).

**How it differs from its neighbours:**

- an `Event` is what happened;
- a `SecurityObservation` is what a sensor recorded about it;
- an `Alert` is a sensor saying "look at this";
- an `Incident` is a person, or automation, declaring it significant and adverse.

`stonework:Event`'s scope note would drop "alert" from its list.

**Triage** is a Step in a detection plan, performed by a Role, whose output Variable binds the
disposition. So "who triaged it, and when" is the run's, and the plan checks (performer,
separation of duties, skipped steps) apply to triage like any other step.

**OCSF.** OCSF 1.9 has *Detection Finding* (class 2004), with severity, status and
disposition. STONEWORK's OCSF adapter places every OCSF event under `stonework:Event`, an
activity, while an Alert here is a record (a `CyberEntity`). Making `ocsf:DetectionFinding`
a subclass of `stonework:Alert` would put one class on both sides of the top-level split,
so the proposal aligns them with `skos:closeMatch` instead. The alternative, an Alert as an
Event, follows OCSF but loses what makes an alert persist: it is triaged, updated, escalated
and closed, which is what records do.

## Proposal 25: Subscription

**`stonework:Subscription`** ⊑ `stonework:QualifiedAssertion`: *a qualified record that an
organization received intelligence from a source outside itself, during an interval.* It
follows `stonework:IdentityControl`: a relationship with a time span and evidence, kept as a
record.

| Term | | Meaning |
|---|---|---|
| `stonework:subscriber` | Subscription → Agent (functional) | Usually the Organization. |
| `stonework:subscribedSource` | Subscription → Provenance or Sensor (functional) | A `Feed` (an ISAC's TAXII collection), a `Publication` series (a vendor's research blog), or a provider's `Sensor` (a managed detection service). |
| `validFrom`, `validUntil` | existing | When it started and ended. |
| `stonework:deliveryChannel` | string | TAXII 2.1, RSS, email, API, syslog. |
| `stonework:deliveryFormat` | string | STIX 2.1, free text, JSON. |

The three kinds of source differ in what arrives (reports, indicators, alerts), but the
arrangement is the same.

**An organization's own appliance is not a subscription.** Its alerts are first-party: the
organization's Sensor, watching the organization's environment, linked by `madeBySensor`. A
managed service watching on the organization's behalf is a subscription. The test is whose
sensor it is.

## Proposal 26: Watchlists, and detection capability

Two different things go by "watchlist".

**Detection capability** (what the organization can detect at all) needs no new terms. It is
the organization's Sensors, the DetectionRules each one `usesRule`, and what each rule
`detects`. The proposal is a section in the docs with the query: "which ATT&CK techniques can
we detect, and with which sensors?"

**A watchlist** is one indicator-matching DetectionRule (a firewall's dynamic block list, a
SIEM watchlist) whose contents change. It needs one property:

- **`stonework:includesIndicator`** (DetectionRule → Indicator): the rule matches this
  indicator.

Used directly, it says what the rule holds now. When the dates matter, the same relationship
is a QualifiedAssertion through the generic properties (`assertionSubject` the rule,
`assertionRelationType` `includesIndicator`, `assertionObject` the indicator) with
`validFrom` and `validUntil`. That answers "since when has this indicator been in the
watchlist?" and "was it removed when it expired?" directly, which a daily snapshot of the
whole list answers only by comparing snapshots.

## Proposal 27: When intelligence arrived

**`stonework:receivedAt`** (IntelligenceProduct → `xsd:dateTime`): when the organization
received it, through a subscription or otherwise.

It is distinct from when the product was created or published (`stonework:publishedDate`).
The gap between published and received measures the feed; the gap between received and
`includesIndicator`'s `validFrom` measures the SOC. A delivery record of its own (which
bundle, which poll) can come later if a case needs it.

## Example

```turtle
ex:sub-isac
    a stonework:Subscription ;
    stonework:subscriber ex:org ;
    stonework:subscribedSource ex:feed-isac-indicators ;
    stonework:deliveryChannel "TAXII 2.1" ;
    stonework:deliveryFormat "STIX 2.1" ;
    stonework:validFrom "2026-10-01T00:00:00Z"^^xsd:dateTime .

ex:ind-198-51-100-23
    a stonework:Indicator ;
    stonework:hasProvenance ex:feed-isac-indicators ;
    stonework:receivedAt "2026-10-08T06:00:00Z"^^xsd:dateTime .

ex:watch-198-51-100-23
    a stonework:QualifiedAssertion ;
    stonework:assertionSubject ex:fw-blocklist ;
    stonework:assertionRelationType stonework:includesIndicator ;
    stonework:assertionObject ex:ind-198-51-100-23 ;
    stonework:validFrom "2026-10-11T02:00:00Z"^^xsd:dateTime .   # three days after it arrived

ex:alert-1012-0412
    a stonework:Alert ;
    stonework:madeBySensor ex:fw-edge ;
    stonework:triggeredBy ex:fw-blocklist ;
    stonework:matchedIndicator ex:ind-198-51-100-23 ;
    stonework:severity "high" ;
    stonework:hasAlertDisposition stonework:alertDispositionTruePositive ;
    stonework:escalatedTo ex:incident-1012 .
```

## Questions for discussion

1. **OCSF:** `skos:closeMatch` between `ocsf:DetectionFinding` and `stonework:Alert`, or should
   Alert be an Event after all?
2. **`triggeredBy`:** functional (one rule per alert), or several, for alerts that tools merge?
3. **Severity:** keep the string, or a category scheme now?
4. **Disposition values:** are the four enough? OCSF separates a finding's status (new, in
   progress, resolved) from its verdict; STONEWORK's runs already say when triage happened.
5. **`escalatedTo`:** or an existing property for an incident's parts?

## Release

A minor core version with categories (the `AlertDisposition` scheme), with shapes for the
new functional properties, fixtures, and a worked example: a week of a SOC's firewall alerts
against a CISA advisory's indicators, with one indicator loaded late and one kept past its
expiry.
