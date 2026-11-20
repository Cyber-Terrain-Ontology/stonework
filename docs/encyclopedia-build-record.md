# Design: the CTI Encyclopedia's build record

*Proposed 2026-11-16. Proposal 30 (28 is `competesWith`; 29 is held for the compound
consistency checks raised on #121). Not in the ontology yet.*

## The gap

The CTI Encyclopedia is rebuilt every night from its sources: the CVE List, NVD's CPE
dictionary and CPE match data, CISA's Known Exploited Vulnerabilities catalog, CWE, CAPEC,
ATT&CK, and NIST SP 800-53 with CTID's mapping to ATT&CK. A statement drawn from it should
be able to say what it rests on: *the Encyclopedia, with CVE data as of 2026-11-16 and
ATT&CK v20.1, says X.*

Nothing in the graph says that today. The nightly keeps what it last loaded in a state
file on the server, which a query can't reach. Only the KEV catalog is described in the
graph, as a `stonework:Feed` that its membership observations cite with `hasProvenance`.

Two dates matter, and the state file keeps only one. *Last changed* is when a source last
brought something new; *confirmed current* is the last night the nightly checked it and
found nothing newer. ATT&CK last changed on 2026-11-10, but every night since has
confirmed it current, and a citation should say so.

## What exists

- **`stonework:Feed`** ⊑ `Provenance`: "a structured data source that provides indicators,
  intelligence, or enrichment data on a regular or continuous basis", with `url` and
  `updateFrequency`.
- **Plan execution** ([plan-execution-model.md](plan-execution-model.md)): a run is a
  `Process` that is `executionOf` a `Plan`; each Step's execution is `partOfExecution` the
  run and `correspondsToStep` its Step, with `startedAtTime`, `endedAtTime`, `hasInput`
  and `performedBy`.

The nightly is a plan in exactly this sense: a fixed procedure, a step per source,
performed every night by an organization's software. So the proposal adds no class for
the run. It adds two terms and a category scheme.

## Proposal 30: the build record

**Each source is a `Feed`.** Eight in all: the existing KEV Feed, and one each for the CVE
List, the CPE dictionary, CPE match data, CWE, CAPEC, ATT&CK Enterprise, and NIST SP 800-53
with CTID's mapping.

**The nightly update is a `Plan`**, with a Step for each source and one for the
re-materialize, which rebuilds the cross-dataset links (CWE to CAPEC to ATT&CK, control to
technique). Statements that follow those links rest on the re-materialize as much as on
the sources, so it gets its own record. `planVersion` changes when the steps do.

**Each night is a run**, and **each Step's execution** records:

| Term | | Meaning |
|---|---|---|
| `hasInput` | existing | The Feed it read. |
| `startedAtTime`, `endedAtTime` | existing | When. |
| `performedBy` | existing | The organization that runs the Encyclopedia. |
| `stonework:sourceRelease` | CyberActivity → string (new) | The release the Step found: a version (`v20.1`, `5.0`), a commit, or a content hash, as the source identifies its releases. |
| `stonework:hasLoadOutcome` | CyberActivity → LoadOutcome (new, functional) | What the Step did. |

**`LoadOutcome`** scheme (in `categories.ttl`):

- *loaded*: the source had something new, and it was loaded;
- *already current*: the source had nothing newer than what was loaded before;
- *refused*: the source changed in a way the transform hasn't been checked against (a new
  schema or specification version), so the data was left as it was;
- *failed*: the Step ran and didn't finish.

A source's data is **current as of** the end of its latest Step execution whose outcome is
*loaded* or *already current*. A *refused* or *failed* Step leaves the previous date
standing, and the record says why it didn't move.

**Why a string for the release.** ATT&CK, CWE and CAPEC publish named releases that could
be entities of their own (an `IntelligenceProduct` with `hasProvenance` to its Feed). The
CVE List can't: its "release" is a git commit, made several times a day. A string covers
every source now; release entities can come later if something needs them.

**How it lines up with DCAT and PROV.** The terms are new because they say what a CTI
citation needs, but the standard vocabularies cover the same ground, and the note follows
STONEWORK's habit of saying so (as `Plan` does with `prov:Plan`):

- `sourceRelease`'s value is what DCAT 3's `dcat:version` holds: "the version indicator
  (name or identifier) of a resource". It is **not** declared a sub-property of it. The
  subject differs: `dcat:version` describes the release itself (ATT&CK v20.1 *has version*
  v20.1), while `sourceRelease` describes the Step that read it (the night's ATT&CK load
  *found* v20.1). A sub-property would say the Step has a version. So `sourceRelease` gets
  `rdfs:seeAlso dcat:version` and a scope note that says this. If release entities come
  later, each carries `dcat:version`, the Step points at it with `hasInput`, and
  `sourceRelease` becomes a shortcut that can be derived.
- A `Feed` is what DCAT calls a `dcat:Dataset` that is published again and again; the
  Feed's `url` is close to a `dcat:Distribution`'s access URL. Saying so would be an
  `rdfs:seeAlso dcat:Dataset` on `Feed`, which is already in use; this proposal leaves it
  as it is, and that can be a small change of its own.
- The run and its Step executions are PROV activities: the example types them
  `Process`, which already has `rdfs:seeAlso prov:Activity`. `hasInput` does the work of
  `prov:used` here but says nothing about PROV today; `actsOn` is the property that carries
  `rdfs:seeAlso prov:used`. Adding the same `seeAlso` to `hasInput` would be a small,
  separate change. `hasLoadOutcome` has no PROV or DCAT counterpart: PROV records that an
  activity used an entity, not whether the attempt succeeded.

**Why a scheme, not a `Deviation`.** A refused load is the plan working as designed: the
step that checks the source's version is part of the plan. A `Deviation` is a departure
from the plan, found afterwards.

**Where it lives.** In its own named graph, written after the night's health check passes,
at the same moment as the nightly's state file, so the graph never claims more than the
state does. A run that aborts writes the run and the Step that failed. About ten records a
night.

## Example

```turtle
ex:nightly-update
    a stonework:Plan ;
    skos:prefLabel "CTI Encyclopedia nightly update"@en ;
    stonework:planVersion "3" ;
    stonework:hasStep ex:step-attack , ex:step-kev , ex:step-materialize .   # and the others

ex:feed-attack
    a stonework:Feed ;
    skos:prefLabel "MITRE ATT&CK Enterprise (STIX 2.1)"@en ;
    stonework:url "https://github.com/mitre-attack/attack-stix-data"^^xsd:anyURI ;
    stonework:updateFrequency "twice a year, with minor releases between"@en .

ex:run-2026-11-16
    a stonework:Process ;
    stonework:executionOf ex:nightly-update ;
    stonework:performedBy ex:operator ;
    stonework:startedAtTime "2026-11-16T11:00:02Z"^^xsd:dateTime ;
    stonework:endedAtTime "2026-11-16T11:41:57Z"^^xsd:dateTime .

ex:run-2026-11-16-attack
    a stonework:Process ;
    stonework:partOfExecution ex:run-2026-11-16 ;
    stonework:correspondsToStep ex:step-attack ;
    stonework:hasInput ex:feed-attack ;
    stonework:sourceRelease "v20.1" ;
    stonework:hasLoadOutcome stonework:loadOutcomeAlreadyCurrent ;
    stonework:endedAtTime "2026-11-16T11:09:40Z"^^xsd:dateTime .

# CISA's site was down: the catalog keeps its date from the night before.
ex:run-2026-11-16-kev
    a stonework:Process ;
    stonework:partOfExecution ex:run-2026-11-16 ;
    stonework:correspondsToStep ex:step-kev ;
    stonework:hasInput ex:feed-cisa-kev ;
    stonework:hasLoadOutcome stonework:loadOutcomeFailed ;
    stonework:endedAtTime "2026-11-16T11:06:12Z"^^xsd:dateTime .
```

And the query a citation runs, for one Feed:

```sparql
SELECT ?release ?asOf WHERE {
  ?step stonework:hasInput ex:feed-attack ;
        stonework:hasLoadOutcome ?o ;
        stonework:endedAtTime ?asOf .
  OPTIONAL { ?step stonework:sourceRelease ?release }
  VALUES ?o { stonework:loadOutcomeLoaded stonework:loadOutcomeAlreadyCurrent }
}
ORDER BY DESC(?asOf) LIMIT 1
```

Note that the KEV step on 2026-11-16 has no `sourceRelease`: the catalog couldn't be read,
so the night can't say which release it would have found. The re-materialize's Step has
no Feed and no release; its outcome and time are what matter.

## Questions for discussion

1. **`sourceRelease`'s domain:** `CyberActivity` (any activity that read a source), or only
   the Steps of a load? Wider is simpler; narrower says more.
2. **Feed and named graph:** should a Feed say which named graph holds its data, so a
   citation can be built in one query, or does that mapping belong to whoever serves the
   graph? Named graphs aren't STONEWORK things today.
3. **The re-materialize's inputs:** list the Feeds it read (`hasInput` each), or leave it
   to be understood as reading everything loaded that night?
4. **Released or not:** should the plan, Feeds and records be part of the Encyclopedia's
   public graphs, or kept for the operator only, with citations served from them?

## Release

A minor core version: `sourceRelease` (with `rdfs:seeAlso dcat:version`), `hasLoadOutcome`,
the `LoadOutcome` scheme, shapes for the functional property, and fixtures. The Encyclopedia starts writing records with
the first nightly after the release is loaded on its server.
