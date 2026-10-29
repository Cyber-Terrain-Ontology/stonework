# Changelog

## 0.12.0 (core), categories 0.3.0

Vocabulary for vulnerability exploit evidence that does not fit the EPSS probability alone, without naming a catalog vendor in the identifier.

### Added

- `stonework:epssPercentile` and `stonework:metricEpssPercentile`. The percentile is the rank of an EPSS probability, not a second probability.
- `stonework:metricReportedExploited`. A source report that a vulnerability was exploited, including reports that name a threat actor, ransomware, or a botnet. Catalog membership stays `stonework:metricKevMembership`.
- `stonework:ExploitationReportKind` (`exploited`, `threat-actor`, `ransomware`, `botnet`) and `stonework:hasExploitationReportKind` on the observation. A named actor, malware, or botnet is the observation's `stonework:assertionObject`.
- `stonework:ExploitMaturity` (`poc`, `weaponized`, in that order) and `stonework:hasExploitMaturity`. One maturity per subject: the vulnerability's highest known maturity (a convenience projection), or one exploit reference's own maturity. Dated, sourced maturity is a `stonework:MetricObservation` with the new `stonework:metricExploitMaturity`.
- `stonework:AffectedStatus` (`affected`, `unaffected`, `unknown`, `fixed`, `under-investigation`) and functional `stonework:hasAffectedStatus` on `stonework:VulnerabilityAssessment`.
- SHACL: `EpssPercentileShape`, the same 0.0–1.0 bound as `epssScore`; `ExploitMaturityShape` and `ExploitationReportKindShape`, at most one value per subject. These are SHACL limits rather than `owl:FunctionalProperty`, so two sources that disagree are reported, not merged by a reasoner.

### Changed

- `stonework:VersionedProduct` is a `stonework:CyberEntity`, the same root as `stonework:Product`. A release stays disjoint from its product line.
- `stonework:metricKevMembership` and `stonework:isKnownExploited` are no longer defined as CISA-only. The catalog is the observation's `stonework:hasProvenance`.

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
