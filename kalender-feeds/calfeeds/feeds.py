"""Registeret over kalenderfeeder. Legg til en ny kilde ved å legge til en Feed her."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .sources import fed, fotball, langrenn, norges_bank, sjakk, ssb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Rekkefølgen kortene vises i på siden.
GROUP_ALL = "Alt i én kalender"
GROUP_ECONOMY = "Økonomi"
GROUP_SPORT = "Sport"
GROUP_ORDER = [GROUP_ALL, GROUP_ECONOMY, GROUP_SPORT]


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
    ),
]


def load_data(feed: Feed) -> dict:
    if feed.data_file is None:
        return {}
    with (DATA_DIR / feed.data_file).open(encoding="utf-8") as fh:
        return json.load(fh)
