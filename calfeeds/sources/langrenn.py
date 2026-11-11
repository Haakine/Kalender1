"""Langrenn: verdenscupen, NM og ski-VM i Falun.

Ingen av kildene oppgir starttidspunkt ennå, så rennene legges inn som
heldagshendelser. Det er bedre enn å gjette på klokkeslett.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..fmt import nb_date, nb_span, slug
from ..ics import Event

ONE_DAY = timedelta(days=1)


def _world_cup(data: dict) -> list[Event]:
    events = []
    for stop in data["world_cup"]:
        for race in stop["races"]:
            d = date.fromisoformat(race["date"])
            events.append(
                Event(
                    uid=f"langrenn-vc-{d.isoformat()}-{slug(stop['place'])}@kalender-feeds",
                    start=d,
                    duration=ONE_DAY,
                    summary=f"Langrenn verdenscup, {stop['place']}: {race['race']}",
                    description=(
                        f"Verdenscup i {stop['place']} ({stop['country']}), {nb_date(d)}.\n"
                        "Starttid er ikke publisert ennå. Sjekk programmet hos FIS.\n"
                        "Datoene følger FIS' foreslåtte kalender fra mai 2026 og kan bli endret.\n"
                        "Kilde: FIS"
                    ),
                    url=data["world_cup_url"],
                )
            )
    return events


def _nm(data: dict) -> list[Event]:
    events = []
    for item in data["nm"]:
        d = date.fromisoformat(item["date"])
        events.append(
            Event(
                uid=f"langrenn-nm-{d.isoformat()}-{slug(item['race'])}@kalender-feeds",
                start=d,
                duration=ONE_DAY,
                summary=f"Langrenn NM, {item['place']}: {item['race']}",
                description=(
                    f"Norgesmesterskap i langrenn, {item['place']}, {nb_date(d)}.\n"
                    "Starttid er ikke publisert ennå. Sjekk programmet hos Norges Skiforbund.\n"
                    "Kilde: Norges Skiforbunds sesonginformasjon 2026/27"
                ),
                url=data["nm_url"],
            )
        )
    return events


def _vm(data: dict) -> list[Event]:
    vm = data["vm"]
    start, end = date.fromisoformat(vm["start"]), date.fromisoformat(vm["end"])
    return [
        Event(
            uid=f"langrenn-vm-{start.isoformat()}@kalender-feeds",
            start=start,
            duration=(end - start) + ONE_DAY,  # slutten er eksklusiv i iCalendar
            summary=f"Ski-VM i {vm['place']} (langrenn)",
            description=(
                f"Ski-VM (FIS Nordic World Ski Championships) i {vm['place']}, {nb_span(start, end)}.\n"
                "Hele mesterskapet, inkludert langrenn. Dagsprogram og starttider er ikke bekreftet ennå.\n"
                "Kilde: " + vm["source_label"]
            ),
            url=vm["url"],
        )
    ]


def build_events(data: dict) -> list[Event]:
    return _world_cup(data) + _nm(data) + _vm(data)
