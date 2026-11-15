# Design: alerts, subscriptions and watchlists

*Proposed 2026-11-07; revised 2026-11-15 after review (#114, #117). Proposals 24 to 27 in
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
| `stonework:raisedByRule` | Alert → DetectionRule | The rule that fired. A correlated alert names the correlation rule. Not `triggeredBy`, which already links a Plan to the Event or Incident that starts it. |
| `stonework:matchedIndicator` | Alert → Indicator | For an indicator-matching rule, the indicator that matched. |
| `stonework:hasAlertSeverity` | Alert → SeverityLevel (functional) | The level the sensor gave it, in the sensor's own scheme. See [Severity](#severity). |
| `stonework:escalatedTo` | Alert → Incident | The incident it became part of. |
| `stonework:observedEvent` | SecurityObservation → Event (optional) | The Event the observation recorded, when the graph holds one: a firewall log entry loaded through the OCSF adapter, or an email's delivery. Most alerts won't have one. |

What triage decided is not a property of the Alert: it is a dated history, below.

**What an alert is about.** Every alert is about something that happened: a connection, a
download, a login. The Alert is the record that ties the parts together, much as a chess game
ties two players and a referee where a binary link can't: the sensor that saw it
(`madeBySensor`), what it saw and when (the observables and the observation window), the rule
that matched (`raisedByRule`) and, for an indicator rule, the indicator (`matchedIndicator`).

**Not a status attached to an event.** What happened doesn't have to be stored as an Event
of its own. A SOC's appliances raise thousands of alerts a day, most of them false
positives, and a graph holding an Event for each harmless connection would mostly hold
noise. The Alert carries what the sensor saw, and that is enough to triage it. When an Event
record does exist, `observedEvent` links to it. So the Alert is a record of its own, and
triage is recorded on the Alert, not as a status on an Event.

### Disposition history

An alert's disposition changes: it waits, someone looks at it, it's found benign, later it's
reopened when a related incident turns up. One functional `hasAlertDisposition` on the Alert
would keep only the last decision. Instead each decision is a triage of its own, following
`stonework:Review`:

**`stonework:AlertTriage`** ⊑ `stonework:Process`: *an analyst's or tool's examination of an
Alert, ending in a disposition.*

| Term | | Meaning |
|---|---|---|
| `hasInput` | existing | The Alert (or Alerts) triaged. |
| `performedBy` | existing | Who decided: a person, or the tool that auto-closed it. |
| `startedAtTime`, `endedAtTime` | existing | When. A triage with a start and no end is one in progress ("under review"). |
| `stonework:hasAlertDisposition` | AlertTriage → AlertDisposition (functional; in `categories.ttl`) | What it decided. |
| `correspondsToStep`, `partOfExecution` | existing | The triage Step of the detection plan, and the run it belongs to. |

**`AlertDisposition`** scheme: *true positive* (the activity is malicious), *benign* (the rule
matched correctly, but the activity is expected: a scanner, an admin), *false positive* (the
rule matched in error), *duplicate* (another alert covers it).

An alert with no triage is untriaged. Its current disposition is the one from the triage that
ended last; earlier triages stay as the record of the work, as later Reviews supersede earlier
ones. "Escalated" is not a disposition: it is `escalatedTo`, alongside a true-positive triage.
"Downgraded" is a change of severity, which a triage can record (question 6).

Each triage is a Step execution, so who did it and when come from the run, and the plan
checks (performer, separation of duties, skipped steps) apply to triage like any other step.
A triage imported from a tool's case history also needs its source (question 7).

### Severity

Every system scores severity its own way, and every severity in STONEWORK today is a bare
string: `stonework:severity` (Event, Incident), `stonework:cvssSeverity`, and CAPEC's
`capec:typicalSeverity`. Strings can't be compared across sources, and they can't carry
labels in other languages. The proposal:

1. **One STONEWORK severity scale, an integer from 0 to 100.** 0 is no severity (CVSS "None",
   "informational"). It is the ground truth other scales map to.
2. **An outside scale's levels are individuals.** **`stonework:SeverityLevel`** ⊑ `skos:Concept`,
   one `skos:ConceptScheme` per source (an appliance vendor, CVSS, CAPEC), with `skos:prefLabel`
   in as many languages as needed.
3. **Each level maps to a band, not a point.** A vendor's "High" means somewhere in a range.
   **`stonework:SeverityMapping`** ⊑ `QualifiedAssertion`:

   | Term | | Meaning |
   |---|---|---|
   | `stonework:mapsLevel` | SeverityMapping → SeverityLevel (functional) | The source's level. |
   | `stonework:severityLowerBound`, `stonework:severityUpperBound` | integer 0–100 (functional) | The band on the STONEWORK scale. A shape checks lower ≤ upper. |
   | `stonework:mappingForVersion` | string | The product or specification version the mapping holds for. Vendors change their scales between versions. |
   | `hasProvenance` | existing | Who made the mapping. A mapping is a judgment. |

4. **Bands are per source, and not always even.** An appliance with Low / Medium / High might
   map them to 1–33, 34–66 and 67–100. CVSS, the first scheme STONEWORK ships, is its 0.0–10.0
   score times ten: None 0, Low 1–39, Medium 40–69, High 70–89, Critical 90–100. A source that
   gives a number, as CVSS does, has a point on the scale as well as a band.
5. **The record keeps what the source said.** The Alert carries the vendor's level; its place
   on the scale comes through the mapping. A wrong mapping is corrected in one place, without
   touching the data.
6. **Severity of what.** An alert's severity (how urgent the vendor thinks it is), a
   vulnerability's (technical severity) and an incident's (assessed impact) are different
   things. They share the scale so they can be compared, and each keeps its own property:
   `hasAlertSeverity` here; the vulnerability and incident properties come when the existing
   strings are replaced (question 8).

**How it differs from its neighbours:**

- an `Event` is what happened;
- a `SecurityObservation` is what a sensor recorded about it;
- an `Alert` is a sensor saying "look at this";
- an `Incident` is a person, or automation, declaring it significant and adverse.

Put shortly: an Event is something that happened, an Alert is something suspicious that
happened, and an Incident is something harmful or unauthorized that happened. For example,
a web proxy appliance fires each time a developer visits a site that once served a
malicious component, long after the lab has patched the component:

- the Event: a developer visited the site (the proxy log has it; the graph needn't);
- the Alert: the appliance told the SOC that someone visited a site with a malicious
  component, thousands of times over;
- the Incident, had there been one: the malicious code compromised a developer's device.

Each of those alerts is triaged as benign. None of them becomes an incident, and the
graph holds no Event for them.

`stonework:Event`'s scope note would drop "alert" from its list, and
`stonework:SecurityObservation`'s would change: it now calls a security observation "the raw
sensor-layer record prior to attribution or indicator matching". That stays true of a plain
SecurityObservation; an Alert is the observation that a rule matched.

**Alert and Sighting.** A `stonework:Sighting` records that a known CTI object, such as an
indicator, was seen. An Alert with `matchedIndicator` is close to that, but it is the sensor
raising the match for triage, and the match may be wrong. The Sighting is the assertion that
the indicator was seen, recorded when triage finds the alert a true positive: the triage Step
`produces` it, citing the alert. A false positive leaves an Alert and no Sighting.

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
| `stonework:subscribedSource` | Subscription → Provenance (functional) | A `Feed` (an ISAC's TAXII collection, or a managed detection service's alert stream) or a `Publication` series (a vendor's research blog). |
| `validFrom`, `validUntil` | existing | When it started and ended. |
| `stonework:deliveryChannel` | string | TAXII 2.1, RSS, email, API, syslog. |
| `stonework:deliveryFormat` | string | STIX 2.1, free text, JSON. |

The sources differ in what arrives (reports, indicators, alerts), but the arrangement is the
same. The source is always the feed or publication, never a Sensor: a provider's sensors stay
sensors, linked from the alerts they raise by `madeBySensor`.

**An organization's own appliance is not a subscription.** Its alerts are first-party: the
organization's Sensor, watching the organization's environment, linked by `madeBySensor`. A
managed service watching on the organization's behalf is a subscription to the service's
feed. Pointing a subscription at a Sensor would be valid data that erases this line, since an
agent on the organization's own laptop is a Sensor too, so the range excludes it.

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

It is distinct from the source's own timestamps, `dcterms:created` and `dcterms:modified` on
the object the feed delivered. The gap from those to `receivedAt` measures the feed; the gap
from `receivedAt` to `includesIndicator`'s `validFrom` measures the SOC. `publishedDate`
(`dcterms:issued`) is not used for either: it is the calendar day of first public disclosure,
so a same-day feed would look instant and an old public report would look like a late
delivery. A delivery record of its own (which
bundle, which poll) can come later if a case needs it.

## The window of exposure

Dated watchlist entries show when an organization could not yet detect an indicator that was
already in use. That window needs no term of its own: it is a documented query over dates
these proposals record.

- **Start:** the earliest date a source shows the indicator in use: a report's
  `publishedDate`, a sighting's first-seen time, or the date a CVE's exploitation was first
  reported.
- **End:** the watchlist entry's `validFrom` (Proposal 26), when the rule began to detect it.
- **In between, `receivedAt` (Proposal 27) splits it in two:** start to received is the
  feed's delay, received to `validFrom` the SOC's. Different problems with different owners,
  so both dates are kept.

What follows from the window uses existing terms. The search back through the logs is a run
of a detection plan, one step per log source, over the window. Anything it finds is an
Alert raised by that hunt's rule and triaged like any other. An investigation's conclusion
"we were exposed from X to Y" is a finding resting on the query and its dates. A tool can
start the search whenever an indicator reaches a watchlist with a start date in the past;
that is tooling, but the ontology records each run. A class for a named window can come later,
if analysts need to cite one on its own.

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
    dcterms:created "2026-10-07T21:40:00Z"^^xsd:dateTime ;     # the feed's object
    stonework:receivedAt "2026-10-08T06:00:00Z"^^xsd:dateTime .

ex:watch-198-51-100-23
    a stonework:QualifiedAssertion ;
    stonework:assertionSubject ex:fw-blocklist ;
    stonework:assertionRelationType "includesIndicator" ;
    stonework:assertionObject ex:ind-198-51-100-23 ;
    stonework:validFrom "2026-10-11T02:00:00Z"^^xsd:dateTime .   # three days after it arrived

ex:alert-1012-0412
    a stonework:Alert ;
    stonework:madeBySensor ex:fw-edge ;
    stonework:hasObservable ex:ip-198-51-100-23 ;     # what it saw; no Event record needed
    stonework:raisedByRule ex:fw-blocklist ;
    stonework:matchedIndicator ex:ind-198-51-100-23 ;
    stonework:hasAlertSeverity ex:fwvendor-high ;
    stonework:escalatedTo ex:incident-1012 .

# Two triages: the night shift's auto-rule closed it as benign; the morning analyst reopened it.
ex:triage-1012-0412-a
    a stonework:AlertTriage ;
    stonework:hasInput ex:alert-1012-0412 ;
    stonework:performedBy ex:soar-autoclose ;
    stonework:endedAtTime "2026-10-12T04:13:00Z"^^xsd:dateTime ;
    stonework:hasAlertDisposition stonework:alertDispositionBenign .

ex:triage-1012-0412-b
    a stonework:AlertTriage ;
    stonework:hasInput ex:alert-1012-0412 ;
    stonework:performedBy ex:analyst-kim ;
    stonework:endedAtTime "2026-10-12T08:40:00Z"^^xsd:dateTime ;     # ended last: current
    stonework:hasAlertDisposition stonework:alertDispositionTruePositive .

# The firewall vendor's "High", placed on the STONEWORK scale.
ex:fwvendor-high
    a stonework:SeverityLevel ;
    skos:inScheme ex:fwvendor-severity ;
    skos:prefLabel "High"@en , "Élevée"@fr .

ex:map-fwvendor-high
    a stonework:SeverityMapping ;
    stonework:mapsLevel ex:fwvendor-high ;
    stonework:severityLowerBound 67 ;
    stonework:severityUpperBound 100 ;
    stonework:mappingForVersion "7.4" ;
    stonework:hasProvenance ex:soc-severity-review-2026 .
```

## Questions for discussion

1. **OCSF:** `skos:closeMatch` between `ocsf:DetectionFinding` and `stonework:Alert`, or should
   Alert be an Event after all?
2. **`raisedByRule`:** functional (one rule per alert), or several, for alerts that tools merge?
3. ~~**Severity:** keep the string, or a category scheme now?~~ Settled (#114): one 0–100
   STONEWORK scale, each source's levels as individuals mapped to bands. See
   [Severity](#severity).
4. **Disposition values:** are the four enough? OCSF separates a finding's status (new, in
   progress, resolved) from its verdict. Here the status comes from the triages (none,
   one in progress, one ended), and the scheme holds only the verdict.
5. ~~**`escalatedTo`:** or an existing property for an incident's parts?~~ Settled:
   `escalatedTo` (Alert → Incident). `hasEvent`'s range is `Event`, so using it would make
   the alert an Event, which this proposal rejects.
6. **Downgrading:** a triage that changes an alert's severity. Record the analyst's level on
   the triage (`hasAlertSeverity` widened to AlertTriage), leaving the sensor's on the Alert?
7. **A triage's source:** `hasProvenance` applies to IntelligenceProducts and
   QualifiedAssertions, not activities. Widen it to AlertTriage, for triages imported from a
   SIEM's or SOAR's case history, or is the run's provenance enough?
8. **The existing strings:** replace `stonework:severity`, `cvssSeverity` and CAPEC's
   `typicalSeverity` with level properties in this release, or keep them as strings and
   replace them in a later one? Replacing them changes what the Encyclopedia's nightly
   loader writes for every CVE.
9. **`observedEvent`:** its domain is SecurityObservation, so a plain observation can name
   its Event too, not only an Alert. Is that right, and should it be functional, or can one
   observation record several Events (a sensor's summary of a burst of connections)? Ryan's
   view: several, not functional.

## Release

A minor core version with categories (the `AlertDisposition` scheme, the CVSS severity scheme
and its bands), with shapes for the new functional properties and the band bounds, fixtures,
and a worked example: a week of a SOC's firewall alerts against a CISA advisory's
indicators, with one indicator loaded late, one kept past its expiry, and one alert closed
and reopened.
