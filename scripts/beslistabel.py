"""Decision table analysis on the RDF form: what SHACL cannot decide.

    from beslistabel import analyseer, als_rapport
    bevindingen = analyseer(graaf)          # graaf: dmn.ttl + model in canonical form
    rapport = als_rapport(bevindingen)      # sh:ValidationReport, same vocabulary as SHACL

Per decision table, over the S-FEEL cells (sfeel.py):

* UNIQUE: rules that overlap (8.2.11: "SHALL NOT contain overlapping rules")
* ANY: overlapping rules with different output entries (8.2.11.1)
* rules that never apply: empty, or (FIRST) covered by earlier rules
* gaps: input combinations no rule covers (8.1, 8.2.4)
* input entries outside the input values (8.2.8, SHOULD), output entries and
  the default output value outside the output values (8.2.6, Table 46)
* a default output value on a complete table (10.3.2.10)

The verdict is never false. A cell that is not an S-FEEL simple unary test
(a name, a function, full FEEL) makes every pair and every gap it takes part
in undecided; the table then gets one Info result that says how many cells
were left alone and why. Gap search runs over the elementary pieces of each
column's domain; above GRENS combinations it stops and says so.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace, URIRef

try:
    from . import sfeel
except ImportError:  # los gebruikt, naast sfeel.py
    import sfeel  # type: ignore[no-redef,import-not-found]

DMN = Namespace("https://w3id.org/dmn#")
SH = Namespace("http://www.w3.org/ns/shacl#")
DMNSH = Namespace("https://w3id.org/dmn/shapes#")
#: Most combinations the gap and masking search visits per table.
GRENS = 50_000
TALEN = ("en", "nl", "de", "fr")

BERICHT: dict[str, dict[str, str]] = {
    "overlap": {
        "en": (
            "Rules {a} and {b} overlap: both apply to {voorbeeld}. A UNIQUE table SHALL "
            "NOT contain overlapping rules."
        ),
        "nl": (
            "Regels {a} en {b} overlappen: beide gelden voor {voorbeeld}. Een "
            "UNIQUE-tabel mag geen overlappende regels bevatten."
        ),
        "de": (
            "Die Regeln {a} und {b} überlappen: beide gelten für {voorbeeld}. Eine "
            "UNIQUE-Tabelle SHALL NOT überlappende Regeln enthalten."
        ),
        "fr": (
            "Les règles {a} et {b} se chevauchent : toutes deux s'appliquent à "
            "{voorbeeld}. Une table UNIQUE SHALL NOT contenir de règles qui se "
            "chevauchent."
        ),
    },
    "any": {
        "en": (
            "Rules {a} and {b} overlap ({voorbeeld}) and give different outputs. In an "
            "ANY table all matching rules SHALL give equal outputs."
        ),
        "nl": (
            "Regels {a} en {b} overlappen ({voorbeeld}) en geven een andere uitkomst. In "
            "een ANY-tabel moeten alle regels die gelden dezelfde uitkomst geven."
        ),
        "de": (
            "Die Regeln {a} und {b} überlappen ({voorbeeld}) und liefern verschiedene "
            "Ausgaben. In einer ANY-Tabelle SHALL alle zutreffenden Regeln gleiche "
            "Ausgaben liefern."
        ),
        "fr": (
            "Les règles {a} et {b} se chevauchent ({voorbeeld}) et donnent des sorties "
            "différentes. Dans une table ANY, toutes les règles applicables SHALL donner "
            "la même sortie."
        ),
    },
    "leeg": {
        "en": (
            "Rule {a} never applies: no value satisfies its input entries within the input values."
        ),
        "nl": (
            "Regel {a} geldt nooit: geen enkele waarde voldoet binnen de invoerwaarden "
            "aan zijn invoercellen."
        ),
        "de": (
            "Regel {a} gilt nie: kein Wert erfüllt ihre Eingabeeinträge innerhalb der Eingabewerte."
        ),
        "fr": (
            "La règle {a} ne s'applique jamais : aucune valeur ne satisfait ses entrées "
            "dans les valeurs d'entrée."
        ),
    },
    "gemaskeerd": {
        "en": (
            "Rule {a} never applies in this FIRST table: earlier rules ({b}) already "
            "cover every case it covers."
        ),
        "nl": (
            "Regel {a} geldt nooit in deze FIRST-tabel: eerdere regels ({b}) dekken al "
            "elk geval dat hij dekt."
        ),
        "de": (
            "Regel {a} gilt in dieser FIRST-Tabelle nie: frühere Regeln ({b}) decken "
            "bereits jeden ihrer Fälle ab."
        ),
        "fr": (
            "La règle {a} ne s'applique jamais dans cette table FIRST : des règles "
            "antérieures ({b}) couvrent déjà tous ses cas."
        ),
    },
    "gat": {
        "en": "No rule applies to {n} combination(s) of input values, for example {voorbeeld}.",
        "nl": (
            "Voor {n} combinatie(s) van invoerwaarden geldt geen regel, bijvoorbeeld {voorbeeld}."
        ),
        "de": (
            "Für {n} Kombination(en) von Eingabewerten gilt keine Regel, zum Beispiel {voorbeeld}."
        ),
        "fr": (
            "Aucune règle ne s'applique à {n} combinaison(s) de valeurs d'entrée, par "
            "exemple {voorbeeld}."
        ),
    },
    "te-groot": {
        "en": (
            "Gaps and rules that never apply were not searched: more than {n} "
            "combinations of input values."
        ),
        "nl": (
            "Niet gezocht naar gaten en regels die nooit gelden: meer dan {n} combinaties"
            " van invoerwaarden."
        ),
        "de": (
            "Nicht nach Lücken und nie geltenden Regeln gesucht: mehr als {n} "
            "Kombinationen von Eingabewerten."
        ),
        "fr": (
            "Lacunes et règles jamais applicables non recherchées : plus de {n} "
            "combinaisons de valeurs d'entrée."
        ),
    },
    "buiten-invoer": {
        "en": (
            "Input entry {cel} of rule {a} ({kolom}) is not a subset of the input values {waarden}."
        ),
        "nl": (
            "Invoercel {cel} van regel {a} ({kolom}) valt niet binnen de invoerwaarden {waarden}."
        ),
        "de": (
            "Eingabeeintrag {cel} der Regel {a} ({kolom}) ist keine Teilmenge der "
            "Eingabewerte {waarden}."
        ),
        "fr": (
            "L'entrée {cel} de la règle {a} ({kolom}) n'est pas incluse dans les valeurs "
            "d'entrée {waarden}."
        ),
    },
    "buiten-uitvoer": {
        "en": "Output entry {cel} of rule {a} ({kolom}) is not one of the output values {waarden}.",
        "nl": (
            "Uitvoercel {cel} van regel {a} ({kolom}) hoort niet bij de uitvoerwaarden {waarden}."
        ),
        "de": (
            "Ausgabeeintrag {cel} der Regel {a} ({kolom}) gehört nicht zu den "
            "Ausgabewerten {waarden}."
        ),
        "fr": (
            "La sortie {cel} de la règle {a} ({kolom}) ne fait pas partie des valeurs de "
            "sortie {waarden}."
        ),
    },
    "standaard-buiten": {
        "en": "The default output value {cel} ({kolom}) is not one of the output values {waarden}.",
        "nl": "De standaarduitkomst {cel} ({kolom}) hoort niet bij de uitvoerwaarden {waarden}.",
        "de": (
            "Der Standardausgabewert {cel} ({kolom}) gehört nicht zu den Ausgabewerten {waarden}."
        ),
        "fr": (
            "La valeur de sortie par défaut {cel} ({kolom}) ne fait pas partie des "
            "valeurs de sortie {waarden}."
        ),
    },
    "standaard-volledig": {
        "en": (
            "This table is complete and still specifies a default output value; a "
            "complete decision table SHALL NOT."
        ),
        "nl": (
            "Deze tabel is volledig en heeft toch een standaarduitkomst; dat mag niet bij"
            " een volledige beslistabel."
        ),
        "de": (
            "Diese Tabelle ist vollständig und gibt dennoch einen Standardausgabewert an;"
            " eine vollständige Tabelle SHALL NOT."
        ),
        "fr": (
            "Cette table est complète et indique pourtant une valeur de sortie par défaut"
            " ; une table complète SHALL NOT."
        ),
    },
    "niet-bepaald": {
        "en": (
            "{n} cell(s) are not S-FEEL simple unary tests and were not decided (first: "
            "{cel}: {reden}). Overlap and gaps involving them are not reported."
        ),
        "nl": (
            "{n} cel(len) zijn geen eenvoudige S-FEEL-toetsen en zijn niet bepaald "
            "(eerste: {cel}: {reden}). Overlap en gaten waar ze bij horen, worden niet "
            "gemeld."
        ),
        "de": (
            "{n} Zelle(n) sind keine einfachen S-FEEL-Tests und wurden nicht entschieden "
            "(erste: {cel}: {reden}). Überlappungen und Lücken mit ihnen werden nicht "
            "gemeldet."
        ),
        "fr": (
            "{n} cellule(s) ne sont pas des tests unaires simples S-FEEL et n'ont pas été"
            " décidées (première : {cel} : {reden}). Chevauchements et lacunes les "
            "concernant ne sont pas signalés."
        ),
    },
}


@dataclass
class Bevinding:
    focus: URIRef | BNode
    ernst: str  # Violation, Warning, Info
    controle: URIRef
    soort: str
    params: dict[str, Any] = field(default_factory=dict)
    waarde: URIRef | BNode | None = None

    def bericht(self, taal: str = "en") -> str:
        return BERICHT[self.soort].get(taal, BERICHT[self.soort]["en"]).format(**self.params)


def _tekst(g: Graph, node: Any) -> str | None:
    if node is None:
        return None
    t = g.value(node, DMN.text)
    return str(t) if t is not None else None


def _geordend(g: Graph, eigenaar: Any, p: URIRef) -> list[Any]:
    items = list(g.objects(eigenaar, p))
    return sorted(items, key=lambda n: int(g.value(n, DMN.position) or 0))


def _type_ref(g: Graph, ref: str | None) -> tuple[str, str | None]:
    """typeRef -> (domein, toegestane waarden als tekst). Volgt een ItemDefinition."""
    gezien: set[str] = set()
    toegestaan: str | None = None
    while ref and ref not in gezien:
        gezien.add(ref)
        d = sfeel.domein_van(ref)
        if d:
            return d, toegestaan
        item = next(
            (
                s
                for s in g.subjects(DMN.name, Literal(ref))
                if (s, RDF.type, DMN.ItemDefinition) in g
            ),
            None,
        )
        if item is None:
            return "", toegestaan
        av = g.value(item, DMN.allowedValues) or g.value(item, DMN.typeConstraint)
        toegestaan = toegestaan or _tekst(g, av)
        nieuw = g.value(item, DMN.typeRef)
        ref = str(nieuw) if nieuw is not None else None
    return "", toegestaan


@dataclass
class Kolom:
    naam: str
    domein: str
    universum: sfeel.Verz
    waarden_tekst: str | None


def _kolom(g: Graph, clause: Any, soort: str, i: int, standaard: str = "") -> Kolom:
    if soort == "in":
        expr = g.value(clause, DMN.inputExpression)
        naam = _tekst(g, expr) or str(g.value(clause, DMN.label) or f"input {i}")
        ref = g.value(expr, DMN.typeRef) if expr is not None else None
        waarden = _tekst(g, g.value(clause, DMN.inputValues))
    else:
        naam = str(
            g.value(clause, DMN.name) or g.value(clause, DMN.label) or standaard or f"output {i}"
        )
        ref = g.value(clause, DMN.typeRef)
        waarden = _tekst(g, g.value(clause, DMN.outputValues))
    domein, item_waarden = _type_ref(g, str(ref) if ref is not None else None)
    waarden = waarden or item_waarden
    universum = sfeel.Verz.overal(domein)
    if waarden:
        try:
            universum = sfeel.lees(waarden, domein)
            domein = domein or universum.domein
        except sfeel.NietBeslisbaar:
            waarden = None
    return Kolom(naam, domein, universum, waarden)


def _atomen(cellen: list[sfeel.Verz], uni: sfeel.Verz, domein: str) -> list[sfeel.Verz]:
    """Elementary pieces of a column: every cell is a union of them."""
    if domein in (sfeel.GETAL, sfeel.DATUM):
        punten = sorted(
            {
                p
                for v in [*cellen, uni]
                if not v.alles
                for iv in v.intervallen
                for p in (iv.lo, iv.hi)
                if p is not None
            }
        )
        stukken: list[sfeel.Verz] = []
        vorige = None
        for p in punten:
            stukken.append(sfeel.Verz(domein, (sfeel.Interval(vorige, False, p, False),)))
            stukken.append(sfeel.Verz(domein, (sfeel.Interval(p, True, p, True),)))
            vorige = p
        stukken.append(sfeel.Verz(domein, (sfeel.Interval(vorige, False, None, False),)))
    elif domein == sfeel.BOOL:
        stukken = [
            sfeel.Verz(domein, waarden=frozenset({True})),
            sfeel.Verz(domein, waarden=frozenset({False})),
        ]
    elif domein == sfeel.TEKST:
        genoemd = frozenset(w for v in [*cellen, uni] if not v.alles for w in v.waarden)
        stukken = [sfeel.Verz(domein, waarden=frozenset({w})) for w in sorted(genoemd)]
        # "Elke andere tekst" telt alleen mee als de kolom invoerwaarden heeft die
        # dat toelaten (not(...)). Zonder invoerwaarden zijn de verwachte waarden
        # (8.2.4) de genoemde: anders is elke teksttabel onvolledig.
        if not uni.alles:
            stukken.append(sfeel.Verz(domein, waarden=genoemd, co=True))
    else:
        stukken = [sfeel.Verz.overal(domein)]
    return [s2 for s2 in (s.snij(uni) for s in stukken) if not s2.leeg()]


def _schrijf_combinatie(
    kolommen: list[Kolom], atomen: list[list[sfeel.Verz]], combi: tuple[int, ...]
) -> str:
    delen = []
    for k, a in zip(kolommen, combi, strict=True):
        tekst = atomen[kolommen.index(k)][a].schrijf()
        if tekst != "-":
            delen.append(f"{k.naam}: {tekst}")
    return "; ".join(delen) or "(any input)"


def _tabel(g: Graph, tabel: Any) -> list[Bevinding]:
    uit: list[Bevinding] = []
    hp_node = g.value(tabel, DMN.hitPolicy)
    hp = str(g.value(hp_node, DMN.xmlValue) or "UNIQUE") if hp_node is not None else "UNIQUE"
    ins = [_kolom(g, c, "in", i) for i, c in enumerate(_geordend(g, tabel, DMN.input), 1)]
    # Een enkele uitvoerkolom heeft geen naam: die van de beslissing (of haar variabele).
    eigenaar = next(iter(g.subjects(DMN.decisionLogic, tabel)), None)
    standaard = str(g.value(eigenaar, DMN.name) or "") if eigenaar is not None else ""
    outs = [
        _kolom(g, c, "out", i, standaard) for i, c in enumerate(_geordend(g, tabel, DMN.output), 1)
    ]
    regels = _geordend(g, tabel, DMN.rule)
    nr = {r: int(g.value(r, DMN.position) or i) for i, r in enumerate(regels, 1)}
    cellen: list[list[sfeel.Verz | None]] = []
    onbepaald: list[tuple[str, str]] = []
    for r in regels:
        rij: list[sfeel.Verz | None] = []
        entries = _geordend(g, r, DMN.inputEntry)
        for ci, k in enumerate(ins):
            tekst = _tekst(g, entries[ci]) if ci < len(entries) else "-"
            try:
                v = sfeel.lees(tekst, k.domein).snij(k.universum)
                rij.append(v)
                ruw = sfeel.lees(tekst, k.domein)
                if k.waarden_tekst and not ruw.alles and not ruw.deel_van(k.universum, k.domein):
                    uit.append(
                        Bevinding(
                            tabel,
                            "Warning",
                            DMNSH.EntryOutsideInputValues,
                            "buiten-invoer",
                            {"cel": tekst, "a": nr[r], "kolom": k.naam, "waarden": k.waarden_tekst},
                            r,
                        )
                    )
            except sfeel.NietBeslisbaar as e:
                rij.append(None)
                onbepaald.append((tekst or "", str(e)))
        cellen.append(rij)
        uitkomsten = _geordend(g, r, DMN.outputEntry)
        for oi, k in enumerate(outs):
            if not k.waarden_tekst or oi >= len(uitkomsten):
                continue
            tekst = _tekst(g, uitkomsten[oi]) or ""
            w = sfeel.lees_waarde(tekst)
            if w is not None and not k.universum.bevat(w):
                uit.append(
                    Bevinding(
                        tabel,
                        "Violation",
                        DMNSH.OutputOutsideOutputValues,
                        "buiten-uitvoer",
                        {"cel": tekst, "a": nr[r], "kolom": k.naam, "waarden": k.waarden_tekst},
                        r,
                    )
                )
    for clause, k in zip(_geordend(g, tabel, DMN.output), outs, strict=True):
        std = _tekst(g, g.value(clause, DMN.defaultOutputEntry))
        if std and k.waarden_tekst:
            w = sfeel.lees_waarde(std)
            if w is not None and not k.universum.bevat(w):
                uit.append(
                    Bevinding(
                        tabel,
                        "Violation",
                        DMNSH.DefaultOutputValue,
                        "standaard-buiten",
                        {"cel": standaard, "kolom": k.naam, "waarden": k.waarden_tekst},
                    )
                )
    if onbepaald:
        uit.append(
            Bevinding(
                tabel,
                "Info",
                DMNSH.NotDecided,
                "niet-bepaald",
                {"n": len(onbepaald), "cel": onbepaald[0][0], "reden": onbepaald[0][1]},
            )
        )

    def uitkomst(r: Any) -> tuple[Any, ...] | None:
        ws = tuple(sfeel.lees_waarde(_tekst(g, e)) for e in _geordend(g, r, DMN.outputEntry))
        return None if any(w is None for w in ws) else ws

    #: per regel de cellen, of None als er een cel bij zit die niet bepaald is
    bepaald: list[list[sfeel.Verz] | None] = [
        None if any(x is None for x in rij) else [x for x in rij if x is not None] for rij in cellen
    ]
    # Overlap, per paar regels met alleen bepaalde cellen
    for (i, ri), (j, rj) in itertools.combinations(list(enumerate(regels)), 2):
        ca, cb = bepaald[i], bepaald[j]
        if ca is None or cb is None:
            continue
        doorsnede = [x.snij(y) for x, y in zip(ca, cb, strict=True)]
        if any(d.leeg() for d in doorsnede):
            continue
        voorbeeld = (
            "; ".join(
                f"{k.naam}: {d.schrijf()}"
                for k, d in zip(ins, doorsnede, strict=True)
                if d.schrijf() != "-"
            )
            or "every input"
        )
        if hp == "UNIQUE":
            uit.append(
                Bevinding(
                    tabel,
                    "Violation",
                    DMNSH.UniqueOverlap,
                    "overlap",
                    {"a": nr[ri], "b": nr[rj], "voorbeeld": voorbeeld},
                    rj,
                )
            )
        elif hp == "ANY":
            ua, ub = uitkomst(ri), uitkomst(rj)
            if ua is not None and ub is not None and ua != ub:
                uit.append(
                    Bevinding(
                        tabel,
                        "Violation",
                        DMNSH.AnyConflict,
                        "any",
                        {"a": nr[ri], "b": nr[rj], "voorbeeld": voorbeeld},
                        rj,
                    )
                )
    for i, r in enumerate(regels):
        rij_i = bepaald[i]
        if rij_i is not None and any(x.leeg() for x in rij_i):
            uit.append(Bevinding(tabel, "Warning", DMNSH.MaskedRule, "leeg", {"a": nr[r]}, r))
    # Gaten en gemaskeerde regels: alleen als elke cel bepaald is
    vast = [rij for rij in bepaald if rij is not None]
    if onbepaald or not ins or len(vast) != len(regels):
        return uit
    atomen = [_atomen([rij[c] for rij in vast], k.universum, k.domein) for c, k in enumerate(ins)]
    totaal = 1
    for stukken in atomen:
        totaal *= max(1, len(stukken))
    if totaal > GRENS:
        uit.append(Bevinding(tabel, "Info", DMNSH.Gap, "te-groot", {"n": GRENS}))
        return uit
    #: per kolom, per atoom: bitmasker van de regels die het atoom bevatten
    maskers = [
        [
            sum(1 << ri for ri, rij in enumerate(vast) if at.deel_van(rij[c], ins[c].domein))
            for at in atomen[c]
        ]
        for c in range(len(ins))
    ]
    gaten: list[tuple[int, ...]] = []
    for combi in itertools.product(*[range(len(stukken)) for stukken in atomen]):
        m = (1 << len(regels)) - 1
        for c, ai in enumerate(combi):
            m &= maskers[c][ai]
            if not m:
                break
        if not m:
            gaten.append(combi)
    if gaten:
        uit.append(
            Bevinding(
                tabel,
                "Info",
                DMNSH.Gap,
                "gat",
                {"n": len(gaten), "voorbeeld": _schrijf_combinatie(ins, atomen, gaten[0])},
            )
        )
    elif any(
        _tekst(g, g.value(c, DMN.defaultOutputEntry)) for c in _geordend(g, tabel, DMN.output)
    ):
        uit.append(
            Bevinding(tabel, "Violation", DMNSH.DefaultOutputValue, "standaard-volledig", {})
        )
    if hp == "FIRST":
        for i, r in enumerate(regels):
            eerder = (1 << i) - 1
            if not eerder or any(x.leeg() for x in vast[i]):
                continue
            binnen = [
                [ai for ai in range(len(atomen[c])) if maskers[c][ai] >> i & 1]
                for c in range(len(ins))
            ]
            dekkers: int = 0
            gemaskeerd = True
            for combi in itertools.product(*binnen):
                m = eerder
                for c, ai in enumerate(combi):
                    m &= maskers[c][ai]
                if not m:
                    gemaskeerd = False
                    break
                dekkers |= m
            if gemaskeerd:
                lijst = ", ".join(str(nr[regels[k]]) for k in range(i) if dekkers >> k & 1)
                uit.append(
                    Bevinding(
                        tabel,
                        "Warning",
                        DMNSH.MaskedRule,
                        "gemaskeerd",
                        {"a": nr[r], "b": lijst},
                        r,
                    )
                )
    return uit


def analyseer(g: Graph) -> list[Bevinding]:
    uit: list[Bevinding] = []
    for tabel in sorted(g.subjects(RDF.type, DMN.DecisionTable), key=str):
        uit.extend(_tabel(g, tabel))
    return uit


def als_rapport(bevindingen: Iterable[Bevinding], talen: Iterable[str] = TALEN) -> Graph:
    """The findings as a SHACL validation report, so SHACL and computed results read alike."""
    r = Graph()
    r.bind("sh", SH)
    r.bind("dmnsh", DMNSH)
    rapport = BNode()
    r.add((rapport, RDF.type, SH.ValidationReport))
    lijst = list(bevindingen)
    r.add(
        (
            rapport,
            SH.conforms,
            Literal(not any(b.ernst == "Violation" for b in lijst), datatype=XSD.boolean),
        )
    )
    for b in lijst:
        res = BNode()
        r.add((rapport, SH.result, res))
        r.add((res, RDF.type, SH.ValidationResult))
        r.add((res, SH.focusNode, b.focus))
        r.add((res, SH.resultSeverity, SH[b.ernst]))
        r.add((res, SH.sourceShape, b.controle))
        r.add((res, SH.sourceConstraintComponent, DMNSH.ComputedConstraintComponent))
        if b.waarde is not None:
            r.add((res, SH.value, b.waarde))
        for t in talen:
            r.add((res, SH.resultMessage, Literal(b.bericht(t), lang=t)))
    return r
