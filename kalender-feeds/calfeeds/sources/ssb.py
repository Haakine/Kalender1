"""Statistisk sentralbyrå (SSB): KPI og noen andre sentrale økonomitall.

Datoene kommer fra SSBs kalender over kommende publiseringer
(https://www.ssb.no/en/kommende-publiseringer). SSB publiserer
mandag til fredag kl. 08:00 norsk tid.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..fmt import nb_date
from ..ics import Event

TZ = ZoneInfo("Europe/Oslo")
CALENDAR_URL = "https://www.ssb.no/en/kommende-publiseringer"

# serie -> (tittelmal, lenke til statistikksiden)
SERIES = {
    "kpi": (
        "SSB: Konsumprisindeksen (KPI) for {period}",
        "https://www.ssb.no/en/priser-og-prisindekser/konsumpriser/statistikk/konsumprisindeksen",
    ),
    "aku": (
        "SSB: Arbeidskraftundersøkelsen (AKU) for {period}",
        "https://www.ssb.no/en/arbeid-og-lonn/sysselsetting/statistikk/arbeidskraftundersokelsen",
    ),
    "ppi": (
        "SSB: Produsentprisindeksen for {period}",
        "https://www.ssb.no/en/priser-og-prisindekser/produsent-og-engrosprisindekser/statistikk/produsentprisindeksen",
    ),
    "konj": (
        "SSB: Konjunkturtendensene ({period})",
        "https://www.ssb.no/en/nasjonalregnskap-og-konjunkturer/konjunkturer/statistikk/konjunkturtendensene",
    ),
}


def build_events(data: dict) -> list[Event]:
    events = []
    for item in data["releases"]:
        title, url = SERIES[item["series"]]
        d = date.fromisoformat(item["date"])
        events.append(
            Event(
                uid=f"ssb-{item['series']}-{d.isoformat()}@kalender-feeds",
                start=datetime.combine(d, time(8, 0), tzinfo=TZ),
                duration=timedelta(minutes=30),
                summary=title.format(period=item["period"]),
                description=(
                    f"Publiseres {nb_date(d)} kl. 08:00 norsk tid.\n"
                    "Kilde: SSBs kalender over kommende publiseringer."
                ),
                url=url,
            )
        )
    return events
