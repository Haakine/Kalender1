"""USA: FOMC-rentemøter og jobbtallene (Employment Situation).

FOMC-datoene kommer fra https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm.
Renteavgjørelsen kommer kl. 14:00 Eastern Time andre møtedag.
Jobbtallene publiseres av BLS kl. 08:30 Eastern Time, etter BLS' publiseringskalender.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..fmt import nb_span
from ..ics import Event

TZ = ZoneInfo("America/New_York")
SOURCE_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
JOBS_URL = "https://www.bls.gov/schedule/news_release/empsit.htm"


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

    for item in data.get("jobs", []):
        d = date.fromisoformat(item["date"])
        events.append(
            Event(
                uid=f"usa-jobbtall-{d.isoformat()}@kalender-feeds",
                start=datetime.combine(d, time(8, 30), tzinfo=TZ),
                duration=timedelta(minutes=30),
                summary="USA: Jobbtall (Employment Situation)",
                description=(
                    f"Sysselsettingsrapporten for {item['month']} (nonfarm payrolls og arbeidsledighet), "
                    "kl. 08:30 amerikansk østkysttid (ET).\nKilde: Bureau of Labor Statistics (BLS)"
                ),
                url=JOBS_URL,
            )
        )
    return events
