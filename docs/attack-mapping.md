# MITRE ATT&CK → STONEWORK mapping

*Draft for review, 2026-10-12; revised 2026-10-13 after review. Companion to `ontologies/frameworks/attack.ttl`.*

## Why

The CTI Encyclopedia's users should need only STONEWORK, STONES and SKOS. A STONEWORK
class is the abstraction of the framework classes beneath it: `stonework:AttackPattern`
generalizes both `capec:AttackPattern` and ATT&CK's techniques. The essence lives in
STONEWORK and the specifics in the framework ontology, which makes STONEWORK the
integration point, and a transform the step that maps a framework concept onto it.

ATT&CK had no framework ontology because MITRE publishes it as STIX 2.1 JSON, and STIX
offered only its generic object types. But MITRE does publish ATT&CK's own model, the
**[ATT&CK Data Model Specification](https://mitre-attack.github.io/attack-data-model/schemas/)**
(v3.3.0, the spec version of the bundle we ingest). `attack.ttl` renders that spec in OWL:
MITRE's concepts, each placed under a STONEWORK parent, and the properties only ATT&CK has.
The STONEWORK parents are the only decisions that are ours.

## Three layers per ATT&CK object

| Layer | Example for T1059 | For whom |
|---|---|---|
| STONES (faithful STIX) | `stones:AttackPattern`, `stones:name`, external references | STIX users; unchanged |
| `attack:` (ATT&CK's own model) | `attack:Technique`, `attack:attackId "T1059"`, `attack:tactic` | ATT&CK specialists |
| STONEWORK (the essence) | `stonework:AttackTechnique`, `stonework:attackId "T1059"`, `skos:prefLabel` | Every Encyclopedia user |

Instance IRIs stay as now, built from MITRE's STIX IDs (`ctienc:attack-pattern--7385dfaf-…`),
which are stable across ATT&CK releases.

## Classes

| ATT&CK concept (STIX type) | In bundle | `attack:` class | STONEWORK parent | Status |
|---|---|---|---|---|
| Technique (`attack-pattern`, not sub) | 381 | `attack:Technique` | `stonework:AttackTechnique` | Settled: STONEWORK's scope note already names `attack:Technique` |
| Sub-technique (`attack-pattern`, `x_mitre_is_subtechnique`) | 477 | `attack:SubTechnique` | `attack:Technique` | Settled |
| Tactic (`x-mitre-tactic`) | 15 | `attack:Tactic` | `stonework:Tactic` | Settled |
| Group (`intrusion-set`) | 191 | `attack:Group` | `stonework:ThreatActorGroup` | Decided: the actor. MITRE publishes groups as STIX intrusion-sets, conflating the actor with its activity. The intrusion-set stays a `CyberActivityCluster` (activity, a BFO process); the interpretation step mints a separate `attack:Group` (actor, a BFO material entity) that the cluster is `stonework:attributedTo`. One individual can't be both: `frameworks/bfo.ttl` (0.2.0) now asserts `CyberActivity` and `Agent` disjoint, following BFO |
| Software: malware (`malware`) | 733 | `attack:Malware` ⊑ `attack:Software` | `stonework:MalwareFamily` | Settled (`attack:Software` ⊑ `stonework:Product`) |
| Software: tool (`tool`) | 95 | `attack:Tool` ⊑ `attack:Software` | `stonework:Tool` | Settled |
| Campaign (`campaign`) | 56 | `attack:Campaign` | `stonework:Campaign` | Settled |
| Mitigation (`course-of-action`) | 44 current + 224 deprecated | `attack:Mitigation` | `stonework:Mitigation` | Decided. Their STIX typing also makes them `stonework:CourseOfAction`, a kind of `Mitigation`, so consistent |
| Detection Strategy (`x-mitre-detection-strategy`) | 699 | `attack:DetectionStrategy` | `stonework:DefendTechnique` | Decided in review, following D3FEND, which models detection as defensive techniques. Not `DetectionPlan`: that is Step-decomposed, and a strategy has no steps. It contains its analytics via `stonework:hasTechnique` |
| Analytic (`x-mitre-analytic`) | 1,758 | `attack:Analytic` | `stonework:DefendTechnique` | Decided in review, as above. Not `AnalyticTechnique`, which covers analytic methods (ACH, clustering), not detection logic. Users query `stonework:AttackTechnique` for T-numbers |
| Data Component (`x-mitre-data-component`) | 109 | `attack:DataComponent` | none yet | **OPEN, likely anchor found**: a *kind* of event ("Process Creation"), not an event, so no parent class. `frameworks/ocsf.ttl` already models kinds of telemetry as classes under `stonework:Event`, so match each Data Component to its OCSF class (Process Creation → `ocsf:ProcessActivity`). `stonework:Log` is an actual record |
| Data Source (`x-mitre-data-source`) | 38 | `attack:DataSource` (deprecated) | none | Superseded in spec 3.3.0; keep for history |
| Asset (`x-mitre-asset`) | 0 (ICS only) | `attack:Asset` | none yet | **OPEN, a STONEWORK gap**; only matters when ICS is loaded |
| Matrix, Collection | 1, 1 | `attack:Matrix`, `attack:Collection` | none | Release metadata, not domain concepts |

Today's skotarch typing already puts detection strategies and analytics under
`stonework:DefendTechnique`, which this keeps; what changes is the `attack:` class and the
strategy → analytic link. Data sources and components are typed `stonework:Threat` today,
which is wrong and goes away.

## Relationships

ATT&CK relationships that mean the same as a STONEWORK property get **no `attack:` property**:
the interpretation step writes the STONEWORK property directly. An `attack:` copy would add
nothing a user needs, would have to be materialized twice (the gateway queries without
inference), and its ATT&CK-only domain and range would retype other data. Example: with
domain Group, `attack:uses` would have made every intrusion set an `attack:Group`, because
MITRE puts the `uses` links on the intrusion set. `attack:` keeps only the relationships that
narrow a STONEWORK property with several meanings, or that STONEWORK lacks.

| ATT&CK relationship (spec) | In bundle | Written as |
|---|---|---|
| `uses`: Group/Software/Campaign → Technique; Group/Campaign → Software | 18,457 | `stonework:uses` |
| `mitigates`: Mitigation → Technique | 1,448 | `stonework:mitigatesAttackPattern` |
| `detects`: Detection Strategy → Technique | 697 | `stonework:detects` |
| `attributed-to`: Campaign → Group; also intrusion-set → its minted Group | 26 (+191) | `stonework:attributedTo` |
| `targets`: Technique → Asset (ICS) | 0 | `stonework:targets` |
| `revoked-by` | 157 | `stonework:revokedBy` |
| `subtechnique-of`: Sub-technique → Technique | 477 | `attack:subtechniqueOf` ⊑ `stonework:techniqueOf` (inverse of `hasTechnique`: "a Technique to a more specific Technique it contains") |
| Technique → Tactic (`kill_chain_phases`) | per technique | `attack:tactic` ⊑ `stonework:techniqueOf` (inverse of `hasTechnique`: "a Tactic to a Technique that serves its goal") |
| Detection Strategy → Analytic (`x_mitre_analytic_refs`) | per strategy | `attack:analytic` ⊑ `stonework:hasTechnique` ("a Technique to a more specific Technique it contains") |
| Analytic → Data Component (`x_mitre_log_source_references`) | per analytic | `attack:dataComponent`; no STONEWORK parent yet (follows the Data Component decision) |

Where an `attack:` property specializes a STONEWORK one, the interpretation step writes both.

The 18,457 `uses` relationships each carry a description: ATT&CK's *procedure examples*.
STONEWORK's `Procedure` layer (see `technique-modeling.md`) could hold them later; not in
this draft.

## Identifiers and attributes

| ATT&CK field | `attack:` property | STONEWORK | Note |
|---|---|---|---|
| ATT&CK ID (`external_id` of the mitre-attack reference) | `attack:attackId` | ⊑ `stonework:attackId` (new in 0.10.0, ⊑ `skos:notation`) and `stonework:externalId` | Canonical and source forms are the same. Not unique across types: deprecated mitigations reuse T-numbers. Not `relatedTechniqueIdentifier`, which carries a technique ID on another framework's entity as a join key |
| Page URL (`https://attack.mitre.org/techniques/T1059/`) | `attack:url` | — | The de facto public identifier; a web page, so a value, not `owl:sameAs` |
| `name` | (STONES `stones:name`) | `skos:prefLabel` | Every object gets both |
| `description` | (STONES) | `stonework:description` | Already materialized |
| `x_mitre_shortname` (tactics) | `attack:shortname` | — | |
| `x_mitre_domains` | `attack:domain` | — | Replaces the undeclared `stonework:domain` |
| `x_mitre_platforms` | `attack:platform` | — | Replaces the undeclared `stonework:platform` |
| `aliases`, `x_mitre_aliases` | `attack:alias` | — | STONEWORK has no alias property; worth adding? |
| `x_mitre_version`, `x_mitre_attack_spec_version` | `attack:version`, `attack:specVersion` | — | Replace the undeclared `stonework:mitreVersion` |
| `x_mitre_deprecated` | `attack:deprecated` | — | Replaces the undeclared `stonework:deprecated` |
| `x_mitre_is_subtechnique` | (class `attack:SubTechnique`) | — | Replaces the undeclared `stonework:isSubtechnique` |

**Found while drafting:** the STIX transform writes `stonework:platform`, `isSubtechnique`,
`domain`, `deprecated` and `mitreVersion`, none of which STONEWORK declares. They are
ATT&CK-specific and move to `attack:`.

## STONEWORK changes this needs

1. Done in 0.10.0: **`stonework:attackId`** (no domain: every ATT&CK object has an ID) and
   **`stonework:capecId`** ("CAPEC-66"). Both, and `stonework:cweId`, specialize `skos:notation`. `capec:capecId` and `cwe:cweId`, the source-native
   numbers, now specialize `stonework:externalId` (CAPEC and CWE modules 0.3.0).
2. None for the strategy → analytic link: with both under `DefendTechnique`, the existing
   `hasTechnique` fits. (The first draft added `stonework:appliesTechnique`; dropped in review.)
3. Data Components: likely matched to OCSF event classes rather than a new concept (see above). A general asset class (ICS) is still open.
4. Possibly `stonework:alias`.

## Not decided here

- **Ingest:** the plan is an ATT&CK interpretation step in skotarch (SPARQL rules over the
  STONES data) that writes the `attack:` and STONEWORK terms, keeping the STIX transform
  generic for customers' own STIX bundles. Separate change, after this mapping is agreed.
- **D3FEND:** linking each technique to D3FEND's class for it (`d3f:T1059`) would make
  D3FEND's countermeasures reachable. Needs D3FEND loaded; later.
- **Mobile and ICS ATT&CK:** the ontology allows for them; only Enterprise is loaded today.
