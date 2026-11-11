"""Små formateringshjelpere for norsk tekst."""

from __future__ import annotations

from datetime import date

_MONTHS = [
    "jan.", "feb.", "mars", "apr.", "mai", "juni",
    "juli", "aug.", "sep.", "okt.", "nov.", "des.",
]


def nb_date(d: date) -> str:
    """8. des. 2026"""
    return f"{d.day}. {_MONTHS[d.month - 1]} {d.year}"


def nb_span(start: date, end: date) -> str:
    """8.–9. des. 2026 (eller 31. jan.–1. feb. 2027 over månedsskifte)."""
    if start.year != end.year:
        return f"{nb_date(start)}–{nb_date(end)}"
    if start.month != end.month:
        return f"{start.day}. {_MONTHS[start.month - 1]}–{end.day}. {_MONTHS[end.month - 1]} {end.year}"
    return f"{start.day}.–{end.day}. {_MONTHS[end.month - 1]} {end.year}"
