# DMN 1.6 in RDF (draft)

A draft OWL ontology, SHACL validation set and decision table checker for DMN
1.6 (OMG, formal/25-12-02), built the same way as
[ArchiMate 4.0 in RDF](https://github.com/jwvveen/archimate-rdf) and
[BPMN 2.0 in RDF](https://github.com/jwvveen/bpmn-rdf): the rules of the
specification are data, validation is separate from meaning, and decision models
connect to processes, the law, concepts and architecture.

*Nederlandse versie: [README.nl.md](README.nl.md).*

Status: **0.1.0-concept**. A discussion piece, not a standard. DMN is a
specification of the Object Management Group; this is not an OMG publication.
Namespace: `https://w3id.org/dmn#` (registration requested in
[perma-id/w3id.org#7065](https://github.com/perma-id/w3id.org/pull/7065); until it is
merged the IRIs do not resolve yet). Design notes: [DESIGN.md](DESIGN.md).

## Files

| File | Role |
|---|---|
| `dmn.ttl` | **Generated** from OMG's own metamodel (`DMN16.xmi`): 60 classes, 127 properties with domain, range and upper bound, 5 enumerations whose values carry their XML spelling. Ordered properties (rules, clauses, entries) are marked `dmn:ordered`. Generated from the metamodel, with documented repairs; the extensions are maintained separately (see `DESIGN.md`) |
| `dmn-matrix.ttl` | **Generated**: the 25 cells of Table 2 (clause 6.2.3), each with what the specification permits, what `DMN16.xsd` and `DMN16.xmi` accept, and the printed cell as provenance; plus the seven hit policies and four aggregations with their properties as data (single hit, rule order matters, overlap allowed, needs output values, compound output allowed) |
| `dmn-rules.ttl` | **Generated**: 177 normative sentences of clauses 6 to 10, verbatim with clause and page, each with the shape or computed check that tests it (94) or the reason nothing does (83) |
| `dmn-bridges.ttl` | Bridges to the law (`dmn:legalBasis`), to concepts (`dmn:meaning`) and to ArchiMate 4.0 (`dmn:elaborates`, `dmn:supportedBy`, 23 bridge rules as data). The bridge to BPMN is in the core: `dmn:usingTask` and `dmn:usingProcess` point to `https://w3id.org/bpmn#` |
| `dmn-alignments.ttl` | **Generated**: `skos:closeMatch` to DMN-O (DMN 1.1) and the WHO SMART Guidelines DMN layer, `skos:relatedMatch` to CPRMV, only to terms that exist in their files |
| `shacl/dmn-shapes.ttl` | Graph integrity, names, decision services, item definitions, the structure of decision tables; and the declaration of the computed checks |
| `shacl/dmn-matrix-shapes.ttl` | One generic constraint that reads Table 2 as data |
| `shacl/dmn-bridge-shapes.ttl` | The ArchiMate bridge rules and the agreement between `dmn:usingTask` and `bpmn:appliesRule` |
| `example.dmn` | A small model that is wrong on purpose; yields exactly eight results |
| `scripts/dmn2rdf.py` | Converter from DMN XML (1.2 to 1.6) to the canonical form, driven by the metamodel |
| `scripts/sfeel.py` | S-FEEL simple unary tests as sets of values (clause 9.2): number, string, boolean, date |
| `scripts/beslistabel.py` | Overlap, gaps, rules that never apply and values outside the lists, as a SHACL validation report |
| `validate.py` | Shapes plus computed checks, one report, in English, Dutch, German or French (`scripts/valideer.py`) |
| `DESIGN.md` | Design notes: standards and entailment, what is generated and what is designed, cardinalities, order, the exact scope of the checker, the corpus, and configuration pitfalls |
| `sources/` | `dmn-rules.json` (Table 2, hit policies and the 177 sentences, extracted from the PDF) and a survey of earlier work (`prior-work.md`) |

## What the specification does not say in its machine-readable files

* **The XML schema does not enforce four constraints of Table 2.** Table 2 and
  the text of Table 22 permit an authority requirement from a decision or input
  data only into a knowledge source. `DMN16.xsd` and `DMN16.xmi` let every
  decision, business knowledge model and knowledge source own any of the three
  kinds of authority requirement. So Decision → Decision, Input Data → Decision,
  Decision → BKM and Input Data → BKM as authority are schema-valid but not permitted by the text (a schema may enforce less than the text);
  and Decision → Decision is in the schema both information and authority, while
  the text says "the type of the requirement is uniquely determined by the types
  of the two elements connected". `dmn-matrix.ttl` records both readings per cell
  (`dmn:schemaAccepts`, `dmn:schemaMismatch`); the shape follows the text.
* **The metamodel file has gaps.** In `DMN16.xmi`, TypedChildExpression has an
  empty superclass without a name, `ItemDefinition.functionItem` and
  `FunctionItem.parameters` have no name, and `Iterator.iteratorVariable` is
  missing. The generator corrects them after the XSD and the specification tables,
  and says so in an `rdfs:comment` on each.
* **The specification contradicts itself on OUTPUT ORDER.** Clause 8.2.11.1
  allows it with more than one output (Figure 8-19 shows one); clause 10.3.2.10
  says such a table SHALL be single output. The shape warns instead of choosing.

## Design choices in short

* **The metamodel is data,** generated from `DMN16.xmi`; local names match the
  metamodel and the XML.
* **The table is data, and so is the prose.** Table 2 is small; most rules are
  sentences elsewhere. Both are in the graph, with provenance.
* **Order is data.** RDF has no order and DMN needs it: the rules of a FIRST
  table, the entry that belongs to each clause. Every value of an ordered
  property gets `dmn:position`.
* **FEEL stays text; a fragment of S-FEEL is analysed.** A cell keeps its FEEL
  text. The checker analyses a documented fragment (comparisons, intervals,
  lists, `not`, `-`) and makes no assumption about whether an unsupported
  expression matches: a rule pair with such a cell is not compared, the table is not
  searched for gaps, and the report says how many cells were not analysed. A
  result without findings is only complete for a fully analysed table. For
  strings without declared input values, gaps are sought only among the values
  the table mentions.
* **SHACL where SHACL can, a checker where it cannot,** with one report format.
* **Four languages.** Every message in English, Dutch, German and French.

## Validating

```
pip install rdflib pyshacl
python validate.py
python validate.py --lang nl model.dmn
```

Expected results on `example.dmn`, eight in total:

1. **Violation** `RequirementMatrixShape`: an authority requirement from one decision to another (`ar2`).
2. **Violation** `UniqueOverlap`: rules 1 and 2 of a UNIQUE table both apply to a resident with a diesel car.
3. **Violation** `AggregationShape`: a sum on a UNIQUE table.
4. **Violation** `OutputOutsideOutputValues`: 90 is not one of 0, 60, 120.
5. **Violation** `VariableNameShape`: decision Fee with variable Annual fee.
6. **Warning** `MaskedRule`: rule 3 of a FIRST table never applies.
7. **Info** `Gap`: no rule for visitors with a petrol or diesel car.
8. **Info** `NotDecided`: `> Maximum` names a value that is not known at design time.

Results on 168 example and test models. All converted without errors, with every element and attribute in the DMN namespace mapped and only vendor extensions skipped (a mapping check, not a round-trip test):

* The eight non-normative example models that OMG publishes with DMN 1.6: 0 requirement
  matrix violations; 8 rule annotation clauses without a name (8.3.2 SHALL), all
  in the Chapter 12 example, and 6 decision services without output, encapsulated
  or input decisions (6.3.10) in 3 of the 8 files; 33 uses of `allowedValues`,
  deprecated since DMN 1.5.
* 160 models of the DMN TCK (commit 1e34917, October 2026): 0 requirement matrix violations; 13 decision
  services without encapsulated or input decisions (6.3.10 SHALL asks for one of
  the two), 2 complete tables with a default
  output value (10.3.2.10 SHALL NOT), 1 OUTPUT ORDER table with two outputs,
  17 tables with gaps, and 12 tables with cells outside S-FEEL.

## Regenerating

```
python scripts/generate_ontology_ttl.py      # downloads DMN16.xmi into sources/.cache/
python scripts/generate_matrix_ttl.py        # dmn-matrix.ttl and dmn-rules.ttl
python scripts/generate_alignments.py
```

The generated files are committed; the scripts are the only way to change them.
The coverage of the rule catalogue is kept by hand in `scripts/coverage.py`.

## Earlier work

See `sources/prior-work.md`. The only earlier DMN metamodel ontology, DMN-O
(Nicholas Car, DMN 1.1, 2017), no longer resolves. Recent users that need a DMN
IRI: the WHO SMART Guidelines knowledge graph, and for Dutch government CPRMV
(open-regels.nl) and regels.overheid.nl. Decision table checkers: dmn-check and
Apache KIE; this one adds the RDF form and the S-FEEL boundary.

## Contributing

Disagreement is welcome, especially on the design choices and on the reading of
the specification where its text and its schema differ. Open an issue.

## License

Code: Apache 2.0, see [LICENSE](LICENSE). Ontology files: CC BY 4.0, as stated in
each file. The quoted sentences in `sources/dmn-rules.json` and `dmn-rules.ttl`
are short extracts of the DMN 1.6 specification (Object Management Group),
quoted with clause and page for the purpose of checking models against them.
