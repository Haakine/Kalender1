"""Federal Reserve: FOMC-rentemøter og referater (minutes).

Datoene kommer fra https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm.
Renteavgjørelsen kommer kl. 14:00 Eastern Time andre møtedag. Referatet
publiseres tre uker etter avgjørelsen (regelen står på Fed sin egen side),
så vi beregner den datoen i stedet for å lagre den.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..fmt import nb_span
from ..ics import Event

TZ = ZoneInfo("America/New_York")
SOURCE_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


def build_events(data: dict) -> list[Event]:
    events = []
    for meeting in data["meetings"]:
        start = date.fromisoformat(meeting["start"])
        end = date.fromisoformat(meeting["end"])
        span = nb_span(start, end)
        tentative = bool(meeting.get("tentative"))
        with_projections = bool(meeting.get("sep"))

        summary = "Fed: Rentebeslutning (FOMC)"
        if with_projections:
            summary += " med prognoser"
        lines = [
            f"FOMC-møte {span}. Renteavgjørelsen kommer kl. 14:00 amerikansk østkysttid (ET), "
            "pressekonferansen vanligvis rundt 30 minutter senere."
        ]
        if with_projections:
            lines.append("Møtet inkluderer nye økonomiske anslag (SEP) og «dot plot».")
        if tentative:
            lines.append("Datoen er foreløpig og bekreftes på møtet før.")
        lines.append("Kilde: federalreserve.gov")
        events.append(
            Event(
                uid=f"fomc-vedtak-{end.isoformat()}@kalender-feeds",
                start=datetime.combine(end, time(14, 0), tzinfo=TZ),
                duration=timedelta(hours=1),
                summary=summary,
                description="\n".join(lines),
                url=SOURCE_URL,
            )
        )

        if meeting.get("minutes"):
            minutes_day = end + timedelta(days=21)
            events.append(
                Event(
                    uid=f"fomc-referat-{end.isoformat()}@kalender-feeds",
                    start=datetime.combine(minutes_day, time(14, 0), tzinfo=TZ),
                    duration=timedelta(minutes=30),
                    summary="Fed: Referat fra FOMC-møtet (minutes)",
                    description=(
                        f"Referat fra FOMC-møtet {span}, kl. 14:00 ET.\n"
                        "Datoen er beregnet: Fed publiserer referatet tre uker etter renteavgjørelsen.\n"
                        "Kilde: federalreserve.gov"
                    ),
                    url=SOURCE_URL,
                )
            )
    return events
