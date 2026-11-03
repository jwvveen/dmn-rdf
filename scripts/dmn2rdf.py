"""DMN XML to RDF in the canonical form of the DMN 1.6 in RDF ontology.

    py dmn2rdf.py model.dmn [--base https://example.org/model/] [--lang en] > model.ttl

Metamodel-driven, like bpmn2rdf.py: which XML element or attribute becomes
which RDF property is read from dmn.ttl (generated from OMG's DMN16.xmi), not
from a hand-written mapping. Every element with an id becomes a resource;
requirements keep their own identity, so the authority requirement that the
schema accepts but the specification forbids stays visible to the shapes.

Accepted: the DMN 1.2 to 1.6 model namespaces (the DMN TCK still uses 1.5).
Left out on purpose: diagram interchange (DMNDI), as in BPMN 2.0 in RDF.

Order carries meaning in DMN (the rules of a FIRST table, the entry that
belongs to each clause), and RDF has none. Every value of an ordered
property gets dmn:position (1-based). The metamodel marks rule, input,
output, inputEntry, outputEntry and annotation as ordered; ORDE_OOK lists the
properties whose order FEEL relies on but the XMI does not mark.

FEEL text stays text (dmn:text). The checker in valideer.py computes with it.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef

HIER = Path(__file__).resolve().parent
DMN = Namespace("https://w3id.org/dmn#")
SCHEMA = URIRef("https://schema.org/")
XSI = "http://www.w3.org/2001/XMLSchema-instance"
MODEL_NS = re.compile(r"^https?://www\.omg\.org/spec/DMN/(\d{8})/MODEL/?$")
#: Model namespace per DMN version, for the report.
VERSIES = {
    "20180521": "1.2",
    "20191111": "1.3",
    "20211108": "1.4",
    "20230324": "1.5",
    "20240513": "1.6",
}
#: Order that FEEL relies on, not marked isOrdered in DMN16.xmi: positional
#: parameters and arguments, list elements, relation rows and columns, context entries.
ORDE_OOK = {"formalParameter", "parameter", "binding", "element", "row", "column", "contextEntry"}
#: XML element names that the XSD spells differently from the metamodel.
XSD_NAAR_XMI: dict[str, str] = {}
#: Classes the XSD spells differently: element organizationUnit (tOrganizationUnit)
#: is class OrganisationalUnit in DMN16.xmi and in Table 14.
KLASSE_ALIAS = {"OrganizationUnit": "OrganisationalUnit"}


class Metamodel:
    """What the converter needs from dmn.ttl."""

    def __init__(self, g: Graph) -> None:
        def kort(t: Any) -> str:
            return str(t).split("#")[-1]

        self.klassen = {
            kort(s) for s in g.subjects(RDF.type, OWL.Class) if str(s).startswith(str(DMN))
        }
        self.supers: dict[str, set[str]] = {k: set() for k in self.klassen}
        for s, o in g.subject_objects(RDFS.subClassOf):
            if str(s).startswith(str(DMN)) and str(o).startswith(str(DMN)):
                self.supers[kort(s)].add(kort(o))
        #: enumeration class -> {xml value: IRI}
        self.enums: dict[str, dict[str, URIRef]] = {}
        for waarde, xml in g.subject_objects(DMN.xmlValue):
            for k in g.objects(waarde, RDF.type):
                self.enums.setdefault(kort(k), {})[str(xml)] = URIRef(str(waarde))
        self.eigenschappen: dict[str, dict[str, Any]] = {}
        for soort in (OWL.ObjectProperty, OWL.DatatypeProperty):
            for p in g.subjects(RDF.type, soort):
                if not str(p).startswith(str(DMN)):
                    continue
                rng = list(g.objects(p, RDFS.range)) + list(g.objects(p, SCHEMA + "rangeIncludes"))
                self.eigenschappen[kort(p)] = {
                    "object": soort == OWL.ObjectProperty,
                    "domein": {kort(o) for o in g.objects(p, RDFS.domain)}
                    | {kort(o) for o in g.objects(p, SCHEMA + "domainIncludes")},
                    "bereik": {kort(o) for o in rng if str(o).startswith(str(DMN))},
                    "buiten": [o for o in rng if not str(o).startswith(str(DMN))],
                    "xsd": next((o for o in rng if str(o).startswith(str(XSD))), None),
                    "composiet": (p, DMN.composite, Literal(True)) in g,
                    "geordend": (p, DMN.ordered, Literal(True)) in g or kort(p) in ORDE_OOK,
                }

    def voorouders(self, klasse: str) -> set[str]:
        uit, rij = {klasse}, [klasse]
        while rij:
            for s in self.supers.get(rij.pop(), ()):
                if s not in uit:
                    uit.add(s)
                    rij.append(s)
        return uit

    def eigenschap_van(self, klasse: str, naam: str) -> str | None:
        anc = self.voorouders(klasse)
        e = self.eigenschappen.get(naam)
        return naam if e and e["domein"] & anc else None

    def bevattend(self, ouder: str, kind: str) -> str | None:
        anc_o, anc_k = self.voorouders(ouder), self.voorouders(kind)
        kandidaten = [
            n
            for n, e in self.eigenschappen.items()
            if e["composiet"] and e["domein"] & anc_o and e["bereik"] & anc_k
        ]
        return min(kandidaten, key=len) if kandidaten else None

    def enum_van(self, p: str) -> str | None:
        return next((r for r in self.eigenschappen[p]["bereik"] if r in self.enums), None)


_MM: Metamodel | None = None


def laad_metamodel() -> Metamodel:
    """De ontologie naast deze map (ontology/dmn/dmn.ttl), of de kopie naast dit bestand."""
    global _MM
    if _MM is None:
        g = Graph()
        for pad in (HIER.parent / "dmn.ttl", HIER / "dmn.ttl"):
            if pad.exists():
                g.parse(pad, format="turtle")
                break
        _MM = Metamodel(g)
    return _MM


def _ontleed(xml: bytes) -> ET.Element:
    """XML van buiten veilig ontleden (zoals bpmn2rdf): in SemanticXL via
    semanticxl.veilig_xml, los weigeren we een DOCTYPE of entiteiten."""
    try:
        from semanticxl import veilig_xml
    except ImportError:
        kop = xml.lstrip()[:65536].lower()
        if b"<!doctype" in kop or b"<!entity" in kop:
            raise ValueError("DMN file with a DOCTYPE or entities is not read") from None
        parser = ET.XMLParser()
        parser.feed(xml)
        return parser.close()
    return veilig_xml.ontleed(xml)


def _klasse(lokaal: str, mm: Metamodel) -> str | None:
    k = lokaal[:1].upper() + lokaal[1:]
    k = KLASSE_ALIAS.get(k, k)
    return k if k in mm.klassen else None


def model_versie(xml: bytes) -> str | None:
    """De DMN-versie volgens de namespace van het wortelelement, of None."""
    tag = _ontleed(xml).tag
    m = MODEL_NS.match(tag[1:].split("}")[0]) if tag.startswith("{") else None
    return VERSIES.get(m.group(1), m.group(1)) if m else None


def converteer(
    xml: bytes, base: str, taal: str = "en", mm: Metamodel | None = None
) -> tuple[Graph, Counter[str]]:
    """DMN-XML naar een graaf. Geeft ook terug wat er niet kon (per tag of attribuut)."""
    mm = mm or laad_metamodel()
    g = Graph()
    g.bind("dmn", DMN)
    onbekend: Counter[str] = Counter()
    wortel = _ontleed(xml)
    model = wortel.tag[1:].split("}")[0] if wortel.tag.startswith("{") else ""
    if not MODEL_NS.match(model):
        raise ValueError(f"not a DMN 1.2-1.6 model (root namespace {model or 'none'})")
    eigen_ns = wortel.attrib.get("namespace", "")
    # Twee elementen met één id worden in RDF één resource: dat melden we hier,
    # want de graaf kan het daarna niet meer laten zien (6.3.1: uniek binnen Definitions).
    for ident, n in Counter(el.attrib["id"] for el in wortel.iter() if "id" in el.attrib).items():
        if n > 1:
            onbekend[f"duplicate id {ident}"] += n

    def iri(ident: str) -> URIRef:
        return URIRef(base + ident)

    def verwijzing(href: str) -> URIRef:
        """'#id' in dit model; 'ns#id' in een geïmporteerd model (de ns als basis)."""
        ns, _, ident = href.rpartition("#")
        if not ns or ns == eigen_ns:
            return iri(ident)
        return URIRef(f"{ns}#{ident}")

    def literal(waarde: str, eig: dict[str, Any]) -> Literal:
        x = eig.get("xsd")
        if x == XSD.boolean:
            return Literal(waarde.strip().lower() == "true", datatype=XSD.boolean)
        if x == XSD.anyURI:
            return Literal(waarde, datatype=XSD.anyURI)
        return Literal(waarde)

    def element(el: ET.Element, klasse: str, onderwerp: URIRef | BNode) -> None:
        g.add((onderwerp, RDF.type, DMN[klasse]))
        for a, waarde in el.attrib.items():
            if a.startswith("{"):
                if not a.startswith(f"{{{XSI}}}"):
                    onbekend[f"@{klasse}.{a.split('}')[-1]} (extension)"] += 1
                continue
            p = mm.eigenschap_van(klasse, XSD_NAAR_XMI.get(a, a))
            if not p:
                onbekend[f"@{klasse}.{a}"] += 1
                continue
            eig = mm.eigenschappen[p]
            enum = mm.enum_van(p) if eig["object"] else None
            if enum:
                w = mm.enums[enum].get(waarde)
                if w is None:
                    onbekend[f"@{klasse}.{a}={waarde}"] += 1
                else:
                    g.add((onderwerp, DMN[p], w))
            elif eig["object"]:
                g.add((onderwerp, DMN[p], verwijzing(waarde)))
            else:
                g.add((onderwerp, DMN[p], literal(waarde, eig)))
            if a == "name" and waarde.strip():
                g.add((onderwerp, RDFS.label, Literal(waarde, lang=taal)))
        posities: Counter[str] = Counter()
        for kind in el:
            if not isinstance(kind.tag, str) or not kind.tag.startswith(f"{{{model}}}"):
                continue  # DMNDI, extensies, commentaar
            lokaal = kind.tag.split("}")[-1]
            if lokaal == "extensionElements":
                continue
            p = mm.eigenschap_van(klasse, XSD_NAAR_XMI.get(lokaal, lokaal))
            eig = mm.eigenschappen.get(p or "", {})
            if p and not eig["object"]:
                if (kind.text or "").strip():
                    g.add((onderwerp, DMN[p], literal((kind.text or "").strip(), eig)))
                    if lokaal == "description":
                        g.add(
                            (onderwerp, RDFS.comment, Literal((kind.text or "").strip(), lang=taal))
                        )
                continue
            if p and eig["object"] and not eig["composiet"] and "href" in kind.attrib:
                g.add((onderwerp, DMN[p], verwijzing(kind.attrib["href"])))
                continue
            t = kind.attrib.get(f"{{{XSI}}}type", "").split(":")[-1]
            kk = (_klasse(t[1:], mm) if t.startswith("t") else None) or _klasse(lokaal, mm)
            if p and (not kk or not (mm.voorouders(kk) & eig["bereik"])):
                rng = sorted(eig["bereik"])
                algemeen = [r for r in rng if all(r in mm.voorouders(o) for o in rng)]
                kk = algemeen[0] if algemeen else (rng[0] if len(rng) == 1 else kk)
            if not kk:
                onbekend[f"<{klasse}/{lokaal}>"] += 1
                continue
            p = p or mm.bevattend(klasse, kk)
            if not p:
                onbekend[f"<{klasse}/{lokaal}>"] += 1
                continue
            sub: URIRef | BNode = iri(kind.attrib["id"]) if "id" in kind.attrib else BNode()
            g.add((onderwerp, DMN[p], sub))
            if mm.eigenschappen[p]["geordend"]:
                posities[p] += 1
                g.add((sub, DMN.position, Literal(posities[p], datatype=XSD.positiveInteger)))
            element(kind, kk, sub)

    element(
        wortel,
        _klasse(wortel.tag.split("}")[-1], mm) or "Definitions",
        iri(wortel.attrib.get("id", "definitions")),
    )
    return g, onbekend


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("bestand")
    ap.add_argument("--base", default="")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    pad = Path(a.bestand)
    g, onbekend = converteer(
        pad.read_bytes(),
        a.base or "urn:dmn:" + re.sub(r"[^A-Za-z0-9-]", "-", pad.stem) + ":",
        a.lang,
    )
    sys.stdout.buffer.write(g.serialize(format="turtle").encode("utf-8"))
    if onbekend:
        sys.stderr.write(
            "niet omgezet: " + ", ".join(f"{k} ({n})" for k, n in onbekend.most_common()) + "\n"
        )


if __name__ == "__main__":
    main()
