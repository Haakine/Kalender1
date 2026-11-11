"""Fotball: Norges herrelandslag.

Kamper legges inn for hånd i data/fotball.json etter hvert som UEFA og NFF
publiserer dem. Avspark lagres som lokal tid på kampstedet og omregnes til UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..fmt import nb_date, slug
from ..ics import Event

OSLO = ZoneInfo("Europe/Oslo")


def build_events(data: dict) -> list[Event]:
    events = []
    for match in data["matches"]:
        venue_tz = ZoneInfo(match.get("tz", "Europe/Oslo"))
        kickoff = datetime.fromisoformat(match["kickoff"]).replace(tzinfo=venue_tz)
        home, away = match["home"], match["away"]
        local = kickoff.astimezone(OSLO)

        lines = [
            f"{match['competition']}.",
            f"{nb_date(local.date())}, avspark kl. {local:%H:%M} norsk tid. "
            + ("Hjemmekamp." if match["home"] == "Norge" else "Bortekamp."),
        ]
        if match.get("note"):
            lines.append(match["note"])
        lines.append("Kilde: " + data["source_label"])

        events.append(
            Event(
                uid=f"fotball-{kickoff.date().isoformat()}-{slug(home)}-{slug(away)}@kalender-feeds",
                start=kickoff,
                duration=timedelta(hours=2),
                summary=f"Fotball: {home}–{away} ({match['competition_short']})",
                description="\n".join(lines),
                url=data["source"],
            )
        )
    return events
