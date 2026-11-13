"""Treningsplan: rullerende plan som genereres av calfeeds/training.py fra data/trening.json.

Kalenderen får bare navnet på økten. Varighet og annet er til planleggingen her.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..fmt import slug
from ..ics import Event
from ..training import generate

USES_TODAY = True  # build.py gir dagens dato, slik at planen rulles fremover


def build_events(data: dict, today: date | None = None) -> list[Event]:
    today = today or date.today()
    seen: dict = {}
    events = []
    for s in generate(today, data):
        n = seen[(s.day, s.title)] = seen.get((s.day, s.title), 0) + 1
        events.append(
            Event(
                uid=f"trening-{s.day.isoformat()}-{slug(s.title)}-{n}@kalender-feeds",
                start=s.day,
                duration=timedelta(days=1),
                summary=s.title,
                icon=s.icon,
            )
        )
    return events
