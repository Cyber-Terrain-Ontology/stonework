![STONEWORK Badge](docs/resources/images/STONEWORK-carved-emb.png)

# STONEWORK — Semantic Threat Ontology for Next-generation Extensions, Workflows, Objects, Relationships, and Knowledge

**STONEWORK is an OWL 2 extension of STONES that adds what STIX 2.1 does not define.**

[STONES](https://github.com/Cyber-Terrain-Ontology/stones) provides a faithful ontological binding of STIX 2.1. STONEWORK extends that cyber terrain to cover adversary techniques, software weaknesses, and defensive controls — drawing from MITRE ATT&CK, MITRE D3FEND, CWE, NIST SP 800-53, and CIS Critical Controls. The core remains lightweight; import-only profiles compose it with the controlled vocabularies and framework mappings needed for a particular use case. Together, STONES and STONEWORK form a composable semantic stack for AI-driven cyber threat intelligence analysis.

STONEWORK is independent work. It is not affiliated with OASIS, MITRE, NIST, or CIS.

> STONEWORK is a candidate ontology for the **Cyber Ontology Foundry**, announced at STIDS 2026.

---

## Status

**v0.6.2 — Active Development**

The namespace (`https://cyberterrain.org/ns/stonework#`) is stable and will not change. Core extension vocabulary is in place. Framework coverage (ATT&CK, D3FEND, CWE, NIST SP 800-53, CIS) is expanding. The scope of coverage will grow as the ontology matures. Feedback, issues, and contributions are welcome.

---

## What STONEWORK adds

STONEWORK extends STONES across four concrete domains:

| Domain | Sources |
|---|---|
| Adversary techniques (TTPs) | MITRE ATT&CK, MITRE D3FEND |
| Software weaknesses | CWE (Common Weakness Enumeration) |
| Defensive controls | NIST SP 800-53, CIS Critical Controls |
| Vulnerability linkage | Connects CVE → CWE → ATT&CK technique → control |

This coverage enables queries that no single standard can answer on its own. A SPARQL query can trace a CVE to the weakness it exploits, to the attack patterns that leverage that weakness, to the APT groups known to use them, and to the controls that mitigate the risk — in a single federated query.

Both NIST SP 800-53 and CIS Controls now carry real, materialized `stonework:mitigatesAttackPattern` links to ATT&CK — not just conceptual coverage. NIST's crosswalk is sourced from the Center for Threat-Informed Defense's mapping, since NIST's own catalog defines no ATT&CK relationship on its own.

---

## Quick Start — Using the Ontology

### 1. Download

Choose the smallest ontology entry point that fits the use case:

```
ontologies/stonework.ttl                         # core vocabulary only
ontologies/profiles/stonework-stix.ttl           # core + categories + STIX mapping
ontologies/profiles/stonework-full.ttl           # all bundled mappings
```

STONEWORK treats STONES and the other CTI framework ontologies (ATT&CK, CAPEC, CWE, CVE, CPE, ...) as peer reference vocabularies. The profile ontologies declare a dependable import closure without adding vocabulary of their own. External framework datasets remain separately loadable peer graphs.

### 2. Load into a triplestore

Load the selected entry point and any external source datasets, such as `stones-merged.ttl` from the STONES repo, into an OWL-compatible triplestore:
[AllegroGraph](https://allegrograph.com) · [Stardog](https://stardog.com) · [GraphDB](https://graphdb.ontotext.com) · [Apache Jena / Fuseki](https://jena.apache.org)

### 3. Verify with SPARQL

```sparql
PREFIX stonework: <https://cyberterrain.org/ns/stonework#>
PREFIX owl:       <http://www.w3.org/2002/07/owl#>
PREFIX rdfs:      <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label WHERE {
  ?class a owl:Class ;
         rdfs:label ?label .
}
ORDER BY ?label
```

### 4. Try the worked example

Load the CTI reference datasets (ATT&CK, CAPEC, CVE, CWE, NIST SP 800-53, CIS) and run the Log4Shell chain query: from a vulnerable product to a threat actor to a defensive control in a single SPARQL query. Full walkthrough at [cyberterrain.org](https://cyberterrain.org).

---

## Modeling convention: OWL classes and SKOS concepts

Use an OWL class for an intrinsic kind of thing whose instances should participate in class reasoning—for example, `stonework:Malware`, `stonework:ThreatActor`, or `stonework:Vulnerability`. Use a SKOS concept for a controlled vocabulary value that classifies or qualifies something—for example, `stonework:Ransomware`, a named individual of `stonework:MalwareType`. A ransomware sample is categorized by that concept; the concept is not an OWL subclass of Malware.

`stonework:categoryScheme` is the umbrella scheme for every STONEWORK category. Narrower schemes such as `stonework:malwareTypeScheme`, `stonework:incidentStatusScheme`, and `stonework:threatActorRoleScheme` organize individual vocabularies. Vocabulary values explicitly assert `rdf:type skos:Concept` plus both umbrella and vocabulary-specific `skos:inScheme` membership, so plain RDF and SKOS clients can discover them without reasoning. Matching OWL value restrictions on each category subclass keep extensions semantically consistent without treating a vocabulary class as a SKOS concept.

Every controlled-vocabulary class, scheme, and canonical value has exactly one English `skos:prefLabel` and `skos:definition`; additional languages may be supplied. Every value in a specific scheme also carries exactly one language-neutral `skos:notation`, unique within that scheme. Use the notation as the stable wire identifier and the preferred label for human-facing text.

Schemes derived from an external standard declare an IRI-valued `dcterms:source` on the scheme itself. The source records provenance; it does not assert that every STONEWORK extension is defined by, or exactly equivalent to, the cited standard.

```turtle
ex:sample-1
    a stonework:MalwareSample ;
    stonework:categorizedBy stonework:Ransomware .

stonework:Ransomware
    a stonework:MalwareType ;
    skos:notation "ransomware" .
```

### SOSA-inspired observation and actuation

STONEWORK distinguishes a persistent safeguard specification from the deployed mechanism and the activity that applies it. A `stonework:Countermeasure` describes the rule, control, or mitigation; a `stonework:SecurityActuator` is the deployed infrastructure capable of applying it; and a `stonework:SecurityActuation` records a particular application. This mirrors the SOSA actuator/actuation pattern without formally importing SOSA. Systems such as IPS and EDR platforms may be both sensors and actuators.

```turtle
ex:edr-agent
    a stonework:SecurityActuator ;
    stonework:implementsCountermeasure ex:isolate-host-rule .

ex:isolation-2026-08-21
    a stonework:SecurityActuation ;
    stonework:madeByActuator ex:edr-agent ;
    stonework:appliesCountermeasure ex:isolate-host-rule ;
    stonework:actsOn ex:compromised-host .
```

---

## Developer Setup

### Clone the repo

```bash
git clone https://github.com/Cyber-Terrain-Ontology/stonework.git
cd stonework
```

### Activate the pre-commit hook

Run these two commands once after cloning:

```bash
git config core.hooksPath .githooks
bash tools/download-rdf-toolkit.sh
```

The first command activates the hooks tracked in `.githooks/`. The second downloads the [edmcouncil rdf-toolkit](https://github.com/edmcouncil/rdf-toolkit) jar (~33 MB, gitignored) used to canonicalize Turtle files on every commit.

Run the ontology checks directly at any time with:

```bash
bash .githooks/format-ttl.sh --check
python3 tools/check-ontology.py
python3 tools/check-shacl.py
```

The first command verifies canonical Turtle formatting without modifying files. The second parses every Turtle file and checks high-value OWL integrity rules. The third exercises both the baseline SHACL profile in `ontologies/shapes/stonework-shapes.ttl` and the additive strict overlay in `ontologies/shapes/stonework-strict-shapes.ttl` with the repository's bundled RDF4J runtime. CI runs all three checks for every pull request.

The SHACL files are optional application-level data-quality profiles; they do not change STONEWORK's open-world OWL semantics and are not part of the core, STIX, or full-profile import closure. The baseline profile accepts externally mapped qualified assertions without normalized provenance while still validating provenance values when present. Consumers that require complete, normalized STONEWORK records can load the strict overlay alongside the baseline profile to require provenance on every `stonework:QualifiedAssertion`. `tools/check-shacl.py` explicitly registers each profile and validates only the repository's test fixtures. Existing ingest pipelines are unaffected unless they deliberately load the shapes into a SHACL-aware engine and invoke validation.

**What the hook does on each commit:**
- Canonicalizes all staged `.ttl` files via rdf-toolkit (alphabetical prefixes, tab indentation, consistent triple ordering) so diffs reflect content changes, not style noise
- Strips Protégé's injected default `:` prefix when present
- Parses every Turtle file and rejects common OWL integrity errors, including accidental domain/range intersections, incompatible inverse-property endpoints, property-kind collisions, class/individual punning, conflicting definitions, duplicate controlled-vocabulary labels, unresolved imports, inconsistent version metadata, and incomplete category-scheme declarations
- Sets `ontologies/catalog-v001.xml` read-only so Protégé cannot overwrite it

**Requirements:** Java 11+ and Python 3 on `PATH`.

### Ontology imports and versions

Import the stable ontology IRI, such as `https://cyberterrain.org/ns/frameworks/cve`. Each ontology also declares an `owl:versionIRI` for consumers that need to pin an exact vocabulary release. The local XML catalog resolves both forms. Every bundled framework module imports the STONEWORK core directly and declares any additional bundled dependency, so a module can be loaded independently as well as through a profile.

### Framework interoperability

- `ontologies/frameworks/stix.ttl` maps STONES classes and properties into STONEWORK. STIX relationship source, target, and open-vocabulary type values project through the generic qualified-assertion properties. STIX Bundle remains intentionally unmapped because it is a transport container rather than a STIX Core Object or cyber-domain assertion.
- `ontologies/frameworks/d3fend.ttl` maps compatible MITRE D3FEND 1.5.0 defensive and offensive techniques, tactics, events, artifacts, identifiers, and selected relationships into STONEWORK. It preserves D3FEND's source-native hierarchy and class/individual punning rather than asserting equivalence.
- `ontologies/frameworks/ocsf.ttl` maps the complete OCSF 1.9.0 core event taxonomy into `stonework:Event`, retaining OCSF category and class identifiers for round-tripping.
- `ontologies/frameworks/uco.ttl` maps compatible UCO 1.5.0 action, identity, location, and observable classes into STONEWORK. It remains class-only because UCO places observable values on facet nodes while STONEWORK commonly projects them directly onto domain entities.

These adapters are alignment modules rather than copies of their source standards. Load the official D3FEND ontology, OCSF schema, or UCO ontologies alongside STONEWORK when source-native constraints and attributes are required.

---

## Documentation

| Resource | URL |
|---|---|
| Website | [cyberterrain.org](https://cyberterrain.org) |
| Ontology reference (WIDOCO) | [cyberterrain.org/ns/stonework/doc](https://cyberterrain.org/ns/stonework/doc/) |
| Namespace | `https://cyberterrain.org/ns/stonework#` |
| Base ontology | [STONES](https://github.com/Cyber-Terrain-Ontology/stones) |

### Names and aliases

Use `skos:prefLabel` for an entity's preferred human-readable name and repeat `skos:altLabel` for alternative names, pseudonyms, or spellings. `skos:altLabel` is intentionally not restricted to `stonework:Agent`: threat actors, malware, campaigns, tools, products, infrastructure, and other resources may all have alternate labels. Model a persona or account with its own identifiers and activity as a `stonework:DigitalIdentity`, not as a label.

---

## Ecosystem

**STONES + STONEWORK** form a composable semantic stack for AI-driven CTI analysis:

- **STONES** — faithful OWL 2 binding of STIX 2.1
- **STONEWORK** — extends STONES with ATT&CK, D3FEND, CWE, NIST SP 800-53, and CIS *(this repository)*

Both ontologies are candidate submissions to the **Cyber Ontology Foundry**, alongside MITRE's D3FEND Framework Ontology.

---

## Adopters

*Using STONEWORK in a project or product? Open an issue or pull request to be listed here.*

---

## License

STONEWORK is released under the **MIT License** — free to use, extend, and integrate in both open-source and commercial environments. See [LICENSE](LICENSE) for full terms.
