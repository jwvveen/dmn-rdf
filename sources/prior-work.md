# Prior work: DMN in RDF, OWL and SHACL

Survey of 3 November 2026, input for "DMN 1.6 in RDF". Every row was checked
against a primary source (GitHub API, the ontology file itself, the OMG
specification page, Crossref, arXiv). Limits: general web search was not
available, so work published only on vendor sites or indexed only by Google
Scholar may be missing; the Internet Archive was offline, so archived copies of
dead IRIs were not checked.

## Vocabularies

| Effort | Namespace | Resolves | Repo, licence | Last activity | Coverage | Relevance |
|---|---|---|---|---|---|---|
| DMN-O (Nicholas Car, CSIRO) | `http://promsns.org/def/dmn#` | no (connection fails) | nicholascar/dmn-ont, CC BY 4.0 | 2017-06-28 (3 commits) | DMN 1.1, partly generated from `dmn.xmi`: 40 classes (Decision, BKM, DecisionService, DecisionTable, DecisionRule, clauses, requirements, ItemDefinition). Most of its 109 properties untyped, no range; no hit-policy individuals, FEEL, DI or SHACL | The only full metamodel ontology. Same XMI-to-OWL approach; abandoned. Align with `skos:closeMatch` |
| WHO SMART Guidelines KG, layer L2-DMN | `http://smart.who.int/kg/` (`sgkg`) | 404 | WorldHealthOrganization/smart-kg, Apache-2.0 | 2026-10-06 | 6 classes (file, decision, decision table, input and output clause, rule); `invokedBy` read from `dmn:usingTask`; rules linked to citations. No hit policy, FEEL, DRD, BKM or decision service | Most recent adopter, already separate BPMN and DMN layers. Alignment target |
| CPRMV, Core Public Rule Management Vocabulary (open-regels.nl) | `https://standaarden.open-regels.nl/standards/cprmv/0.4.0#` | yes (HTML) | sgort/cprmv, EUPL-1.2 (ontology CC BY 4.0) | 2026-02-28 | Rule sets, decision models, rules, methods; extends ELI, CPSV, PROV. DMN itself is not modelled: DMN XML goes into `cprmv:definition` literals, tied to a law article (JCI/BWB) | Dutch rules as code: law-to-rule traceability. Real resources could replace the XML in a literal |
| RONL vocabulary, CPSV-AP-RONL (MinBZK, regels.overheid.nl) | `https://regels.overheid.nl/termen/` | redirects | MinBZK/regels.overheid.nl, EUPL-1.2 | 2026-07-06 | Catalogue level: a service points to a `.dmn` file (`dct:source`), with analysis method (Wetsanalyse/JAS) and implementation endpoint | Shows where Dutch government needs a DMN IRI to point to |
| Decision Ontology (W3C Decisions XG 2012) | `promsns.org/def/do` | no | nicholascar/decision-o, CC BY 4.0 | 2018 | Generic decision making, not DMN | Context only |
| DMN-to-SPARQL or SHACL translators | none | n/a | Kuladeep561/DMN-RDF-SHACL (2023), BPaaSModelling/DMN-SPARQL-Construct-Rules-Translator (2017), Stizzo/SPARQL_Generator (GPL-3.0) | 2017-2023 | Compile a table into rules over a domain graph; the DMN itself is not in RDF | Pattern only |
| AOAME (FHNW) | `http://fhnw.ch/modelingEnvironment/...` | not checked | BPaaSModelling/Ontology4ModelingEnvironment, CC0 | 2025 | Palette entries for DMN 1.1, no DMN TBox (it has one for BPMN, CMMN, ArchiMate) | Low |
| OMG About-DMN.rdf | `https://www.omg.org/spec/DMN/About-DMN` | yes | omg.org | 2026 | Specification metadata only | `dct:source` target |

Not found: a DMN ontology from Signavio, KIE/Drools, Camunda or Trisotech; a
LegalRuleML or LKIF link to DMN in RDF; FEEL in RDF; an RML mapping from DMN
XML. `https://w3id.org/dmn` is free.

## Formal work

- Calvanese, Dumas, Laurson, Maggi, Montali, Teinemaa, "Semantics and Analysis
  of DMN Decision Tables", BPM 2016 (doi:10.1007/978-3-319-45348-4_13);
  Information Systems 2018 (doi:10.1016/j.is.2018.01.010). Formal hit-policy
  semantics; algorithms for overlapping and missing rules.
- Calvanese, Montali, Dumas, Maggi, "Semantic DMN", BPMRDS 2017
  (doi:10.1007/978-3-319-61252-2_6); TPLP 2019 (doi:10.1017/S1471068418000479).
  Decision tables plus description-logic background knowledge. No tool found.

## Decision table checkers

| Tool | Repo, licence | What it checks | FEEL |
|---|---|---|---|
| dmn-check (red6) | red6/dmn-check, Apache-2.0, active | duplicate, conflicting and shadowed rules, types, enumerations, aggregations, requirement graph | own checker for a subset of unary tests |
| Apache KIE DMN DT analysis | apache/incubator-kie-drools (`DMNDTAnalyser`), Apache-2.0, active | gaps, overlaps, masked, misleading and subsumed rules, MC/DC, hit-policy advice | Drools FEEL; static analysis stops at symbols and named references |
| Laurson and Maggi | ulaurson/dmn-js, 2016 | overlap, missing rules, merging (BPM 2016 algorithms) | numeric intervals, enumerations |
| dmnlint (bpmn.io) | bpmn-io/dmnlint, MIT | two structural rules | no |

OMG publishes no FEEL grammar file; reusable grammars are Drools
`FEEL_1_1.g4` and camunda/feel-scala (both Apache-2.0).

## Machine-readable sources and test corpus

- OMG DMN 1.6 (formal/25-12-02, September 2026): `DMN16.xmi` (59 classes,
  5 enumerations), `DMN16.xsd` (namespace `https://www.omg.org/spec/DMN/20240513/MODEL/`,
  does not dereference), `DMNDI15.xmi/xsd`, `DC.xsd`, `DI.xsd`; informative
  example models in `dtc/24-05-22.zip`.
- DMN TCK (dmn-tck/tck, active): 168 `.dmn` models with expected results, all
  seven hit policies, results of twelve vendors. All models use the DMN 1.5
  namespace (`20230324`); a 1.6 reader must accept it. Licence unclear (an
  Apache-2.0 file, the README says Creative Commons share-alike): fetch at test
  time, do not redistribute, until clarified.
