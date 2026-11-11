#!/usr/bin/env python3
"""Bygger kalenderfeedene (.ics) og nettsiden til mappen site/.

Bruk:
  python build.py                      # bygg (henter oppdateringer hvis nettet er tilgjengelig)
  python build.py --offline            # bygg kun fra lagrede data
  python build.py --check-freshness    # feil (exit 1) hvis dataene snart går tom for fremtidige datoer
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from calfeeds.feeds import FEEDS, load_data
from calfeeds.fmt import nb_date
from calfeeds.ics import Event, render_calendar

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"


def collect(today: date, offline: bool):
    results = []
    notes: list[str] = []
    for feed in FEEDS:
        data = load_data(feed)
        if not offline and hasattr(feed.module, "refresh"):
            data, feed_notes = feed.module.refresh(data, today)
            notes += feed_notes
        results.append((feed, data, feed.module.build_events(data)))
    return results, notes


def stale_problems(results, today: date) -> list[str]:
    problems = []
    for feed, _data, events in results:
        last = max(e.start for e in events).date()
        needed = today + timedelta(days=feed.min_horizon_days)
        if last < needed:
            problems.append(
                f"{feed.name}: siste kjente dato er {nb_date(last)}, "
                f"men feeden bør dekke minst til {nb_date(needed)}. Oppdater data/{feed.data_file}."
            )
    return problems


def _sha256_csp(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def _events_json(results, now: datetime) -> str:
    cutoff = now - timedelta(days=1)
    payload = {
        feed.id: [
            {"start": e.start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "title": e.summary}
            for e in sorted(events, key=lambda e: e.start)
            if e.start >= cutoff
        ]
        for feed, _data, events in results
    }
    # «</» kan avslutte script-elementet for tidlig, så den escapes.
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def _feed_card(feed, data) -> str:
    e = html.escape
    verified = data.get("verified")
    verified_text = f"Datoene ble sjekket mot kilden {nb_date(date.fromisoformat(verified))}." if verified else ""
    note = data.get("coverage_note", "")
    extra = " ".join(x for x in (verified_text, note) if x)
    return f"""
    <section class="feed" data-feed="{e(feed.id)}">
      <div class="leaf" aria-hidden="true"><span class="leaf-day js-day">–</span><span class="leaf-month js-month"></span></div>
      <div class="feed-main">
        <h2>{e(feed.name)}</h2>
        <p class="what">{e(feed.description)}</p>
        <p class="next js-next">Neste dato lastes inn …</p>
        <div class="actions">
          <a class="btn primary js-subscribe" href="ics/{e(feed.id)}.ics" hidden>Abonner i Kalender</a>
          <a class="btn" href="ics/{e(feed.id)}.ics" download>Last ned .ics</a>
          <button class="btn js-copy" type="button">Kopier lenke</button>
        </div>
        <details>
          <summary>Kommende datoer</summary>
          <ul class="upcoming js-upcoming"></ul>
        </details>
        <p class="source">Kilde: <a href="{e(feed.source_url)}">{e(feed.source_label)}</a>. {e(extra)}</p>
      </div>
    </section>"""


def _stylesheet(results) -> str:
    css = (TEMPLATES / "app.css").read_text(encoding="utf-8")
    tones = "\n".join(
        f'.feed[data-feed="{feed.id}"] {{ --tone: {feed.color}; }}' for feed, _d, _e in results
    )
    return css.rstrip("\n") + "\n" + tones + "\n"


def write_site(results, out: Path, now: datetime) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / "ics").mkdir(parents=True)
    (out / ".nojekyll").write_text("", encoding="utf-8")

    for feed, _data, events in results:
        text = render_calendar(
            name=feed.name,
            description=feed.description,
            events=events,
            color=feed.color,
            now=now,
        )
        # Skrives som bytes for å bevare CRLF-linjeskift som iCalendar krever.
        (out / "ics" / f"{feed.id}.ics").write_bytes(text.encode("utf-8"))

    style = _stylesheet(results)
    script = (TEMPLATES / "app.js").read_text(encoding="utf-8")
    csp = (
        "default-src 'none'; "
        f"style-src {_sha256_csp(style)}; "
        f"script-src {_sha256_csp(script)}; "
        "img-src data:; base-uri 'none'; form-action 'none'"
    )
    page = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    page = (
        page.replace("{{CSP}}", html.escape(csp, quote=True))
        .replace("{{STYLE}}", style)
        .replace("{{FEEDS}}", "".join(_feed_card(f, d) for f, d, _e in results))
        .replace("{{EVENTS}}", _events_json(results, now))
        .replace("{{SCRIPT}}", script)
        .replace("{{BUILT}}", nb_date(now.date()))
    )
    (out / "index.html").write_text(page, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="site", help="Utmappe (standard: site)")
    parser.add_argument("--offline", action="store_true", help="Ikke hent oppdateringer fra nettet")
    parser.add_argument("--check-freshness", action="store_true", help="Sjekk at dataene dekker nok frem i tid")
    parser.add_argument("--today", help="Overstyr dagens dato (YYYY-MM-DD), brukes i tester")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = date.fromisoformat(args.today) if args.today else now.date()

    if args.check_freshness:
        results, _ = collect(today, offline=True)
        problems = stale_problems(results, today)
        for p in problems:
            print(f"FOR GAMMELT: {p}")
        if not problems:
            print("Alle feeder dekker langt nok frem i tid.")
        return 1 if problems else 0

    results, notes = collect(today, offline=args.offline)
    for n in notes:
        print(n)
    write_site(results, ROOT / args.out, now)
    for feed, _d, events in results:
        print(f"{feed.id}: {len(events)} hendelser")
    for p in stale_problems(results, today):
        print(f"ADVARSEL: {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
