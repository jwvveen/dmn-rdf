"""Validate DMN models: SHACL shapes plus the computed decision table checks.

    py valideer.py model.dmn [more.dmn ...]       DMN XML, converted first
    py valideer.py model.ttl                      RDF in the canonical form
    py valideer.py --lang nl model.dmn            messages in en, nl, de or fr

Loads dmn.ttl, dmn-matrix.ttl and the model into one data graph, runs the
shapes in shacl/, then tools/beslistabel.py over every decision table, and
prints one report. Exit code 1 when there is a Violation.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import beslistabel  # noqa: E402
import dmn2rdf  # noqa: E402

SH = Namespace("http://www.w3.org/ns/shacl#")
MAP = HIER.parent


def ontologie() -> Graph:
    g = Graph()
    for f in ("dmn.ttl", "dmn-matrix.ttl", "dmn-bridges.ttl"):
        g.parse(MAP / f, format="turtle")
    # The ArchiMate ontology for the bridge shapes, when it sits next to this one
    # (ontology/archimate) or a clone of archimate-rdf next to this repository.
    for am in (MAP.parent / "archimate", MAP.parent / "archimate-rdf"):
        if (am / "archimate.ttl").exists():
            for f in ("archimate.ttl", "archimate-profile-3.2.ttl"):
                g.parse(am / f, format="turtle")
            break
    return g


def vormen() -> Graph:
    g = Graph()
    for f in sorted((MAP / "shacl").glob("dmn*-shapes.ttl")):
        g.parse(f, format="turtle")
    return g


def model(pad: Path) -> Graph:
    if pad.suffix.lower() == ".dmn" or pad.suffix.lower() == ".xml":
        base = "urn:dmn:" + "".join(c if c.isalnum() or c == "-" else "-" for c in pad.stem) + ":"
        g, _ = dmn2rdf.converteer(pad.read_bytes(), base)
        return g
    g = Graph()
    g.parse(pad, format="turtle")
    return g


def berichten(sg: Graph, beperking: object, vorm: object) -> dict[str, str]:
    """The messages per language, from the shapes graph itself: pyshacl drops the
    language tags of sh:message in its report, and then the languages mix."""
    for knoop in (beperking, vorm):
        if knoop is None:
            continue
        ms = {
            m.language: str(m)
            for m in sg.objects(knoop, SH.message)
            if isinstance(m, Literal) and m.language
        }
        if ms:
            return ms
    return {}


def valideer(data: Graph) -> list[dict]:
    """All results, SHACL and computed, as dicts (focus, ernst, bron, berichten per taal)."""
    from pyshacl import validate

    graaf = ontologie() + data
    sg = vormen()
    _, rapport, _ = validate(graaf, shacl_graph=sg, inference="none", advanced=True)
    uit = []
    for res in rapport.subjects(SH.resultSeverity, None):
        bron = rapport.value(res, SH.sourceShape)
        bron = next(iter(sg.subjects(SH.property, bron)), bron)  # property shape -> its node shape
        uit.append(
            {
                "focus": rapport.value(res, SH.focusNode),
                "ernst": str(rapport.value(res, SH.resultSeverity)).rsplit("#", 1)[-1],
                "bron": bron,
                "waarde": rapport.value(res, SH.value),
                "berichten": berichten(
                    sg, rapport.value(res, SH.sourceConstraint), rapport.value(res, SH.sourceShape)
                )
                or berichten(sg, None, bron)
                or {"en": str(rapport.value(res, SH.resultMessage) or "")},
            }
        )
    for b in beslistabel.analyseer(graaf):
        uit.append(
            {
                "focus": b.focus,
                "ernst": b.ernst,
                "bron": b.controle,
                "waarde": b.waarde,
                "berichten": {t: b.bericht(t) for t in beslistabel.TALEN},
            }
        )
    volgorde = {"Violation": 0, "Warning": 1, "Info": 2}
    return sorted(uit, key=lambda r: (volgorde.get(r["ernst"], 3), str(r["bron"]), str(r["focus"])))


def kort(term: object) -> str:
    s = str(term)
    return s.rsplit("#", 1)[-1] if isinstance(term, URIRef) and "#" in s else s.rsplit(":", 1)[-1]


def main() -> int:
    args = sys.argv[1:]
    taal = "en"
    if "--lang" in args:
        i = args.index("--lang")
        taal = args[i + 1]
        del args[i : i + 2]
    fout = False
    for a in args:
        res = valideer(model(Path(a)))
        print(f"== {a}")
        for r in res:
            print(
                f"  {r['ernst']:9} {kort(r['bron']):30} {kort(r['focus'])}: "
                f"{r['berichten'].get(taal) or r['berichten'].get('en', '')}"
            )
        telling = Counter(r["ernst"] for r in res)
        print(
            "  " + ", ".join(f"{k} {v}" for k, v in sorted(telling.items()))
            if telling
            else "  conforms"
        )
        fout |= telling["Violation"] > 0
    return 1 if fout else 0


if __name__ == "__main__":
    raise SystemExit(main())
