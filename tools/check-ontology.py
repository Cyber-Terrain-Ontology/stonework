#!/usr/bin/env python3
"""Parse every Turtle file and enforce a few high-value OWL integrity rules."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "tools" / "rdf-toolkit.jar"
CATALOG = ROOT / "ontologies" / "catalog-v001.xml"

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
DCTERMS = "http://purl.org/dc/terms/"
STONEWORK = "https://cyberterrain.org/ns/stonework#"
STONEX = "https://cyberterrain.org/ns/stonex#"
D3FEND = "http://d3fend.mitre.org/ontologies/d3fend.owl#"
OCSF = "https://cyberterrain.org/ns/frameworks/ocsf#"
UCO = "https://ontology.unifiedcyberontology.org/uco/"

RDF_TYPE = RDF + "type"
RDF_ABOUT = "{" + RDF + "}about"
RDF_RESOURCE = "{" + RDF + "}resource"
RDF_NODE_ID = "{" + RDF + "}nodeID"
RDF_DATATYPE = "{" + RDF + "}datatype"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def expanded_name(tag: str) -> str:
    if not tag.startswith("{"):
        return tag
    namespace, local = tag[1:].split("}", 1)
    return namespace + local


def parse_file(path: Path, output: Path):
    command = [
        "java",
        "-jar",
        str(JAR),
        "-sfmt",
        "turtle",
        "-tfmt",
        "rdf-xml",
        "-dtd",
        "-s",
        str(path),
        "-t",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(detail or "rdf-toolkit could not parse the file")

    triples = []
    root = ET.parse(output).getroot()
    file_key = path.relative_to(ROOT).as_posix()
    for element in root:
        subject = element.get(RDF_ABOUT)
        if subject is None:
            node_id = element.get(RDF_NODE_ID)
            if node_id is None:
                continue
            subject = f"_:{file_key}:{node_id}"

        element_type = expanded_name(element.tag)
        if element_type != RDF + "Description":
            triples.append((subject, RDF_TYPE, ("iri", element_type)))

        for predicate_element in element:
            predicate = expanded_name(predicate_element.tag)
            resource = predicate_element.get(RDF_RESOURCE)
            if resource is not None:
                obj = ("iri", resource)
            else:
                node_id = predicate_element.get(RDF_NODE_ID)
                if node_id is not None:
                    obj = ("bnode", f"_:{file_key}:{node_id}")
                else:
                    obj = (
                        "literal",
                        predicate_element.text or "",
                        predicate_element.get(XML_LANG),
                        predicate_element.get(RDF_DATATYPE),
                    )
            triples.append((subject, predicate, obj))
    return triples


def describe(resource: str) -> str:
    return resource.replace(STONEWORK, "stonework:").replace(D3FEND, "d3f:")


def main() -> int:
    if not JAR.is_file():
        print(f"ERROR: rdf-toolkit.jar not found at {JAR}", file=sys.stderr)
        print("Run once: bash tools/download-rdf-toolkit.sh", file=sys.stderr)
        return 1

    # Tracked Turtle only. A glob of the working tree would also scan vendor
    # trees such as the unpacked Apache Jena examples under tools/.
    ttl_files = sorted(
        ROOT / relative
        for relative in subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "--", "*.ttl"],
            text=True,
        ).splitlines()
        if relative
    )
    triples = []
    sources = defaultdict(set)
    errors = []

    with tempfile.TemporaryDirectory(prefix="stonework-check-") as temp_dir:
        for index, path in enumerate(ttl_files):
            try:
                file_triples = parse_file(path, Path(temp_dir) / f"{index}.rdf")
            except (ValueError, ET.ParseError) as exc:
                errors.append(f"{path.relative_to(ROOT)}: parse failure: {exc}")
                continue
            triples.extend(file_triples)
            for subject, _, _ in file_triples:
                if not subject.startswith("_:"):
                    sources[subject].add(path.relative_to(ROOT).as_posix())

    values = defaultdict(set)
    types = defaultdict(set)
    for subject, predicate, obj in triples:
        values[(subject, predicate)].add(obj)
        if predicate == RDF_TYPE and obj[0] == "iri":
            types[subject].add(obj[1])

    try:
        catalog_root = ET.parse(CATALOG).getroot()
        catalog_names = {
            element.get("name")
            for element in catalog_root.iter()
            if expanded_name(element.tag) == "urn:oasis:names:tc:entity:xmlns:xml:cataloguri"
            and element.get("name")
        }
    except ET.ParseError as exc:
        catalog_names = set()
        errors.append(f"{CATALOG.relative_to(ROOT)}: parse failure: {exc}")

    for subject, predicate, obj in triples:
        if predicate != OWL + "imports" or obj[0] != "iri":
            continue
        imported_iri = obj[1]
        if imported_iri.startswith("https://cyberterrain.org/ns/") and imported_iri not in catalog_names:
            location = ", ".join(sorted(sources.get(subject, ())))
            errors.append(
                f"{describe(subject)} ({location}) imports {imported_iri}, which is not resolved "
                "by ontologies/catalog-v001.xml"
            )

    def list_members(head):
        members = set()
        seen = set()
        while head[0] == "bnode" and head[1] not in seen:
            seen.add(head[1])
            first = values[(head[1], RDF + "first")]
            rest = values[(head[1], RDF + "rest")]
            members.update(obj[1] for obj in first if obj[0] == "iri")
            if len(rest) != 1:
                break
            head = next(iter(rest))
        return members

    def class_expression_members(obj):
        if obj[0] == "iri":
            return {obj[1]}
        if obj[0] != "bnode":
            return set()
        members = set()
        for union_head in values[(obj[1], OWL + "unionOf")]:
            members.update(list_members(union_head))
        return members

    def endpoints(subject, predicate):
        result = set()
        for obj in values[(subject, predicate)]:
            result.update(class_expression_members(obj))
        return result

    direct_superclasses = defaultdict(set)
    direct_superproperties = defaultdict(set)
    for (subject, predicate), objects in values.items():
        if predicate == RDFS + "subClassOf":
            direct_superclasses[subject].update(obj[1] for obj in objects if obj[0] == "iri")
        elif predicate == RDFS + "subPropertyOf":
            direct_superproperties[subject].update(obj[1] for obj in objects if obj[0] == "iri")

    def ancestors(subject):
        result = {subject}
        pending = [subject]
        while pending:
            current = pending.pop()
            for superclass in direct_superclasses[current] - result:
                result.add(superclass)
                pending.append(superclass)
        return result

    def compatible(left, right):
        return any(
            right_class in ancestors(left_class) or left_class in ancestors(right_class)
            for left_class in left
            for right_class in right
        )

    object_property = OWL + "ObjectProperty"
    datatype_property = OWL + "DatatypeProperty"
    named_individual = OWL + "NamedIndividual"
    owl_class = OWL + "Class"
    owl_ontology = OWL + "Ontology"
    concept_scheme = SKOS + "ConceptScheme"

    d3fend_file = "ontologies/frameworks/d3fend.ttl"
    d3fend_ontology = "https://cyberterrain.org/ns/frameworks/d3fend"
    expected_d3fend_source = (
        "https://d3fend.mitre.org/ontologies/d3fend/1.5.0/d3fend.owl"
    )
    if d3fend_file in sources.get(d3fend_ontology, set()):
        if ("iri", expected_d3fend_source) not in values[
            (d3fend_ontology, DCTERMS + "source")
        ]:
            errors.append(
                "the D3FEND adapter must cite the version-pinned D3FEND 1.5.0 ontology "
                "with dcterms:source"
            )

    expected_d3fend_classes = {
        D3FEND + "AccessControlList": {STONEWORK + "AccessControlList"},
        D3FEND + "Agent": {STONEWORK + "Agent"},
        D3FEND + "AgentGroup": {STONEWORK + "Group"},
        D3FEND + "AnalyticTechnique": {STONEWORK + "AnalyticTechnique"},
        D3FEND + "Certificate": {STONEWORK + "Certificate"},
        D3FEND + "ComputerPlatform": {STONEWORK + "Host"},
        D3FEND + "CyberTechnique": {STONEWORK + "CyberTechnique"},
        D3FEND + "DefensiveTactic": {STONEWORK + "DefensiveTactic"},
        D3FEND + "DefensiveTechnique": {
            STONEWORK + "Countermeasure",
            STONEWORK + "DefendTechnique",
        },
        D3FEND + "DigitalArtifact": {STONEWORK + "DigitalArtifact"},
        D3FEND + "DigitalEvent": {STONEWORK + "CyberActivity"},
        D3FEND + "DigitalIdentity": {STONEWORK + "DigitalIdentity"},
        D3FEND + "Directory": {STONEWORK + "Directory"},
        D3FEND + "DomainName": {STONEWORK + "Domain", STONEWORK + "Identifier"},
        D3FEND + "Event": {STONEWORK + "Event"},
        D3FEND + "File": {STONEWORK + "File"},
        D3FEND + "Host": {STONEWORK + "Host"},
        D3FEND + "IPAddress": {STONEWORK + "IPAddress", STONEWORK + "Identifier"},
        D3FEND + "Identifier": {STONEWORK + "Identifier"},
        D3FEND + "Log": {STONEWORK + "Log"},
        D3FEND + "MACAddress": {STONEWORK + "MACAddress"},
        D3FEND + "NetworkNode": {STONEWORK + "Infrastructure"},
        D3FEND + "NetworkServiceApplicationProcess": {STONEWORK + "NetworkService"},
        D3FEND + "NetworkTraffic": {STONEWORK + "NetworkTraffic"},
        D3FEND + "OffensiveTactic": {STONEWORK + "OffensiveTactic"},
        D3FEND + "OffensiveTechnique": {STONEWORK + "AttackTechnique"},
        D3FEND + "OperationalActivityPlan": {STONEWORK + "Behavior"},
        D3FEND + "Organization": {STONEWORK + "Organization"},
        D3FEND + "Person": {STONEWORK + "Person"},
        D3FEND + "PhysicalArtifact": {STONEWORK + "PhysicalArtifact"},
        D3FEND + "Process": {STONEWORK + "RuntimeProcess"},
        D3FEND + "Procedure": {STONEWORK + "Procedure"},
        D3FEND + "Sensor": {STONEWORK + "Sensor"},
        D3FEND + "Step": {STONEWORK + "Step"},
        D3FEND + "System": {STONEWORK + "Infrastructure"},
        D3FEND + "Technique": {STONEWORK + "Technique"},
        D3FEND + "URL": {STONEWORK + "URI"},
        D3FEND + "UserAccount": {STONEWORK + "UserAccount"},
        D3FEND + "UserGroup": {STONEWORK + "UserGroup"},
        D3FEND + "Vulnerability": {STONEWORK + "Vulnerability"},
        D3FEND + "Weakness": {STONEWORK + "Weakness"},
    }
    actual_d3fend_classes = {
        subject: targets
        for subject, targets in direct_superclasses.items()
        if subject.startswith(D3FEND) and d3fend_file in sources.get(subject, set())
    }
    for subject in sorted(expected_d3fend_classes.keys() | actual_d3fend_classes.keys()):
        expected_targets = expected_d3fend_classes.get(subject, set())
        actual_targets = actual_d3fend_classes.get(subject, set())
        if actual_targets != expected_targets:
            expected_rendered = ", ".join(describe(item) for item in sorted(expected_targets))
            actual_rendered = ", ".join(describe(item) for item in sorted(actual_targets))
            errors.append(
                f"{describe(subject)} has unexpected D3FEND class mappings; expected "
                f"[{expected_rendered}], found [{actual_rendered}]"
            )

    expected_d3fend_properties = {
        D3FEND + "associated-with": {STONEWORK + "relatedTo"},
        D3FEND + "counters": {STONEWORK + "counters"},
        D3FEND + "d3fend-id": {STONEWORK + "externalId"},
        D3FEND + "definition": {SKOS + "definition"},
        D3FEND + "detects": {STONEWORK + "detects"},
        D3FEND + "enables": {STONEWORK + "techniqueOf"},
        D3FEND + "synonym": {SKOS + "altLabel"},
    }
    actual_d3fend_properties = {
        subject: targets
        for subject, targets in direct_superproperties.items()
        if subject.startswith(D3FEND) and d3fend_file in sources.get(subject, set())
    }
    for subject in sorted(expected_d3fend_properties.keys() | actual_d3fend_properties.keys()):
        expected_targets = expected_d3fend_properties.get(subject, set())
        actual_targets = actual_d3fend_properties.get(subject, set())
        if actual_targets != expected_targets:
            expected_rendered = ", ".join(describe(item) for item in sorted(expected_targets))
            actual_rendered = ", ".join(describe(item) for item in sorted(actual_targets))
            errors.append(
                f"{describe(subject)} has unexpected D3FEND property mappings; expected "
                f"[{expected_rendered}], found [{actual_rendered}]"
            )

    for subject, predicate, _ in triples:
        if (
            subject.startswith(D3FEND)
            and d3fend_file in sources.get(subject, set())
            and predicate in {OWL + "equivalentClass", OWL + "equivalentProperty"}
        ):
            errors.append(
                f"{describe(subject)} uses an OWL equivalence axiom; D3FEND mappings must be "
                "one-way"
            )

    ocsf_event = OCSF + "Event"
    ocsf_discovery_result = OCSF + "DiscoveryResult"
    ocsf_classes = {
        subject
        for subject, subject_types in types.items()
        if owl_class in subject_types and subject.startswith(OCSF)
    }
    if ocsf_classes:
        if STONEWORK + "Event" not in ancestors(ocsf_event):
            errors.append("ocsf:Event must be a subclass of stonework:Event")

        expected_ocsf_categories = {
            OCSF + "SystemActivityEvent": "1",
            OCSF + "FindingEvent": "2",
            OCSF + "IdentityAndAccessManagementEvent": "3",
            OCSF + "NetworkActivityEvent": "4",
            OCSF + "DiscoveryEvent": "5",
            OCSF + "ApplicationActivityEvent": "6",
            OCSF + "RemediationEvent": "7",
            OCSF + "UnmannedSystemsEvent": "8",
        }
        for category_class, expected_identifier in expected_ocsf_categories.items():
            identifiers = values[(category_class, DCTERMS + "identifier")]
            if identifiers != {("literal", expected_identifier, None, None)}:
                errors.append(
                    f"{category_class} must declare OCSF category identifier "
                    f"{expected_identifier!r}"
                )

        identifier_owners = defaultdict(set)
        for subject in sorted(ocsf_classes - {ocsf_event}):
            if ocsf_event not in ancestors(subject):
                errors.append(f"{subject} must descend from ocsf:Event")

            identifiers = values[(subject, DCTERMS + "identifier")]
            if subject == ocsf_discovery_result:
                if identifiers:
                    errors.append("ocsf:DiscoveryResult must not declare a concrete class ID")
            elif len(identifiers) != 1 or any(obj[0] != "literal" for obj in identifiers):
                errors.append(f"{subject} must declare exactly one literal OCSF identifier")
            else:
                identifier = next(iter(identifiers))[1]
                identifier_owners[identifier].add(subject)

            see_also = values[(subject, RDFS + "seeAlso")]
            if len(see_also) != 1 or any(obj[0] != "iri" for obj in see_also):
                errors.append(f"{subject} must declare exactly one IRI-valued rdfs:seeAlso")

        if len(identifier_owners) != 87:
            errors.append(
                "the OCSF 1.9.0 adapter must contain 87 category and concrete class IDs; "
                f"found {len(identifier_owners)}"
            )
        for identifier, owners in sorted(identifier_owners.items()):
            if len(owners) > 1:
                rendered = ", ".join(sorted(owners))
                errors.append(f"duplicate OCSF identifier {identifier!r}: {rendered}")

    uco_prefixes = (
        UCO + "action/",
        UCO + "core/",
        UCO + "identity/",
        UCO + "location/",
        UCO + "observable/",
    )
    uco_mapped_classes = {
        subject
        for subject in direct_superclasses
        if subject.startswith(uco_prefixes)
        and "ontologies/frameworks/uco.ttl" in sources.get(subject, set())
    }
    if uco_mapped_classes:
        expected_uco_mappings = {
            UCO + "action/Action": STONEWORK + "CyberActivity",
            UCO + "core/Event": STONEWORK + "Event",
            UCO + "core/Grouping": STONEWORK + "Grouping",
            UCO + "core/Relationship": STONEWORK + "QualifiedAssertion",
            UCO + "observable/File": STONEWORK + "File",
            UCO + "observable/ObservableObject": STONEWORK + "CyberEntity",
            UCO + "observable/Observation": STONEWORK + "CyberActivity",
            UCO + "observable/Process": STONEWORK + "RuntimeProcess",
            UCO + "observable/UserAccount": STONEWORK + "UserAccount",
            UCO + "observable/WindowsRegistryKey": STONEWORK + "RegistryKey",
            UCO + "observable/X509Certificate": STONEWORK + "Certificate",
        }
        for uco_class, stonework_class in expected_uco_mappings.items():
            if stonework_class not in direct_superclasses[uco_class]:
                errors.append(
                    f"{uco_class} must map directly to {describe(stonework_class)}"
                )
        if len(uco_mapped_classes) != 49:
            errors.append(
                "the UCO 1.5.0 adapter must contain 49 class mappings; "
                f"found {len(uco_mapped_classes)}"
            )
        for subject in sorted(uco_mapped_classes):
            for target in direct_superclasses[subject]:
                if not target.startswith(STONEWORK):
                    errors.append(
                        f"{subject} maps outside the STONEWORK namespace: {target}"
                    )
                elif owl_class not in types[target]:
                    errors.append(
                        f"{subject} maps to {describe(target)}, which is not an owl:Class"
                    )

    required_local_imports = {
        "https://cyberterrain.org/ns/frameworks/cwe": {
            "https://cyberterrain.org/ns/frameworks/capec",
        },
        "https://cyberterrain.org/ns/frameworks/email": {
            "https://cyberterrain.org/ns/frameworks/dns",
        },
        "https://cyberterrain.org/ns/frameworks/killchain": {
            "https://cyberterrain.org/ns/frameworks/stix",
            "https://cyberterrain.org/ns/stonework/categories#",
        },
        "https://cyberterrain.org/ns/frameworks/registry": {
            "https://cyberterrain.org/ns/frameworks/stix",
        },
        "https://cyberterrain.org/ns/frameworks/stix": {
            "https://cyberterrain.org/ns/stonework/categories#",
        },
    }

    for subject, subject_types in sorted(types.items()):
        if owl_ontology not in subject_types:
            continue

        location = ", ".join(sorted(sources.get(subject, ())))
        version_iris = {
            obj[1] for obj in values[(subject, OWL + "versionIRI")] if obj[0] == "iri"
        }
        version_infos = {
            obj[1] for obj in values[(subject, OWL + "versionInfo")] if obj[0] == "literal"
        }
        if len(version_iris) != 1:
            errors.append(
                f"{describe(subject)} ({location}) must declare exactly one IRI-valued "
                "owl:versionIRI"
            )
        if len(version_infos) != 1:
            errors.append(
                f"{describe(subject)} ({location}) must declare exactly one literal "
                "owl:versionInfo"
            )
        if len(version_iris) == 1 and len(version_infos) == 1:
            version_info = next(iter(version_infos))
            version_iri = next(iter(version_iris))
            expected_version_iri = subject.rstrip("#/") + "/" + version_info
            if version_iri != expected_version_iri:
                errors.append(
                    f"{describe(subject)} ({location}) has a version IRI that does not match "
                    f"owl:versionInfo {version_info!r}; expected {expected_version_iri}"
                )
            for catalog_iri in (subject, version_iri):
                if catalog_iri not in catalog_names:
                    errors.append(
                        f"{describe(subject)} ({location}) is not cataloged under "
                        f"{catalog_iri} in ontologies/catalog-v001.xml"
                    )

        if any(path.startswith("ontologies/frameworks/") for path in sources.get(subject, ())):
            imports = {
                obj[1] for obj in values[(subject, OWL + "imports")] if obj[0] == "iri"
            }
            if STONEWORK not in imports:
                errors.append(
                    f"{describe(subject)} ({location}) is a framework module but does not "
                    "directly import the STONEWORK core ontology"
                )
            for required_import in sorted(required_local_imports.get(subject, set()) - imports):
                errors.append(
                    f"{describe(subject)} ({location}) does not import required local dependency "
                    f"{required_import}"
                )

    for subject, subject_types in sorted(types.items()):
        location = ", ".join(sorted(sources.get(subject, ())))
        if object_property in subject_types and datatype_property in subject_types:
            errors.append(f"{describe(subject)} ({location}) is both an object and datatype property")
        if owl_class in subject_types and named_individual in subject_types:
            errors.append(f"{describe(subject)} ({location}) is both a class and named individual")

        if object_property in subject_types or datatype_property in subject_types:
            for predicate, label in ((RDFS + "domain", "domain"), (RDFS + "range", "range")):
                named = sorted(obj[1] for obj in values[(subject, predicate)] if obj[0] == "iri")
                if len(named) > 1:
                    rendered = ", ".join(describe(item) for item in named)
                    errors.append(
                        f"{describe(subject)} ({location}) has multiple named rdfs:{label} values "
                        f"({rendered}); use an owl:unionOf class expression for alternatives"
                    )

    category = STONEWORK + "Category"
    category_scheme = STONEWORK + "categoryScheme"
    stix_specification = "https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html"
    expected_scheme_sources = {
        STONEWORK + "infrastructureTypeScheme": {stix_specification},
        STONEWORK + "killChainPhaseScheme": {
            "https://www.lockheedmartin.com/en-us/capabilities/cyber/cyber-kill-chain.html"
        },
        STONEWORK + "malwareTypeScheme": {stix_specification},
        STONEWORK + "markingScheme": {"https://www.first.org/tlp/"},
        STONEWORK + "motivationScheme": {stix_specification},
        STONEWORK + "resourceLevelScheme": {stix_specification},
        STONEWORK + "sophisticationLevelScheme": {stix_specification},
        STONEWORK + "threatActorRoleScheme": {stix_specification},
        STONEWORK + "threatActorTypeScheme": {stix_specification},
    }

    def require_english_vocabulary_annotations(subject):
        location = ", ".join(sorted(sources.get(subject, ())))
        for predicate, field_name in (
            (SKOS + "prefLabel", "skos:prefLabel"),
            (SKOS + "definition", "skos:definition"),
        ):
            english_values = [
                obj
                for obj in values[(subject, predicate)]
                if obj[0] == "literal" and (obj[2] or "").casefold() == "en"
            ]
            if len(english_values) != 1:
                errors.append(
                    f"{describe(subject)} ({location}) must declare exactly one English "
                    f"{field_name}"
                )

    def class_schemes(subject):
        schemes = set()
        for superclass in values[(subject, RDFS + "subClassOf")]:
            if superclass[0] != "bnode":
                continue
            restriction = superclass[1]
            if ("iri", SKOS + "inScheme") not in values[(restriction, OWL + "onProperty")]:
                continue
            schemes.update(
                obj[1]
                for obj in values[(restriction, OWL + "hasValue")]
                if obj[0] == "iri"
            )
        return schemes

    for subject, subject_types in sorted(types.items()):
        if concept_scheme not in subject_types or not subject.startswith(STONEWORK):
            continue
        require_english_vocabulary_annotations(subject)

        declared_source_values = values[(subject, DCTERMS + "source")]
        declared_sources = {obj[1] for obj in declared_source_values if obj[0] == "iri"}
        if len(declared_sources) != len(declared_source_values):
            errors.append(f"{describe(subject)} must use IRI-valued dcterms:source links")
        missing_sources = expected_scheme_sources.get(subject, set()) - declared_sources
        if missing_sources:
            rendered = ", ".join(sorted(missing_sources))
            errors.append(
                f"{describe(subject)} is missing its authoritative dcterms:source: {rendered}"
            )

        if subject == category_scheme:
            continue
        if ("iri", category_scheme) not in values[(subject, DCTERMS + "isPartOf")]:
            errors.append(
                f"{describe(subject)} must declare dcterms:isPartOf stonework:categoryScheme"
            )

    for subject, subject_types in sorted(types.items()):
        if owl_class not in subject_types or not subject.startswith(STONEWORK):
            continue
        if subject == category or category not in ancestors(subject):
            continue

        require_english_vocabulary_annotations(subject)

        schemes = class_schemes(subject) - {category_scheme}

        if not schemes:
            location = ", ".join(sorted(sources.get(subject, ())))
            errors.append(
                f"{describe(subject)} ({location}) is a Category subclass but has no "
                "vocabulary-specific skos:inScheme restriction"
            )
            continue

        for scheme in schemes:
            if concept_scheme not in types[scheme]:
                errors.append(
                    f"{describe(subject)} references {describe(scheme)} as its concept scheme, "
                    "but that resource is not a skos:ConceptScheme"
                )

    scheme_notation_owners = defaultdict(set)

    for subject, subject_types in sorted(types.items()):
        if named_individual not in subject_types:
            continue
        # Compatibility aliases point at the canonical vocabulary individual;
        # require materialized membership on the canonical resource instead.
        if values[(subject, OWL + "sameAs")]:
            continue

        required_schemes = set()
        for subject_type in subject_types - {named_individual}:
            if category not in ancestors(subject_type):
                continue
            for ancestor in ancestors(subject_type):
                required_schemes.update(class_schemes(ancestor))

        if required_schemes:
            require_english_vocabulary_annotations(subject)

        materialized_schemes = {
            obj[1] for obj in values[(subject, SKOS + "inScheme")] if obj[0] == "iri"
        }
        if required_schemes and SKOS + "Concept" not in subject_types:
            location = ", ".join(sorted(sources.get(subject, ())))
            errors.append(
                f"{describe(subject)} ({location}) must explicitly materialize rdf:type "
                "skos:Concept"
            )
        specific_schemes = required_schemes - {category_scheme}
        notation_values = values[(subject, SKOS + "notation")]
        notations = [obj for obj in notation_values if obj[0] == "literal"]
        if specific_schemes and (len(notation_values) != 1 or len(notations) != 1):
            location = ", ".join(sorted(sources.get(subject, ())))
            errors.append(
                f"{describe(subject)} ({location}) must declare exactly one literal "
                "skos:notation"
            )
        elif specific_schemes:
            notation = notations[0]
            if notation[2] is not None:
                location = ", ".join(sorted(sources.get(subject, ())))
                errors.append(
                    f"{describe(subject)} ({location}) has a language-tagged skos:notation; "
                    "notations must be language-neutral"
                )
            for scheme in specific_schemes:
                scheme_notation_owners[(scheme, notation[1].casefold())].add(subject)
        missing_schemes = required_schemes - materialized_schemes
        if missing_schemes:
            rendered = ", ".join(describe(scheme) for scheme in sorted(missing_schemes))
            location = ", ".join(sorted(sources.get(subject, ())))
            errors.append(
                f"{describe(subject)} ({location}) must explicitly materialize skos:inScheme "
                f"for {rendered}"
            )

    for (scheme, notation), owners in sorted(scheme_notation_owners.items()):
        if len(owners) < 2:
            continue
        rendered = ", ".join(describe(owner) for owner in sorted(owners))
        errors.append(
            f"duplicate skos:notation {notation!r} in {describe(scheme)}: {rendered}"
        )

    for subject in sorted(sources):
        definitions = values[(subject, SKOS + "definition")]
        lexical_definitions = {obj[1:] for obj in definitions if obj[0] == "literal"}
        if subject.startswith(STONEWORK) and len(lexical_definitions) > 1:
            location = ", ".join(sorted(sources[subject]))
            errors.append(f"{describe(subject)} ({location}) has conflicting skos:definition values")

        deprecated = any(
            obj[0] == "literal" and obj[1].casefold() == "true"
            for obj in values[(subject, OWL + "deprecated")]
        )
        if deprecated and values[(subject, OWL + "sameAs")]:
            errors.append(
                f"{describe(subject)} is deprecated and declares owl:sameAs; use a replacement "
                "link so deprecation is not inferred onto the canonical resource"
            )

    malware_type = STONEWORK + "MalwareType"
    for subject, subject_types in sorted(types.items()):
        if malware_type not in subject_types:
            continue
        for notation in values[(subject, SKOS + "notation")]:
            if notation[0] != "literal":
                continue
            stonex_value = STONEX + "_" + notation[1]
            if ("iri", subject) not in values[(stonex_value, OWL + "sameAs")]:
                errors.append(
                    f"{describe(subject)} has STIX notation {notation[1]!r} but "
                    f"{stonex_value} does not map to it with owl:sameAs"
                )

    checked_inverses = set()
    for subject, predicate, obj in triples:
        if predicate != OWL + "inverseOf" or obj[0] != "iri":
            continue
        inverse = obj[1]
        pair = tuple(sorted((subject, inverse)))
        if pair in checked_inverses:
            continue
        checked_inverses.add(pair)
        comparisons = (
            (endpoints(subject, RDFS + "domain"), endpoints(inverse, RDFS + "range"), "domain/range"),
            (endpoints(subject, RDFS + "range"), endpoints(inverse, RDFS + "domain"), "range/domain"),
        )
        for left, right, endpoint_names in comparisons:
            if left and right and not compatible(left, right):
                errors.append(
                    f"{describe(subject)} and {describe(inverse)} declare owl:inverseOf but have "
                    f"incompatible {endpoint_names} classes"
                )

    label_owners = defaultdict(set)
    for subject, subject_types in types.items():
        if named_individual not in subject_types:
            continue
        domain_types = subject_types - {named_individual, SKOS + "Concept"}
        for label in values[(subject, SKOS + "prefLabel")]:
            if label[0] != "literal":
                continue
            for domain_type in domain_types:
                label_owners[(domain_type, label[1].casefold())].add(subject)

    same_as = defaultdict(set)
    for subject, predicate, obj in triples:
        if predicate == OWL + "sameAs" and obj[0] == "iri":
            same_as[subject].add(obj[1])
            same_as[obj[1]].add(subject)

    for (domain_type, label), owners in sorted(label_owners.items()):
        if len(owners) < 2:
            continue
        if all(other in same_as[owner] for owner in owners for other in owners if other != owner):
            continue
        rendered = ", ".join(describe(owner) for owner in sorted(owners))
        errors.append(
            f'duplicate skos:prefLabel "{label}" for {describe(domain_type)} individuals: {rendered}'
        )

    if errors:
        print("Ontology integrity check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Ontology integrity check passed ({len(ttl_files)} Turtle files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
