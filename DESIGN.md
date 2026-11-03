# DMN 1.6 in RDF: design notes

What the draft claims, how it was built, and where its limits are. Versions as
used and tested on 3 November 2026: Python 3.14, rdflib 7.6.0, pyshacl 0.31.0.
Paths refer to the public repository (github.com/jwvveen/dmn-rdf); in SemanticXL
the generators are scripts/genereer_dmn_*.py and the coverage is scripts/dmn_dekking.py.

## Standards and entailment

* RDF 1.1, Turtle. Vocabulary terms are declared with OWL 2 and RDFS
  (`owl:Class`, `owl:ObjectProperty`, `rdfs:subClassOf`, `rdfs:domain`,
  `rdfs:range`, `schema:domainIncludes` where a property has several owners).
* Domain and range are documentation of the metamodel. Validation runs with
  `inference="none"`: no RDFS or OWL entailment is applied, so a domain does not
  make anything an instance of a class. Where a check needs the class hierarchy
  it follows `rdfs:subClassOf*` explicitly.
* SHACL 1.0: SHACL Core plus SPARQL-based constraints (`sh:sparql`). The
  checker reports in the SHACL report vocabulary (`sh:ValidationResult`).

## What is generated and what is designed

* **Generated** from `DMN16.xmi` (scripts/generate_ontology_ttl.py): classes,
  the class hierarchy, properties with domain, range and upper bound, and the
  enumerations. The XML spelling of each enumeration value is kept as
  `dmn:xmlValue`.
* **Repaired**, after `DMN16.xsd` and the specification tables, each with an
  `rdfs:comment` that says so: the unnamed superclass of TypedChildExpression,
  the unnamed properties `functionItem` and `parameters`, the missing
  `iteratorVariable`. The converter also maps the XSD element
  `organizationUnit` to the class OrganisationalUnit.
* **Extensions**, maintained by hand and not part of the OMG metamodel:
  `dmn:position`, the matrix vocabulary (`dmn:RequirementRule` and its
  properties), the hit policy properties, the rule catalogue vocabulary, and
  the bridge properties (`dmn:legalBasis`, `dmn:meaning`, `dmn:elaborates`,
  `dmn:supportedBy`).
* **From the PDF**, extracted and checked against its text
  (sources/dmn-rules.json): Table 2, the hit policies and aggregations, and
  177 normative sentences. Which check covers which sentence is kept by hand in
  scripts/coverage.py.

## Cardinalities

UML multiplicities are not translated to OWL restrictions. The ontology keeps
the upper bound as an annotation (`dmn:upperBound` "1" or "*"). Where a
multiplicity matters for validation, a SHACL shape states it explicitly (for
example one required target per requirement, at most one function item per
item definition). Where the text and the schema disagree on a multiplicity
(output decisions of a decision service, rules of a table), the shape follows
the text and warns.

## Order

`dmn:position` belongs to a member of an ordered collection, and is its 1-based
place in that collection. Every ordered collection in the metamodel is
composite (rules of a table, clauses, entries of a rule), so each member
belongs to exactly one collection and one position per member is enough. Seven
properties are marked ordered: six in the XMI, plus the repaired `parameters` of a
function item. The converter also numbers
parameters, bindings, list elements, relation rows and columns and context
entries, whose order FEEL relies on.

## The checker: scope and behaviour

* **Supported fragment.** Simple unary tests of S-FEEL (clause 9.2): `-`,
  comparisons `<`, `<=`, `>`, `>=` with a literal, intervals with open or
  closed ends, literals, lists of these, and `not(...)` around a list.
* **Datatypes.** Number (as decimal), string, boolean and date (`date("...")`).
  The domain of a column comes from its typeRef, following item definitions,
  or else from its cells.
* **Not analysed.** Names (`> Maximum`), functions, filters, paths, arithmetic,
  `null`, time, date and time, durations, and a cell whose type differs from
  its column. Each is reported once per table with the first reason.
* **Effect of a cell that is not analysed.** It takes no part in the overlap
  test (the pair is skipped), and a table with such a cell is not searched for
  gaps or masked rules. A result without findings is therefore only complete
  for a table without such cells.
* **Gaps** are computed against the declared input values of a column, when
  there are any. Otherwise: the whole number line or calendar for numbers and
  dates, true and false for booleans, and the values the table itself mentions
  for strings. Missing values (null) are not part of any domain.
* **ANY**: two overlapping rules conflict when both output entries are literals
  and differ. Outputs that are not literals are not compared.
* **FIRST**: a rule is reported as never applying when the earlier rules
  together cover every input it covers, computed over the elementary pieces of
  each column's domain. Above 50,000 combinations the search stops and says so.
* **What a clean result means.** Within the analysed fragment and the declared
  input domains, an overlap-free result establishes that no two rules match the
  same input. It does not establish completeness, and nothing here establishes
  legal correctness.

## Bridges are proposals

* The 23 ArchiMate bridge rules in `dmn-bridges.ttl` are a proposed mapping
  profile. Neither DMN nor ArchiMate defines them.
* `dmn:usingTask` and `dmn:usingProcess` are in the DMN metamodel; only their
  ranges, pointing to `https://w3id.org/bpmn#`, are ours. The shape that checks
  that the BPMN task also says it applies the decision (`bpmn:appliesRule`) is
  a project constraint; neither standard requires that mutual link.
* `dmn:legalBasis` states a relationship to a source of law. It is not evidence
  that the translation into rules is correct, nor of competence. Versions of
  the source, the interpretation and the review of the translation are not
  modelled yet.

## Corpus and coverage claims

* Corpus: the eight non-normative example models of DMN 1.6 (OMG document
  dtc/24-05-22) and 160 models of the DMN TCK at commit
  1e349176e5ae689d924a2a2c7a8df25c220d8b07 (19 October 2026). The TCK models use
  the DMN 1.5 namespace; the converter accepts DMN 1.2 to 1.6.
* "Converted" means: no error, and every element and attribute in the DMN
  namespace mapped to a property or class; only vendor extensions are skipped.
  There is no writer back to DMN XML, so there is no round-trip test, and no
  claim that conversion is lossless.

## Configuration pitfalls (rdflib 7.6.0, pyshacl 0.31.0)

Measured on the example models; implementation behaviour, not properties of
SHACL itself.

* **Query shape, not data size.** The first version of the requirement matrix
  check took 525 s on OMG's Chapter 12 example (49 requirements). It matched
  the owner through a variable predicate filtered with `IN`, and found the cell
  by its properties (`?cell dmn:requiredType ?a ; dmn:requiringType ?b`); rdflib
  orders triple patterns by their number of variables, not by what is bound, so
  both walked large parts of the graph for every requirement. Looking the cell
  up by its IRI (`dmn:req-<required>-<requiring>`, set by the generator) was not
  enough on its own: written with UNION blocks, the check still took about 100 s
  per requirement; as far as we could tell, a UNION block was evaluated without
  the `$this` that pyshacl binds. Property path alternatives (`a|b|c`) and the IRI lookup took it
  to about 0.5 s per requirement, and one query per model (next point) to 0.1 s
  for the whole model. The whole validation of that model now takes 1.8 s
  (warm). The individual contributions of the first two causes were not
  measured separately.
* **Per focus node.** pyshacl runs a SPARQL constraint once per focus node. Four
  graph-wide checks (the matrix, requirement targets, unique names, variable names) target the model
  (`dmn:Definitions`) and report the element as `sh:value`: one query per model.
* **No VALUES.** A SPARQL-based constraint may not contain a VALUES clause; use
  `FILTER (?x IN (...))`.
* **Severity.** `sh:severity` on a node shape does not apply to the results of
  its property shapes; set it on the property shape.
* **Language tags.** The `sh:resultMessage` values in pyshacl's report came back
  without their language tag, so the four languages could not be told apart. The
  validator reads the messages from the shapes graph instead.
