"""Sjakk: VM-matchen og andre store turneringer.

Starttider for partiene er ikke oppgitt i kildene, så alt legges inn som
heldagshendelser. Flere turneringer legges til i data/sjakk.json.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..fmt import nb_date, nb_span, slug
from ..ics import Event

ONE_DAY = timedelta(days=1)
NO_TIME = "Starttid er ikke publisert i kildene. Sjekk FIDE."


def _world_championship(data: dict) -> list[Event]:
    wc = data["world_championship"]
    url = wc["url"]
    players = wc["players"]
    events = []

    opening = date.fromisoformat(wc["opening_ceremony"])
    events.append(
        Event(
            uid=f"sjakk-vm-apning-{opening.isoformat()}@kalender-feeds",
            start=opening,
            duration=ONE_DAY,
            summary="Sjakk-VM: mediedag og åpningsseremoni",
            description=f"VM-matchen i {wc['venue']}: {players}.\nKilde: FIDE",
            url=url,
        )
    )

    total = len(wc["games"])
    for game in wc["games"]:
        d = date.fromisoformat(game["date"])
        events.append(
            Event(
                uid=f"sjakk-vm-parti-{game['n']:02d}-{d.isoformat()}@kalender-feeds",
                start=d,
                duration=ONE_DAY,
                summary=f"Sjakk-VM: parti {game['n']} av {total}",
                description=(
                    f"Klassisk parti {game['n']} i VM-matchen i {wc['venue']}, {nb_date(d)}.\n"
                    f"{players}. Første spiller til 7,5 poeng vinner.\n"
                    f"{NO_TIME}\nKilde: FIDE"
                ),
                url=url,
            )
        )

    tiebreak = date.fromisoformat(wc["tiebreak"])
    events.append(
        Event(
            uid=f"sjakk-vm-omkamp-{tiebreak.isoformat()}@kalender-feeds",
            start=tiebreak,
            duration=ONE_DAY,
            summary="Sjakk-VM: omkamper (bare hvis det står likt)",
            description=(
                "Omkamper spilles bare hvis stillingen er 7–7 etter de 14 klassiske partiene. "
                "Avslutningsseremoni samme dag.\n" + NO_TIME + "\nKilde: FIDE"
            ),
            url=url,
        )
    )
    return events


def _other(data: dict) -> list[Event]:
    events = []
    for item in data["events"]:
        start, end = date.fromisoformat(item["start"]), date.fromisoformat(item["end"])
        events.append(
            Event(
                uid=f"sjakk-{slug(item['id'])}-{start.isoformat()}@kalender-feeds",
                start=start,
                duration=(end - start) + ONE_DAY,
                summary=f"Sjakk: {item['title']}",
                description=(
                    f"{item['title']}, {item['place']}, {nb_span(start, end)}.\n"
                    f"{NO_TIME}\nKilde: {item['source_label']}"
                ),
                url=item["url"],
            )
        )
    return events


def build_events(data: dict) -> list[Event]:
    return _world_championship(data) + _other(data)
