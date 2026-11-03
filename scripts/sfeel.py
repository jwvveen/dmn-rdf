"""S-FEEL simple unary tests as sets of values: the part of DMN that can be decided.

DMN 1.6 clause 9.2 defines the simple unary tests of a decision table cell:

    -                       any value
    < 10, <= 10, > 10, >= 10
    [1..10], (1..10], ]1..10[, ...
    "A", 42, true, date("2026-01-01")
    "A", "B", < 0           a list: the union
    not("A", "B")           the complement

This module turns such a cell into a set (``Verz``) over one of four
domains: number (decimal), string, boolean and date. Sets can be intersected,
joined, complemented and compared, which is all an overlap or completeness
check needs.

Everything else raises ``NietBeslisbaar`` with a reason, and the caller
reports it as "not decided". That covers names (``< limit``: its value is not known at
design time), time and duration literals, and full FEEL (functions, paths,
arithmetic). The point is that the checker never gives a false verdict: it
decides what S-FEEL can decide and says how much it left alone.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

#: Domains. A column's domain follows its typeRef; "" means: take it from the cell.
GETAL, TEKST, BOOL, DATUM = "number", "string", "boolean", "date"
_TYPEREF = {
    "number": GETAL,
    "string": TEKST,
    "boolean": BOOL,
    "date": DATUM,
    "feel:number": GETAL,
    "feel:string": TEKST,
    "feel:boolean": BOOL,
    "feel:date": DATUM,
    "integer": GETAL,
    "decimal": GETAL,
    "double": GETAL,
    "long": GETAL,
    "int": GETAL,
}


def domein_van(type_ref: str | None) -> str:
    """Domain of a column from its typeRef; '' when unknown or not an S-FEEL base type."""
    return _TYPEREF.get((type_ref or "").strip().lower(), "")


@dataclass(frozen=True)
class Interval:
    """Interval over an ordered domain; None as a bound means unbounded."""

    lo: Any
    lo_in: bool
    hi: Any
    hi_in: bool

    def leeg(self) -> bool:
        if self.lo is None or self.hi is None:
            return False
        return self.lo > self.hi or (self.lo == self.hi and not (self.lo_in and self.hi_in))

    def bevat(self, w: Any) -> bool:
        if self.lo is not None and (w < self.lo or (w == self.lo and not self.lo_in)):
            return False
        return not (self.hi is not None and (w > self.hi or (w == self.hi and not self.hi_in)))


def _snij_iv(a: Interval, b: Interval) -> Interval:
    if a.lo is None:
        lo, lo_in = b.lo, b.lo_in
    elif b.lo is None or a.lo > b.lo:
        lo, lo_in = a.lo, a.lo_in
    elif b.lo > a.lo:
        lo, lo_in = b.lo, b.lo_in
    else:
        lo, lo_in = a.lo, a.lo_in and b.lo_in
    if a.hi is None:
        hi, hi_in = b.hi, b.hi_in
    elif b.hi is None or a.hi < b.hi:
        hi, hi_in = a.hi, a.hi_in
    elif b.hi < a.hi:
        hi, hi_in = b.hi, b.hi_in
    else:
        hi, hi_in = a.hi, a.hi_in and b.hi_in
    return Interval(lo, lo_in, hi, hi_in)


def _normaliseer(delen: list[Interval]) -> tuple[Interval, ...]:
    """Sorted, disjoint, touching intervals merged."""
    rij = sorted(
        (iv for iv in delen if not iv.leeg()),
        key=lambda iv: (iv.lo is not None, iv.lo if iv.lo is not None else 0, not iv.lo_in),
    )
    uit: list[Interval] = []
    for iv in rij:
        if uit:
            v = uit[-1]
            raakt = (
                v.hi is None
                or iv.lo is None
                or iv.lo < v.hi
                or (iv.lo == v.hi and (v.hi_in or iv.lo_in))
            )
            if raakt:
                if v.hi is None or (
                    iv.hi is not None and (iv.hi < v.hi or (iv.hi == v.hi and v.hi_in))
                ):
                    continue
                uit[-1] = Interval(
                    v.lo, v.lo_in, iv.hi, iv.hi_in if iv.hi != v.hi else (iv.hi_in or v.hi_in)
                )
                continue
        uit.append(iv)
    return tuple(uit)


def _complement_iv(delen: tuple[Interval, ...]) -> tuple[Interval, ...]:
    uit: list[Interval] = []
    lo, lo_in = None, False
    for iv in delen:
        if iv.lo is not None:
            uit.append(Interval(lo, lo_in, iv.lo, not iv.lo_in))
        if iv.hi is None:
            return _normaliseer(uit)
        lo, lo_in = iv.hi, not iv.hi_in
    uit.append(Interval(lo, lo_in, None, False))
    return _normaliseer(uit)


@dataclass(frozen=True)
class Verz:
    """A set of values in one domain.

    Ordered domains (number, date) hold intervals. String holds a finite set,
    or the complement of one (``co``). Boolean holds a subset of {True, False}.
    ``alles`` is the '-' cell: any value, of any domain.
    """

    domein: str = ""
    intervallen: tuple[Interval, ...] = ()
    waarden: frozenset[Any] = field(default_factory=frozenset)
    co: bool = False
    alles: bool = False

    @staticmethod
    def overal(domein: str = "") -> Verz:
        return Verz(domein, alles=True)

    def _uitgeschreven(self, domein: str) -> Verz:
        """'-' written out in a domain, for set algebra."""
        if not self.alles:
            return self
        if domein in (GETAL, DATUM):
            return Verz(domein, (Interval(None, False, None, False),))
        if domein == BOOL:
            return Verz(domein, waarden=frozenset({True, False}))
        return Verz(domein, waarden=frozenset(), co=True)

    def leeg(self) -> bool:
        if self.alles:
            return False
        if self.domein in (GETAL, DATUM):
            return not self.intervallen
        return not self.co and not self.waarden

    def bevat(self, w: Any) -> bool:
        if self.alles:
            return True
        if self.domein in (GETAL, DATUM):
            return any(iv.bevat(w) for iv in self.intervallen)
        return (w in self.waarden) != self.co

    def complement(self) -> Verz:
        if self.alles:
            return Verz(self.domein, (), frozenset(), False, False) if self.domein else Verz("", ())
        if self.domein in (GETAL, DATUM):
            return Verz(self.domein, _complement_iv(self.intervallen))
        if self.domein == BOOL:
            return Verz(BOOL, waarden=frozenset({True, False}) - self.waarden)
        return Verz(self.domein, waarden=self.waarden, co=not self.co)

    def snij(self, ander: Verz) -> Verz:
        if self.alles:
            return ander
        if ander.alles:
            return self
        if self.domein != ander.domein:
            return Verz(self.domein or ander.domein)  # verschillende domeinen: niets gemeen
        if self.domein in (GETAL, DATUM):
            delen = [_snij_iv(a, b) for a in self.intervallen for b in ander.intervallen]
            return Verz(self.domein, _normaliseer(delen))
        if self.domein == BOOL:
            return Verz(BOOL, waarden=self.waarden & ander.waarden)
        if not self.co and not ander.co:
            return Verz(self.domein, waarden=self.waarden & ander.waarden)
        if self.co and ander.co:
            return Verz(self.domein, waarden=self.waarden | ander.waarden, co=True)
        eind, uitsluit = (ander, self) if self.co else (self, ander)
        return Verz(self.domein, waarden=eind.waarden - uitsluit.waarden)

    def verenig(self, ander: Verz) -> Verz:
        if self.alles or ander.alles:
            return Verz.overal(self.domein or ander.domein)
        d = self.domein or ander.domein
        if self.domein and ander.domein and self.domein != ander.domein:
            raise ValueError("mixed domains")
        return (
            self._uitgeschreven(d)
            .complement()
            .snij(ander._uitgeschreven(d).complement())
            .complement()
            if d not in (GETAL, DATUM)
            else Verz(d, _normaliseer([*self.intervallen, *ander.intervallen]))
        )

    def deel_van(self, ander: Verz, domein: str = "") -> bool:
        """self ⊆ ander."""
        if ander.alles:
            return True
        d = self.domein or ander.domein or domein
        return self._uitgeschreven(d).snij(ander.complement()).leeg()

    def schrijf(self) -> str:
        """Back to S-FEEL, for messages."""
        if self.alles:
            return "-"
        if self.domein in (GETAL, DATUM):
            return ", ".join(_schrijf_iv(iv, self.domein) for iv in self.intervallen) or "(none)"
        tekst = ", ".join(sorted(_schrijf_w(w, self.domein) for w in self.waarden))
        if self.co:
            return f"not({tekst})" if tekst else "-"
        return tekst or "(none)"


def _schrijf_w(w: Any, domein: str) -> str:
    if domein == TEKST:
        return '"' + str(w).replace('"', '\\"') + '"'
    if domein == BOOL:
        return "true" if w else "false"
    if domein == DATUM:
        return f'date("{w.isoformat()}")'
    return format(w.normalize(), "f") if isinstance(w, Decimal) else str(w)


def _schrijf_iv(iv: Interval, domein: str) -> str:
    if iv.lo is not None and iv.lo == iv.hi:
        return _schrijf_w(iv.lo, domein)
    if iv.lo is None and iv.hi is None:
        return "-"
    if iv.lo is None:
        return ("<= " if iv.hi_in else "< ") + _schrijf_w(iv.hi, domein)
    if iv.hi is None:
        return (">= " if iv.lo_in else "> ") + _schrijf_w(iv.lo, domein)
    return (
        ("[" if iv.lo_in else "(")
        + _schrijf_w(iv.lo, domein)
        + ".."
        + _schrijf_w(iv.hi, domein)
        + ("]" if iv.hi_in else ")")
    )


class NietBeslisbaar(Exception):  # noqa: N818 (Nederlandse naam, zoals FeelFout in SemanticXL)
    """The cell is not an S-FEEL simple unary test over a known domain."""


_TOKEN = re.compile(
    r"""\s*(?:
    (?P<str>"(?:[^"\\]|\\.)*") |
    (?P<num>-?(?:\d+(?:\.\d+)?|\.\d+)) |
    (?P<op><=|>=|!=|\.\.|[<>=(),\[\]-]) |
    (?P<naam>[A-Za-z_?][\w.?]*)
)""",
    re.VERBOSE,
)


def _tokens(tekst: str) -> list[tuple[str, str]]:
    uit, pos = [], 0
    while pos < len(tekst):
        if tekst[pos:].strip() == "":
            break
        m = _TOKEN.match(tekst, pos)
        if not m or m.end() == pos:
            raise NietBeslisbaar(
                f"unexpected text at position {pos + 1}: {tekst[pos : pos + 12]!r}"
            )
        soort = m.lastgroup or ""
        uit.append((soort, m.group(soort)))
        pos = m.end()
    return uit


def _ontsnap(s: str) -> str:
    return re.sub(
        r"\\(.)", lambda m: {"n": "\n", "t": "\t", "r": "\r"}.get(m.group(1), m.group(1)), s[1:-1]
    )


class _Lezer:
    def __init__(self, tekst: str) -> None:
        self.t = _tokens(tekst)
        self.i = 0

    def kijk(self, k: int = 0) -> tuple[str, str]:
        return self.t[self.i + k] if self.i + k < len(self.t) else ("", "")

    def neem(self, waarde: str | None = None) -> tuple[str, str]:
        tok = self.kijk()
        if waarde is not None and tok[1] != waarde:
            raise NietBeslisbaar(f"expected {waarde!r}, found {tok[1] or 'end'!r}")
        self.i += 1
        return tok

    def waarde(self) -> tuple[str, Any]:
        soort, w = self.neem()
        if soort == "str":
            return TEKST, _ontsnap(w)
        if soort == "num":
            try:
                return GETAL, Decimal(w)
            except InvalidOperation as e:
                raise NietBeslisbaar(f"not a number: {w}") from e
        if soort == "naam" and w in ("true", "false"):
            return BOOL, w == "true"
        if (
            soort == "naam"
            and w in ("date", "time", "duration", "date and time")
            and self.kijk()[1] == "("
        ):
            self.neem("(")
            s_soort, s = self.neem()
            self.neem(")")
            if w != "date" or s_soort != "str":
                raise NietBeslisbaar(f"{w}(...) is not decided (only date literals are)")
            try:
                return DATUM, _dt.date.fromisoformat(_ontsnap(s))
            except ValueError as e:
                raise NietBeslisbaar(f"not a date: {s}") from e
        if soort == "naam" and self.kijk()[1] == "(":
            raise NietBeslisbaar(f"function call {w}(...): full FEEL, not a simple unary test")
        if soort == "naam":
            raise NietBeslisbaar(f"name {w!r}: its value is not known at design time")
        raise NietBeslisbaar(f"expected a value, found {w or 'end'!r}")

    def positief(self) -> tuple[str, Verz]:
        _, w = self.kijk()
        if w in ("<", "<=", ">", ">="):
            self.neem()
            d, v = self.waarde()
            if d not in (GETAL, DATUM, TEKST):
                raise NietBeslisbaar(f"{w} on a {d}")
            if d == TEKST:
                raise NietBeslisbaar("string comparison ranges are not decided")
            iv = {
                "<": Interval(None, False, v, False),
                "<=": Interval(None, False, v, True),
                ">": Interval(v, False, None, False),
                ">=": Interval(v, True, None, False),
            }[w]
            return d, Verz(d, (iv,))
        if w in ("[", "(", "]"):
            self.neem()
            d1, a = self.waarde()
            self.neem("..")
            d2, b = self.waarde()
            sluit = self.neem()[1]
            if sluit not in ("]", ")", "["):
                raise NietBeslisbaar("interval without an end")
            if d1 != d2 or d1 not in (GETAL, DATUM):
                raise NietBeslisbaar("interval over mixed or unordered values")
            return d1, Verz(d1, _normaliseer([Interval(a, w == "[", b, sluit == "]")]))
        d, v = self.waarde()
        if d in (GETAL, DATUM):
            return d, Verz(d, (Interval(v, True, v, True),))
        return d, Verz(d, waarden=frozenset({v}))


def lees(tekst: str | None, domein: str = "") -> Verz:
    """Parse a simple unary tests cell into a set. Raises NietBeslisbaar.

    ``domein`` is the column's domain, when known; a cell of another domain
    is then not decided (a type error is not this checker's to report).
    """
    t = (tekst or "").strip()
    if t in ("", "-"):
        return Verz.overal(domein)
    lz = _Lezer(t)
    negatie = False
    if lz.kijk() == ("naam", "not") and lz.kijk(1)[1] == "(":
        lz.neem()
        lz.neem("(")
        negatie = True
    delen: list[tuple[str, Verz]] = [lz.positief()]
    while lz.kijk()[1] == ",":
        lz.neem()
        delen.append(lz.positief())
    if negatie:
        lz.neem(")")
    if lz.kijk()[0]:
        raise NietBeslisbaar(f"unexpected {lz.kijk()[1]!r}: not a simple unary test")
    domeinen = {d for d, _ in delen}
    if len(domeinen) > 1:
        raise NietBeslisbaar("values of more than one type in one cell")
    d = domeinen.pop()
    if domein and d != domein:
        raise NietBeslisbaar(f"a {d} in a {domein} column")
    verz = delen[0][1]
    for _, v in delen[1:]:
        verz = verz.verenig(v)
    return verz.complement() if negatie else verz


def lees_waarde(tekst: str | None) -> Any:
    """An output entry as a plain value, for comparing outputs (ANY). None if not a literal."""
    try:
        lz = _Lezer((tekst or "").strip())
        _, w = lz.waarde()
        return None if lz.kijk()[0] else w
    except NietBeslisbaar:
        return None
