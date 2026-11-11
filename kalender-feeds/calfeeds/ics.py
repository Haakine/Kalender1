"""Minimal, streng iCalendar-skriver (RFC 5545) uten eksterne avhengigheter.

Alt som havner i filen går gjennom escape_text(), slik at tekst fra eksterne
kilder ikke kan injisere egne iCalendar-linjer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CRLF = "\r\n"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class Event:
    uid: str
    start: datetime  # må være tidssone-bevisst
    duration: timedelta
    summary: str
    description: str = ""
    url: str = ""


def escape_text(text: str) -> str:
    """Escape verdi av typen TEXT. Fjerner kontrolltegn og normaliserer linjeskift."""
    text = _CONTROL.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold(line: str) -> str:
    """Bryt linjer ved 75 oktetter. Deler aldri et UTF-8-tegn midt i."""
    out: list[str] = []
    current = ""
    size = 0
    for ch in line:
        width = len(ch.encode("utf-8"))
        if size + width > 75:
            out.append(current)
            current = " " + ch  # fortsettelseslinjen starter med ett mellomrom
            size = 1 + width
        else:
            current += ch
            size += width
    out.append(current)
    return CRLF.join(out)


def format_utc(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("Tidspunkt må ha tidssone")
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _event_lines(event: Event, now: datetime) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{escape_text(event.uid)}",
        f"DTSTAMP:{format_utc(now)}",
        f"DTSTART:{format_utc(event.start)}",
        f"DTEND:{format_utc(event.start + event.duration)}",
        f"SUMMARY:{escape_text(event.summary)}",
    ]
    if event.description:
        lines.append(f"DESCRIPTION:{escape_text(event.description)}")
    if event.url:
        if not event.url.startswith("https://") or re.search(r"\s", event.url):
            raise ValueError(f"Ugyldig URL: {event.url!r}")
        lines.append(f"URL:{event.url}")
    # TRANSPARENT: hendelsene skal ikke markere deg som opptatt i kalenderen.
    lines += ["TRANSP:TRANSPARENT", "STATUS:CONFIRMED", "END:VEVENT"]
    return lines


def render_calendar(
    *,
    name: str,
    description: str,
    events: list[Event],
    color: str,
    now: datetime,
    refresh_hours: int = 12,
    prodid: str = "-//kalender-feeds//NO",
) -> str:
    uids = [e.uid for e in events]
    if len(uids) != len(set(uids)):
        raise ValueError("Duplikate UID-er i kalenderen")
    if not _HEX_COLOR.match(color):
        raise ValueError(f"Ugyldig farge: {color!r}")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{prodid}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"NAME:{escape_text(name)}",
        f"X-WR-CALNAME:{escape_text(name)}",
        f"X-WR-CALDESC:{escape_text(description)}",
        f"X-APPLE-CALENDAR-COLOR:{color}",
        f"REFRESH-INTERVAL;VALUE=DURATION:PT{refresh_hours}H",
        f"X-PUBLISHED-TTL:PT{refresh_hours}H",
    ]
    for event in sorted(events, key=lambda e: (e.start, e.uid)):
        lines += _event_lines(event, now)
    lines.append("END:VCALENDAR")
    return CRLF.join(fold(line) for line in lines) + CRLF
