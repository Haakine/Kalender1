"""Registeret over kalenderfeeder. Legg til en ny kilde ved å legge til en Feed her."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .sources import enkel, fed, fotball, langrenn, norges_bank, sjakk, ssb, trening

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Rekkefølgen kortene vises i på siden.
GROUP_ALL = "Alt i én kalender"
GROUP_ECONOMY = "Økonomi"
GROUP_SPORT = "Sport"
GROUP_TRAINING = "Trening"
GROUP_ORDER = [GROUP_ALL, GROUP_ECONOMY, GROUP_SPORT, GROUP_TRAINING]  # egne grupper i data/custom legges til etter disse


@dataclass(frozen=True)
class Feed:
    id: str  # brukes i filnavnet: ics/<id>.ics
    name: str
    description: str
    color: str
    group: str
    # Samlefeeden har ingen egen datafil eller modul, den slår sammen alle de andre.
    data_file: str | None = None
    module: ModuleType | None = None
    source_label: str = ""
    source_url: str = ""
    # Varsler hvis siste hendelse ligger nærmere enn dette frem i tid.
    # None = ingen sjekk (sesongbaserte sportskilder, som oppdateres for hånd).
    min_horizon_days: int | None = None
    combined: bool = False
    # false = hendelsene tas ikke med i «Alle hendelser» (for eksempel treningsplanen).
    in_combined: bool = True
    # Emoji foran alle titler i feeden (en hendelse kan ha sitt eget ikon i stedet).
    icon: str = ""
    # Påminnelse i minutter før start, for hendelser med klokkeslett og for heldagshendelser.
    # Negativt = etter start (for heldag: -450 betyr kl. 07:30 samme dag). None = ingen.
    alarm_minutes: int | None = None
    alarm_minutes_all_day: int | None = None


FEEDS: list[Feed] = [
    Feed(
        id="alle",
        name="Alle hendelser",
        description=(
            "Økonomi og sport samlet i én kalender, med én farge. "
            "Abonner på denne i stedet for de enkelte, ellers får du hver hendelse to ganger."
        ),
        color="#14202B",
        group=GROUP_ALL,
        combined=True,
    ),
    Feed(
        id="norges-bank",
        name="Norges Bank: rentemøter",
        description="Rentebeslutninger og dagene Pengepolitisk rapport legges frem.",
        color="#1F6F8B",
        group=GROUP_ECONOMY,
        data_file="norges_bank.json",
        module=norges_bank,
        source_label="Norges Banks kalender",
        source_url="https://www.norges-bank.no/aktuelt/kalender/rentemoter/",
        min_horizon_days=60,
        icon="🏦",
    ),
    Feed(
        id="fed",
        name="Federal Reserve: rentemøter",
        description="FOMC-avgjørelser kl. 14:00 ET, med referatene tre uker senere.",
        color="#8F3B76",
        group=GROUP_ECONOMY,
        data_file="fed.json",
        module=fed,
        source_label="Fed: FOMC-kalenderen",
        source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        min_horizon_days=90,
        icon="🇺🇸",
    ),
    Feed(
        id="ssb",
        name="SSB: KPI og nøkkeltall",
        description="Konsumprisindeksen, arbeidsledighet (AKU), produsentpriser og konjunkturtendensene.",
        color="#3C7D3E",
        group=GROUP_ECONOMY,
        data_file="ssb.json",
        module=ssb,
        source_label="SSBs kommende publiseringer",
        source_url="https://www.ssb.no/en/kommende-publiseringer",
        min_horizon_days=21,
        icon="📊",
    ),
    Feed(
        id="fotball",
        name="Fotball: Norges landslag",
        description="Kamper for herrelandslaget, med avspark i norsk tid.",
        color="#B3202F",
        group=GROUP_SPORT,
        data_file="fotball.json",
        module=fotball,
        source_label="sportsidioten.no",
        source_url="https://www.sportsidioten.no/fotball/nations-league-2026-2027/",
        icon="⚽",
        alarm_minutes=60,
    ),
    Feed(
        id="langrenn",
        name="Langrenn: verdenscup, NM og VM",
        description="Verdenscuprenn, Tour de Ski, Holmenkollen, NM og ski-VM i Falun.",
        color="#2F5FA8",
        group=GROUP_SPORT,
        data_file="langrenn.json",
        module=langrenn,
        source_label="FIS og Norges Skiforbund",
        source_url="https://www.fis-ski.com/cross-country/news/2025-26/tour-de-ski-to-make-french-debut-2026-27-world-cup-calendar-unveiled",
        icon="⛷️",
    ),
    Feed(
        id="sjakk",
        name="Sjakk: VM og store turneringer",
        description="VM-matchen i Genève, parti for parti, og VM i rapid og blitz.",
        color="#4A4A4A",
        group=GROUP_SPORT,
        data_file="sjakk.json",
        module=sjakk,
        source_label="FIDE",
        source_url="https://www.fide.com/salesforce-fide-world-championship-match-2026-schedule-format-and-prize-fund-confirmed/",
        icon="♟️",
    ),
    Feed(
        id="trening",
        name="Treningsplan",
        description=(
            "Dine økter de neste tre månedene, tilpasset konkurransene dine. "
            "Egen kalender, ikke med i «Alle hendelser»."
        ),
        color="#C2571A",
        group=GROUP_TRAINING,
        data_file="trening.json",
        module=trening,
        in_combined=False,
    ),
]


CUSTOM_DIR = DATA_DIR / "custom"
_REQUIRED = ("id", "name", "description", "color", "group", "events")


def _discover_custom() -> list[Feed]:
    """Leser alle data/custom/*.json. Filer som begynner med _ (malen) hoppes over."""
    feeds = []
    for path in sorted(CUSTOM_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        missing = [k for k in _REQUIRED if k not in data]
        if missing:
            raise ValueError(f"{path.name}: mangler {', '.join(missing)}")
        feeds.append(
            Feed(
                id=data["id"],
                name=data["name"],
                description=data["description"],
                color=data["color"],
                group=data["group"],
                data_file=f"custom/{path.name}",
                module=enkel,
                source_label=data.get("source_label", ""),
                source_url=data.get("source_url", ""),
                min_horizon_days=data.get("min_horizon_days"),
                in_combined=data.get("in_combined", True),
                icon=data.get("icon", ""),
                alarm_minutes=data.get("alarm_minutes"),
                alarm_minutes_all_day=data.get("alarm_minutes_all_day"),
            )
        )
    return feeds


FEEDS.extend(_discover_custom())
for _feed in FEEDS:
    if _feed.group not in GROUP_ORDER:
        GROUP_ORDER.append(_feed.group)
if len({f.id for f in FEEDS}) != len(FEEDS):
    raise ValueError("To kalendere har samme id")


def load_data(feed: Feed) -> dict:
    if feed.data_file is None:
        return {}
    with (DATA_DIR / feed.data_file).open(encoding="utf-8") as fh:
        return json.load(fh)
