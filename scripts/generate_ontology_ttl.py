"""Generate the DMN 1.6 core ontology from OMG's own metamodel (DMN16.xmi).

    py scripts/generate_ontology_ttl.py [pad/naar/DMN16.xmi]

Without an argument the XMI is downloaded from
https://www.omg.org/spec/DMN/20240513/DMN16.xmi into sources/.cache/
(not committed: the OMG files stay at OMG). Writes dmn.ttl.

Nothing in dmn.ttl is typed by hand except the Dutch labels (NL below) and
the ontology header: classes, the class hierarchy, properties, their domains,
ranges and multiplicities, and the enumerations all come from the metamodel.

Two choices the XMI leaves open:

* The XMI carries stubs for two classes of other OMG specifications that a
  Decision points to: BPMN Process and Task (``usingProcess``, ``usingTask``).
  Their ranges point to https://w3id.org/bpmn#, so the bridge to BPMN 2.0 in
  RDF sits in the core and not in a separate file. The BMM stub (Objective)
  stays a DMN class: there is no BMM in RDF to point to.
* Diagram interchange (DMNDI) is left out, as in BPMN 2.0 in RDF: geometry
  belongs in the XML, which stays the round-trip format.
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

WORTEL = Path(__file__).resolve().parents[1]
MAP = WORTEL
XMI_URL = "https://www.omg.org/spec/DMN/20240513/DMN16.xmi"
NS = "https://w3id.org/dmn#"
BPMN = "https://w3id.org/bpmn#"
X = "{http://www.omg.org/spec/XMI/20131001}"
VERSIE = "0.1.0"

#: Dutch labels for what a modeller meets. The rest keeps its English label.
NL = {
    "Definitions": "Definities",
    "Decision": "Beslissing",
    "BusinessKnowledgeModel": "Rekenmodule",
    "DecisionService": "Beslisservice",
    "InputData": "Invoergegeven",
    "KnowledgeSource": "Kennisbron",
    "InformationRequirement": "Informatievereiste",
    "KnowledgeRequirement": "Kennisvereiste",
    "AuthorityRequirement": "Autoriteitsvereiste",
    "DRGElement": "DRG-element",
    "DecisionTable": "Beslistabel",
    "DecisionRule": "Beslisregel",
    "InputClause": "Invoerkolom",
    "OutputClause": "Uitvoerkolom",
    "RuleAnnotationClause": "Annotatiekolom",
    "RuleAnnotation": "Regelannotatie",
    "UnaryTests": "Unaire toetsen",
    "LiteralExpression": "Letterlijke expressie",
    "Expression": "Expressie",
    "ItemDefinition": "Gegevenstype",
    "InformationItem": "Informatie-item",
    "Invocation": "Aanroep",
    "Binding": "Binding",
    "FunctionDefinition": "Functiedefinitie",
    "Context": "Context",
    "ContextEntry": "Contextregel",
    "List": "Lijst",
    "Relation": "Relatie",
    "Conditional": "Voorwaardelijke expressie",
    "Filter": "Filter",
    "For": "Herhaling",
    "Some": "Er is een",
    "Every": "Voor alle",
    "Iterator": "Iterator",
    "OrganisationalUnit": "Organisatie-eenheid",
    "PerformanceIndicator": "Prestatie-indicator",
    "Objective": "Doelstelling",
    "BusinessContextElement": "Bedrijfscontextelement",
    "TextAnnotation": "Tekstannotatie",
    "Association": "Associatie",
    "Group": "Groep",
    "Artifact": "Artefact",
    "Import": "Import",
    "ImportedValues": "Geïmporteerde waarden",
    "ElementCollection": "Elementverzameling",
    "HitPolicy": "Hit policy",
    "BuiltinAggregator": "Aggregatie",
    "NamedElement": "Element met naam",
    "DMNElement": "DMN-element",
}

_PRIM = {
    "String": "xsd:string",
    "Boolean": "xsd:boolean",
    "Integer": "xsd:integer",
    "Real": "xsd:decimal",
    "URI": "xsd:anyURI",
    "QName": "xsd:string",
    "ID": "xsd:string",
}
#: Defects in DMN16.xmi, corrected here and reported in the ontology itself.
#: TypedChildExpression generalizes an empty class without a name; DMN16.xsd has
#: tTypedChildExpression extend tChildExpression.
CORRECTIES = {
    "TypedChildExpression": (
        "ChildExpression",
        "DMN16.xmi gives TypedChildExpression an unnamed, empty superclass; "
        "DMN16.xsd has tTypedChildExpression extend tChildExpression, which is followed here.",
    )
}

#: Properties DMN16.xmi leaves without a name or omits, while the specification
#: tables and DMN16.xsd have them: (class, property, type, composite, many, why).
AANVULLINGEN = [
    (
        "ItemDefinition",
        "functionItem",
        "FunctionItem",
        True,
        False,
        "DMN16.xmi has this composite property without a name; Table 26 (clause 7.3.3) and DMN16.xsd call it functionItem.",
    ),
    (
        "FunctionItem",
        "parameters",
        "InformationItem",
        True,
        True,
        "DMN16.xmi has this composite property without a name; Table 27 (clause 7.3.3) and DMN16.xsd call it parameters.",
    ),
    (
        "Iterator",
        "iteratorVariable",
        "String",
        False,
        False,
        "Missing from DMN16.xmi; Table 92 (clause 10.5.9) and DMN16.xsd (tIterator) have it.",
    ),
]

#: Stubs of other specifications in the XMI and where they point to.
_BUITEN = {"Process": "bpmn:Process", "Task": "bpmn:Task", "DMNDI": "rdfs:Resource"}


def woorden(naam: str) -> str:
    """DecisionService -> 'Decision service' (spec style: first word capitalised)."""
    delen = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+", naam)
    if not delen:
        return naam
    return " ".join(
        [delen[0]] + [d if d.isupper() and len(d) > 1 else d.lower() for d in delen[1:]]
    )


def lit(t: str, taal: str = "en") -> str:
    return '"' + t.replace("\\", "\\\\").replace('"', '\\"') + f'"@{taal}'


def waarde_iri(enum: str, waarde: str) -> str:
    """'RULE ORDER' -> dmn:HitPolicy-RULE_ORDER (an IRI cannot hold a space)."""
    return f"dmn:{enum}-{re.sub(r'[^A-Za-z0-9_-]', '_', waarde)}"


def lees(pad: Path) -> dict:
    r = ET.parse(pad).getroot()
    per_id: dict[str, ET.Element] = {
        e.attrib[X + "id"]: e for e in r.iter() if X + "id" in e.attrib
    }
    pakket: dict[str, str] = {}

    def loop(e: ET.Element, naam: str | None) -> None:
        for c in e:
            t = c.attrib.get(X + "type")
            if t == "uml:Package":
                loop(c, c.attrib.get("name"))
            elif t in ("uml:Class", "uml:Enumeration", "uml:PrimitiveType") and c.attrib.get(
                "name"
            ):
                pakket[c.attrib["name"]] = naam or ""

    loop(r, None)
    soort = {
        e.attrib["name"]: e.attrib[X + "type"][4:]
        for e in per_id.values()
        if e.attrib.get(X + "type") in ("uml:Class", "uml:Enumeration", "uml:PrimitiveType")
        and e.attrib.get("name")
    }
    return {"wortel": r, "per_id": per_id, "pakket": pakket, "soort": soort}


def type_van(attr: ET.Element, per_id: dict) -> str:
    t = attr.attrib.get("type")
    if t:
        e = per_id.get(t)
        return e.attrib.get("name", "Element") if e is not None else "Element"
    for g in attr:
        if g.tag == "type" and "href" in g.attrib:
            return g.attrib["href"].split("#")[-1]
    return "Element"


def veelvoud(attr: ET.Element) -> tuple[int, str]:
    """UML XMI: no lowerValue means 1, a lowerValue without value means 0; same for upper."""
    onder = attr.find("lowerValue")
    boven = attr.find("upperValue")
    lo = 1 if onder is None else int(onder.attrib.get("value", "0"))
    hi = "1" if boven is None else boven.attrib.get("value", "0")
    return lo, hi


def genereer(pad: Path) -> str:
    d = lees(pad)
    per_id, pakket, soort = d["per_id"], d["pakket"], d["soort"]
    sha = hashlib.sha256(pad.read_bytes()).hexdigest()
    klassen = {
        n
        for n, s in soort.items()
        if s == "Class" and pakket.get(n) in ("DMN", "BMM") and n not in _BUITEN
    }
    enums = {
        n: [lt.attrib["name"] for lt in per_id_by_name(per_id, n).findall("ownedLiteral")]
        for n, s in soort.items()
        if s == "Enumeration"
    }
    uit = [
        f"@prefix dmn: <{NS}> .",
        f"@prefix bpmn: <{BPMN}> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix dct: <http://purl.org/dc/terms/> .",
        "@prefix schema: <https://schema.org/> .",
        "",
        "# GENERATED by scripts/generate_ontology_ttl.py from the OMG DMN 1.6 metamodel",
        f"# ({XMI_URL}, sha256 {sha}). Do not edit by hand.",
        "",
        f"<{NS.rstrip('#')}> a owl:Ontology ;",
        f"    dct:title {lit('DMN 1.6 in RDF: core ontology')}, {lit('DMN 1.6 in RDF: kernontologie', 'nl')} ;",
        f"    dct:description {lit('Classes, properties and enumerations of the DMN 1.6 metamodel, generated from DMN16.xmi. Concept version for discussion; not a publication of the Object Management Group.')} ;",
        f"    dct:source <{XMI_URL}> ;",
        "    dct:license <https://creativecommons.org/licenses/by/4.0/> ;",
        f'    owl:versionInfo "{VERSIE}" .',
        "",
        "dmn:abstract a owl:AnnotationProperty ;",
        f"    rdfs:label {lit('abstract')}, {lit('abstract', 'nl')} ;",
        f"    rdfs:comment {lit('True for metamodel classes that have no instances of their own (isAbstract in the XMI).')} .",
        "",
        "dmn:composite a owl:AnnotationProperty ;",
        f"    rdfs:label {lit('composite')} ;",
        f"    rdfs:comment {lit('True for properties that own their values (aggregation composite in the XMI): the value lives inside its owner.')} .",
        "",
        "dmn:upperBound a owl:AnnotationProperty ;",
        f"    rdfs:label {lit('upper bound')} ;",
        f"    rdfs:comment {lit('Highest multiplicity of the property in the metamodel over all its owners: 1, or * for many.')} .",
        "",
        "dmn:ordered a owl:AnnotationProperty ;",
        f"    rdfs:label {lit('ordered')} ;",
        f"    rdfs:comment {lit('True for properties whose values are ordered in the metamodel (isOrdered in the XMI), such as the rules and entries of a decision table. Instance data records the order with dmn:position.')} .",
        "",
        "dmn:position a owl:DatatypeProperty ;",
        f"    rdfs:label {lit('position')}, {lit('positie', 'nl')} ;",
        f"    rdfs:comment {lit('1-based position of a value of an ordered property within its owner. Not part of the OMG metamodel: RDF has no order of its own, and in DMN order carries meaning (rules of a FIRST or RULE ORDER table, the entry that belongs to each clause).')} ;",
        "    rdfs:range xsd:positiveInteger .",
        "",
        "dmn:xmlValue a owl:DatatypeProperty ;",
        f"    rdfs:label {lit('XML value')} ;",
        f"    rdfs:comment {lit('The literal of an enumeration value exactly as it is written in DMN XML.')} .",
        "",
    ]
    for naam in sorted(klassen):
        e = per_id_by_name(per_id, naam)
        supers = sorted(
            {
                per_id[g.attrib["general"]].attrib.get("name", "")
                for g in e.findall("generalization")
                if g.attrib.get("general") in per_id
            }
            - {""}
        )
        regels = [
            f"dmn:{naam} a owl:Class",
            f"rdfs:label {lit(woorden(naam))}" + (f", {lit(NL[naam], 'nl')}" if naam in NL else ""),
        ]
        if naam in CORRECTIES:
            supers = sorted(set(supers) | {CORRECTIES[naam][0]})
            regels.append(f"rdfs:comment {lit('Correction: ' + CORRECTIES[naam][1])}")
        regels += [f"rdfs:subClassOf dmn:{s}" for s in supers if s in klassen]
        if e.attrib.get("isAbstract") == "true":
            regels.append("dmn:abstract true")
        regels.append(f"rdfs:isDefinedBy <{NS.rstrip('#')}>")
        uit.append(" ;\n    ".join(regels) + " .\n")
    for naam, waarden in sorted(enums.items()):
        label = f"rdfs:label {lit(woorden(naam))}" + (
            f", {lit(NL[naam], 'nl')}" if naam in NL else ""
        )
        uit.append(
            f"dmn:{naam} a owl:Class ;\n    {label} ;\n"
            f"    owl:oneOf ( {' '.join(waarde_iri(naam, w) for w in waarden)} ) ;\n"
            f"    rdfs:isDefinedBy <{NS.rstrip('#')}> .\n"
        )
        for w in waarden:
            uit.append(
                f'{waarde_iri(naam, w)} a dmn:{naam} ; rdfs:label {lit(w)} ; dmn:xmlValue "{w}" .'
            )
        uit.append("")
    eigenaar: dict[str, set[str]] = defaultdict(set)
    bereik: dict[str, set[str]] = defaultdict(set)
    samengesteld: dict[str, bool] = defaultdict(bool)
    veel: dict[str, bool] = defaultdict(bool)
    geordend: dict[str, bool] = defaultdict(bool)
    for naam in klassen:
        for a in per_id_by_name(per_id, naam).findall("ownedAttribute"):
            if not a.attrib.get("name"):
                continue
            p = a.attrib["name"]
            eigenaar[p].add(naam)
            bereik[p].add(type_van(a, per_id))
            samengesteld[p] |= a.attrib.get("aggregation") == "composite"
            veel[p] |= veelvoud(a)[1] != "1"
            geordend[p] |= a.attrib.get("isOrdered") == "true"

    reden: dict[str, str] = {}
    for k, p, t, comp, many, why in AANVULLINGEN:
        eigenaar[p].add(k)
        bereik[p].add(t)
        samengesteld[p] |= comp
        veel[p] |= many
        geordend[p] |= many
        reden[p] = why

    def rng_van(t: str) -> str:
        if t in klassen or t in enums:
            return f"dmn:{t}"
        if t in _BUITEN:
            return _BUITEN[t]
        return _PRIM.get(t, "rdfs:Resource")

    for p in sorted(eigenaar):
        typen = bereik[p]
        object_ = all(t in klassen or t in enums or t in _BUITEN or t == "Element" for t in typen)
        regels = [
            f"dmn:{p} a {'owl:ObjectProperty' if object_ else 'owl:DatatypeProperty'}",
            f"rdfs:label {lit(woorden(p))}",
        ]
        dom = sorted(eigenaar[p])
        regels += (
            [f"rdfs:domain dmn:{dom[0]}"]
            if len(dom) == 1
            else [f"schema:domainIncludes dmn:{x}" for x in dom]
        )
        rng = sorted({rng_van(t) for t in typen})
        regels += (
            [f"rdfs:range {rng[0]}"]
            if len(rng) == 1
            else [f"schema:rangeIncludes {r}" for r in rng]
        )
        if p in reden:
            regels.append(f"rdfs:comment {lit('Correction: ' + reden[p])}")
        if samengesteld[p]:
            regels.append("dmn:composite true")
        regels.append(f'dmn:upperBound "{"*" if veel[p] else "1"}"')
        if geordend[p] and veel[p]:
            regels.append("dmn:ordered true")
        regels.append(f"rdfs:isDefinedBy <{NS.rstrip('#')}>")
        uit.append(" ;\n    ".join(regels) + " .\n")
    return "\n".join(uit)


def per_id_by_name(per_id: dict, naam: str) -> ET.Element:
    for e in per_id.values():
        if e.attrib.get("name") == naam and e.attrib.get(X + "type") in (
            "uml:Class",
            "uml:Enumeration",
        ):
            return e
    raise KeyError(naam)


def bron() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    pad = MAP / "sources" / ".cache" / "DMN16.xmi"
    if not pad.exists():
        pad.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(XMI_URL, timeout=60) as r:  # noqa: S310 - vast adres
            pad.write_bytes(r.read())
    return pad


def main() -> None:
    tekst = genereer(bron())
    (MAP / "dmn.ttl").write_text(tekst, encoding="utf-8", newline="\n")
    print(
        "dmn.ttl",
        tekst.count(" a owl:Class"),
        "klassen,",
        tekst.count("a owl:ObjectProperty") + tekst.count("a owl:DatatypeProperty"),
        "eigenschappen",
    )


if __name__ == "__main__":
    main()
