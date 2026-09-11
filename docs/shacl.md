# SHACL in STONEWORK

## Shapes are a validation profile, not the interoperability contract

The interoperability contract is the **ontology**: the classes, properties,
domains, ranges, and controlled vocabularies in `ontologies/stonework.ttl` and
`ontologies/categories.ttl`. Two systems interoperate when they agree on what
`stonework:SecurityActuation` means and which property links it to its target.

The shape graphs in `ontologies/shapes/` are something narrower. They describe
what a **well-formed record looks like for a particular consumer**. A record can
be a perfectly legitimate instance of the ontology and still fail a shape,
because the shape encodes an expectation the ontology deliberately does not
impose.

This distinction matters because STONEWORK is an OWL ontology under the open
world assumption. The absence of `stonework:actsOn` does not mean an actuation
had no target; it means nobody has said what the target is. SHACL is a
closed-world checker bolted onto an open-world model, and treating every SHACL
finding as a contract breach makes the ontology unusable for the partial,
in-flight, progressively enriched data that real ingest pipelines produce.

Practical consequences:

- **Shapes are versioned separately from the contract.** Tightening a shape is
  not a breaking ontology change, and loosening one does not relax the
  ontology's semantics.
- **A producer is conformant when it uses the vocabulary correctly**, not when
  it satisfies every shipped shape.
- **A consumer picks the profile it needs.** Nobody has to satisfy all of them.

## Profiles

The engine accepts one shape graph per run, so `tools/check-shacl.py` composes
profiles by unioning shape files. A profile is a named list of shape graphs.

| Profile | Shape graphs | Use |
| --- | --- | --- |
| `core` | `stonework-shapes.ttl` | Value-domain well-formedness that holds for any STONEWORK record, regardless of source. |
| `financial` | core + `frameworks/financial-shapes.ttl` | Adds the financial adapter contract. |
| `strict` | core + `stonework-strict-shapes.ttl` | Adds the normalized-provenance demand. |
| `financial-strict` | core + financial + strict | Both overlays together. |

### What belongs in core

Constraints that are true of the data *as data*: a latitude is between -90 and
90, a CVSS base score is between 0 and 10, a port is a 16-bit integer, a
`stonework:MonetaryAmount` reifies exactly one currency and one decimal amount,
`firstSeen` is no later than `lastSeen`. These are not source-specific opinions;
a malformed latitude is malformed everywhere.

### What belongs in an adapter profile

Cardinality contracts that only make sense for a specific ingest source or
framework. `ontologies/shapes/frameworks/financial-shapes.ttl` holds the
currency-exchange and normalized-valuation contracts: a consumer that never
ingests financial records should not be asked to satisfy them, and a partially
mapped exchange record should not fail a pipeline that does not care about
exchanges.

New adapters go in `ontologies/shapes/frameworks/`, get a profile entry in
`tools/check-shacl.py`, and are opt-in.

## Severity tiers

Every result carries a severity. `tools/check-shacl.py` gates the build on
`sh:Violation` only; `sh:Warning` results are reported and do not fail.

**`sh:Violation` — the data is wrong.** A value is outside its domain, has the
wrong datatype, contradicts itself, or a reified tuple is missing a field that
constitutes it. A `stonework:MonetaryAmount` without a currency is not an
incomplete monetary amount; it is not a monetary amount. Violations are the
default: a shape with no `sh:severity` reports violations.

**`sh:Warning` — the data is incomplete.** A cross-reference has not resolved
yet, a source mapping is partial, or an enrichment pass has not run. The record
is a legitimate instance of the ontology; it just is not as complete as a
consumer would like.

Current warning-tier constraints:

| Shape | Constraint | Why it is advisory |
| --- | --- | --- |
| `stonework:SecurityActuationShape` | `stonework:actsOn` `sh:minCount 1` | An actuation whose target has not been resolved yet is incomplete, not malformed. |
| `stonework:CurrencyExchangeTransactionShape` | originator and beneficiary monetary values | A partially mapped exchange record is incomplete, not malformed. |

The strict provenance overlay stays at violation severity on purpose. It is
opt-in, and a consumer that loads it is explicitly demanding normalized
provenance, so a missing `stonework:hasProvenance` is a real failure *for that
consumer*.

### Placing `sh:severity` correctly

`sh:severity` applies to **every constraint declared on the shape that carries
it**, and is read from the shape that declares the *failing* constraint. Two
consequences:

**Split mixed shapes.** A property shape carrying both `sh:class` and
`sh:minCount` cannot have one advisory and one gating. `stonework:actsOn` is
therefore declared as two sibling property shapes — the class check stays a
violation (a target that is not a `CyberEntity` is wrong data), while only the
cardinality check is demoted:

```turtle
	sh:property
		[
			sh:class stonework:CyberEntity ;
			sh:path stonework:actsOn ;
		] ,
		[
			sh:minCount "1"^^xsd:integer ;
			sh:path stonework:actsOn ;
			sh:severity sh:Warning ;
		] ,
```

**Put severity where the constraint is declared.** When a constraint is nested
inside `sh:or`, the result is reported against the `sh:or` on the enclosing node
shape, so severity must be set on the node shape. Setting it on the inner
property shape has no effect on the reported result.

```turtle
stonework:CurrencyExchangeTransactionShape
	a sh:NodeShape ;
	sh:or ( ... ) ;
	sh:severity sh:Warning ;   # on the node shape, not inside the sh:or
	sh:targetClass stonework:FinancialTransaction ;
	.
```

## No `sh:closed`

STONEWORK shape graphs must never use `sh:closed`, and `tools/check-shacl.py`
fails if one appears in `ontologies/shapes/`.

A closed shape rejects any predicate the shape author did not enumerate. That
inverts the point of an extensible vocabulary: every downstream extension,
every STIX passthrough property, every experimental annotation becomes a
validation failure. Shapes constrain the properties they care about and ignore
everything else.

If you need to detect unexpected predicates, do it as a reporting pass outside
the shape graph rather than as a shipped constraint.

## The engine

`tools/check-shacl.py` shells out to [Apache Jena](https://jena.apache.org)
`shacl`, pinned in `tools/download-jena.sh` and unpacked into
`tools/apache-jena-6.2.0/` (gitignored). Jena 6 requires Java 21; rdf-toolkit
still runs on Java 11, so the combined local toolchain is Java 21.

```bash
bash tools/download-jena.sh
python3 tools/check-shacl.py
```

It replaced a hand-rolled RDF4J harness whose SHACL engine did not implement
`sh:severity`, `sh:message`, `sh:closed`, or `sh:lessThanOrEquals`. That engine
silently rewrote `sh:Warning` to `sh:Violation`, discarded authored messages in
favour of generic ones, and needed a bespoke SPARQL workaround to enforce
ordering — which is why severity tiers were not expressible before. Jena's SHACL
implementation covers the W3C Core constraints this repo uses, including
`sh:lessThanOrEquals` natively, and reports authored `sh:message` values.

Jena always exits 0 when it can produce a ValidationReport, including for
non-conforming data, so the harness canonicalizes the Turtle report to N-Triples
with `riot` and applies the severity gate itself rather than relying on the
exit code. The Python tooling stays dependency-free.
