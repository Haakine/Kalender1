"""Registeret over kalenderfeeder. Legg til en ny kilde ved å legge til en Feed her."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .sources import fed, norges_bank, ssb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Feed:
    id: str  # brukes i filnavnet: ics/<id>.ics
    name: str
    description: str
    color: str
    data_file: str
    module: ModuleType
    source_label: str
    source_url: str
    # Varsler hvis siste hendelse ligger nærmere enn dette frem i tid.
    min_horizon_days: int


FEEDS: list[Feed] = [
    Feed(
        id="norges-bank",
        name="Norges Bank: rentemøter",
        description="Rentebeslutninger og dagene Pengepolitisk rapport legges frem.",
        color="#1F6F8B",
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
        data_file="ssb.json",
        module=ssb,
        source_label="SSBs kommende publiseringer",
        source_url="https://www.ssb.no/en/kommende-publiseringer",
        min_horizon_days=21,
    ),
]


def load_data(feed: Feed) -> dict:
    with (DATA_DIR / feed.data_file).open(encoding="utf-8") as fh:
        return json.load(fh)
