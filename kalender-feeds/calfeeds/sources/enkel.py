"""Generisk kilde: en kalender som er beskrevet helt i én JSON-fil i data/custom/.

Bruk denne når hendelsene bare er en liste med datoer. Trenger kilden egen logikk
(henting fra nettet, utregning av datoer), lag heller en egen modul, se README.

Hendelser:
  {"id": "unik-id", "title": "Tittel", "start": "2027-03-05"}                    heldag
  {..., "start": "2027-03-05", "end": "2027-03-07"}                              flere dager (end er med)
  {..., "start": "2027-03-05T18:00", "tz": "Europe/Oslo", "minutes": 90}         med klokkeslett (lokal tid)
Valgfritt på hver hendelse: "description", "url" (https), "icon" (emoji), "channel" (TV-kanal, bare når den er bekreftet).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from ..fmt import slug
from ..ics import Event

ONE_DAY = timedelta(days=1)
DEFAULT_MINUTES = 60


def build_events(data: dict) -> list[Event]:
    prefix = slug(data["id"])
    label = data.get("source_label", "")
    events = []
    for item in data["events"]:
        raw = item["start"]
        if "T" in raw:
            start = datetime.fromisoformat(raw).replace(tzinfo=ZoneInfo(item.get("tz", "Europe/Oslo")))
            duration = timedelta(minutes=item.get("minutes", DEFAULT_MINUTES))
            day = start.date()
        else:
            start = date.fromisoformat(raw)
            end = date.fromisoformat(item["end"]) if item.get("end") else start
            if end < start:
                raise ValueError(f"{item['id']}: end er før start")
            duration = (end - start) + ONE_DAY
            day = start

        lines = [item["description"]] if item.get("description") else []
        if label:
            lines.append(f"Kilde: {label}")
        events.append(
            Event(
                uid=f"{prefix}-{slug(item['id'])}-{day.isoformat()}@kalender-feeds",
                start=start,
                duration=duration,
                summary=item["title"],
                description="\n".join(lines),
                url=item.get("url") or data.get("source_url") or "",
                icon=item.get("icon", ""),
                channel=item.get("channel", ""),
            )
        )
    return events
