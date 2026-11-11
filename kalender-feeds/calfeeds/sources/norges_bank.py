"""Norges Bank: rentemøter.

Datoene lagres i data/norges_bank.json. Under bygging i GitHub Actions
oppdateres de fra Norges Banks egen kalenderside, hvis siden kan hentes.
Lenkene på siden inneholder datoen (…/rentemoter/27-01-21/), så vi trenger
ikke å tolke HTML-strukturen.
"""

from __future__ import annotations

import re
import urllib.request
from datetime import date, datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from ..fmt import nb_date
from ..ics import Event

TZ = ZoneInfo("Europe/Oslo")
LIST_URL = "https://www.norges-bank.no/aktuelt/kalender/rentemoter/"
# Pengepolitisk rapport kommer på møtene i mars, juni, september og desember.
PPR_MONTHS = {3, 6, 9, 12}
# Datoen i lenkene har tosifret år og måned, men dagen kan ha ett eller to sifre.
_HREF = re.compile(r"/aktuelt/kalender/rentemoter/(\d{2})-(\d{2})-(\d{1,2})/")
_MAX_BYTES = 2_000_000


def parse_meeting_dates(html: str) -> list[date]:
    found: set[date] = set()
    for m in _HREF.finditer(html):
        try:
            d = date(2000 + int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            continue
        if d.weekday() < 5:  # rentemøter holdes aldri i helgen
            found.add(d)
    return sorted(found)


def fetch_html(url: str, timeout: int = 20) -> str:
    if not url.startswith("https://"):
        raise ValueError("Bare https er tillatt")
    req = urllib.request.Request(url, headers={"User-Agent": "kalender-feeds/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError("Svaret er uventet stort")
    return raw.decode("utf-8", errors="replace")


def refresh(
    data: dict, today: date, fetcher: Callable[[str], str] = fetch_html
) -> tuple[dict, list[str]]:
    """Oppdater møtedatoer fra Norges Bank. Ved enhver tvil beholdes lagrede data."""
    try:
        html = fetcher(LIST_URL)
    except Exception as exc:  # noqa: BLE001 - nettverksfeil skal aldri stoppe bygget
        return data, [f"Norges Bank: kunne ikke hente siden ({exc}); bruker lagrede datoer."]

    fetched = [d for d in parse_meeting_dates(html) if d >= today]
    if len(fetched) < 3:
        return data, [
            f"Norges Bank: fant bare {len(fetched)} datoer på siden; bruker lagrede datoer."
        ]

    old = {m["date"]: m for m in data["meetings"]}
    last_fetched = fetched[-1]
    merged: dict[str, dict] = {}
    # Behold historikk, og lagrede datoer etter siste dato siden viser
    # (siden kan være avkortet med «Vis flere treff»).
    for iso, meeting in old.items():
        d = date.fromisoformat(iso)
        if d < today or d > last_fetched:
            merged[iso] = meeting
    for d in fetched:
        iso = d.isoformat()
        merged[iso] = {"date": iso, "ppr": old.get(iso, {}).get("ppr", d.month in PPR_MONTHS)}

    notes = []
    added = sorted(set(merged) - set(old))
    removed = sorted(set(old) - set(merged))
    if added:
        notes.append(f"Norges Bank: nye datoer {', '.join(added)}")
    if removed:
        notes.append(f"Norges Bank: datoer fjernet {', '.join(removed)}")
    if not notes:
        notes.append("Norges Bank: datoene stemmer med siden.")
    return {**data, "meetings": [merged[k] for k in sorted(merged)]}, notes


def build_events(data: dict) -> list[Event]:
    events = []
    for meeting in data["meetings"]:
        d = date.fromisoformat(meeting["date"])
        with_report = bool(meeting.get("ppr"))
        summary = "Norges Bank: Rentebeslutning"
        if with_report:
            summary += " og Pengepolitisk rapport"
        lines = [f"Rentemøte i Norges Bank {nb_date(d)}, kl. 10:00 norsk tid."]
        if with_report:
            lines.append("Møtet legges frem sammen med en ny Pengepolitisk rapport.")
        lines.append("Kilde: Norges Banks kalender.")
        events.append(
            Event(
                uid=f"norgesbank-rentemote-{d.isoformat()}@kalender-feeds",
                start=datetime.combine(d, time(10, 0), tzinfo=TZ),
                duration=timedelta(minutes=30),
                summary=summary,
                description="\n".join(lines),
                url=LIST_URL,
            )
        )
    return events
