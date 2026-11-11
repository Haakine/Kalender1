import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build  # noqa: E402
from calfeeds import ics  # noqa: E402
from calfeeds.feeds import FEEDS, load_data  # noqa: E402
from calfeeds.sources import fed, norges_bank, ssb  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def events_of(feed_id):
    feed = next(f for f in FEEDS if f.id == feed_id)
    return feed.module.build_events(load_data(feed))


class IcsWriter(unittest.TestCase):
    def test_escape_blocks_line_injection(self):
        evil = "Hei\r\nEND:VEVENT\r\nBEGIN:VEVENT; a,b\\c"
        escaped = ics.escape_text(evil)
        self.assertNotIn("\n", escaped)
        self.assertNotIn("\r", escaped)
        self.assertIn("\\;", escaped)
        self.assertIn("\\,", escaped)
        self.assertIn("\\\\", escaped)

    def test_control_characters_removed(self):
        self.assertEqual(ics.escape_text("a\x00b\x07c"), "abc")

    def test_fold_respects_75_octets_and_utf8(self):
        line = "SUMMARY:" + "æøå" * 60
        folded = ics.fold(line)
        parts = folded.split("\r\n")
        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part.encode("utf-8")), 75)
        unfolded = "".join(p[1:] if i else p for i, p in enumerate(parts))
        self.assertEqual(unfolded, line)

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            ics.format_utc(datetime(2026, 1, 1, 10, 0))

    def test_duplicate_uid_rejected(self):
        e = ics.Event("x@y", NOW, timedelta(minutes=5), "A")
        with self.assertRaises(ValueError):
            ics.render_calendar(name="n", description="d", events=[e, e], color="#112233", now=NOW)

    def test_bad_url_and_color_rejected(self):
        bad = ics.Event("x@y", NOW, timedelta(minutes=5), "A", url="http://insecure.example")
        with self.assertRaises(ValueError):
            ics.render_calendar(name="n", description="d", events=[bad], color="#112233", now=NOW)
        ok = ics.Event("x@y", NOW, timedelta(minutes=5), "A")
        with self.assertRaises(ValueError):
            ics.render_calendar(name="n", description="d", events=[ok], color="red", now=NOW)

    def test_crlf_endings_and_envelope(self):
        e = ics.Event("x@y", NOW, timedelta(minutes=5), "A")
        text = ics.render_calendar(name="n", description="d", events=[e], color="#112233", now=NOW)
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))
        self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertIn("TRANSP:TRANSPARENT", text)


class Timezones(unittest.TestCase):
    def utc(self, event):
        return event.start.astimezone(UTC)

    def test_norges_bank_winter_time(self):
        ev = next(e for e in events_of("norges-bank") if "2026-12-17" in e.uid)
        self.assertEqual(self.utc(ev), datetime(2026, 12, 17, 9, 0, tzinfo=UTC))  # CET = UTC+1

    def test_norges_bank_summer_time(self):
        ev = next(e for e in events_of("norges-bank") if "2027-06-17" in e.uid)
        self.assertEqual(self.utc(ev), datetime(2027, 6, 17, 8, 0, tzinfo=UTC))  # CEST = UTC+2

    def test_fomc_winter_and_summer(self):
        winter = next(e for e in events_of("fed") if e.uid == "fomc-vedtak-2026-12-09@kalender-feeds")
        self.assertEqual(self.utc(winter), datetime(2026, 12, 9, 19, 0, tzinfo=UTC))  # EST = UTC-5
        summer = next(e for e in events_of("fed") if e.uid == "fomc-vedtak-2027-03-17@kalender-feeds")
        self.assertEqual(self.utc(summer), datetime(2027, 3, 17, 18, 0, tzinfo=UTC))  # EDT = UTC-4

    def test_ssb_release_time(self):
        ev = next(e for e in events_of("ssb") if e.uid == "ssb-kpi-2027-01-11@kalender-feeds")
        self.assertEqual(self.utc(ev), datetime(2027, 1, 11, 7, 0, tzinfo=UTC))


SOURCE_FEEDS = [f for f in FEEDS if not f.combined]
ECONOMY_IDS = {"norges-bank", "fed", "ssb"}


class DataSanity(unittest.TestCase):
    def test_uids_unique_across_all_feeds(self):
        uids = [e.uid for f in SOURCE_FEEDS for e in f.module.build_events(load_data(f))]
        self.assertEqual(len(uids), len(set(uids)))

    def test_economy_events_on_weekdays(self):
        for feed in SOURCE_FEEDS:
            if feed.id not in ECONOMY_IDS:
                continue  # sport kan ligge i helgene
            for e in feed.module.build_events(load_data(feed)):
                local = e.start.astimezone(ZoneInfo("Europe/Oslo")).date()
                self.assertLess(e.start.weekday(), 5, f"{e.uid} faller i helgen")
                self.assertLess(local.weekday(), 5, f"{e.uid} faller i helgen (norsk tid)")

    def test_norges_bank_report_months(self):
        for m in load_data(next(f for f in FEEDS if f.id == "norges-bank"))["meetings"]:
            d = date.fromisoformat(m["date"])
            self.assertEqual(m["ppr"], d.month in norges_bank.PPR_MONTHS, m["date"])

    def test_fomc_is_two_day_tue_wed_and_minutes_after_21_days(self):
        data = load_data(next(f for f in FEEDS if f.id == "fed"))
        for m in data["meetings"]:
            s, e = date.fromisoformat(m["start"]), date.fromisoformat(m["end"])
            self.assertEqual((s.weekday(), e.weekday(), (e - s).days), (1, 2, 1), m)
        events = {e.uid: e for e in fed.build_events(data)}
        minutes = events["fomc-referat-2026-10-28@kalender-feeds"]
        self.assertEqual(minutes.start.date(), date(2026, 11, 18))  # stemmer med Reuters/Fed-oversikten
        minutes = events["fomc-referat-2026-12-09@kalender-feeds"]
        self.assertEqual(minutes.start.date(), date(2026, 12, 30))

    def test_ssb_series_known(self):
        for item in load_data(next(f for f in FEEDS if f.id == "ssb"))["releases"]:
            self.assertIn(item["series"], ssb.SERIES)

    def test_feeds_render_with_every_event(self):
        for feed in SOURCE_FEEDS:
            events = feed.module.build_events(load_data(feed))
            text = ics.render_calendar(
                name=feed.name, description=feed.description, events=events, color=feed.color, now=NOW
            )
            self.assertEqual(text.count("BEGIN:VEVENT"), len(events))
            self.assertEqual(text.count("END:VEVENT"), len(events))

    def test_combined_feed_contains_every_event_once(self):
        results, _ = build.collect(date(2026, 11, 11), offline=True)
        by_id = {feed.id: events for feed, _d, events in results}
        expected = sorted(e.uid for f in SOURCE_FEEDS for e in by_id[f.id])
        self.assertEqual(sorted(e.uid for e in by_id["alle"]), expected)
        self.assertGreater(len(expected), 60)


class AllDayEvents(unittest.TestCase):
    def render(self, event):
        return ics.render_calendar(name="n", description="d", events=[event], color="#112233", now=NOW)

    def test_all_day_uses_date_values_with_exclusive_end(self):
        e = ics.Event("a@b", date(2027, 2, 24), timedelta(days=12), "VM")
        text = self.render(e)
        self.assertIn("DTSTART;VALUE=DATE:20270224", text)
        self.assertIn("DTEND;VALUE=DATE:20270308", text)

    def test_all_day_must_be_whole_days(self):
        with self.assertRaises(ValueError):
            self.render(ics.Event("a@b", date(2027, 1, 1), timedelta(hours=5), "x"))
        with self.assertRaises(ValueError):
            self.render(ics.Event("a@b", date(2027, 1, 1), timedelta(days=1, hours=1), "x"))

    def test_mixed_events_sort_without_error(self):
        events = [
            ics.Event("a@b", date(2026, 12, 2), timedelta(days=1), "heldag"),
            ics.Event("b@b", datetime(2026, 12, 2, 8, 0, tzinfo=UTC), timedelta(hours=1), "tid"),
        ]
        text = ics.render_calendar(name="n", description="d", events=events, color="#112233", now=NOW)
        self.assertEqual(text.count("BEGIN:VEVENT"), 2)


class SportFeeds(unittest.TestCase):
    def test_football_kickoff_times_in_utc(self):
        events = {e.uid: e for e in events_of("fotball")}
        wales = events["fotball-2026-11-14-norge-wales@kalender-feeds"]
        self.assertEqual(wales.start.astimezone(UTC), datetime(2026, 11, 14, 17, 0, tzinfo=UTC))
        denmark = events["fotball-2026-11-17-danmark-norge@kalender-feeds"]
        self.assertEqual(denmark.start.astimezone(UTC), datetime(2026, 11, 17, 19, 45, tzinfo=UTC))
        self.assertIn("Hjemmekamp", wales.description)
        self.assertIn("Bortekamp", denmark.description)

    def test_world_championship_has_14_games_and_none_on_rest_days(self):
        games = [e for e in events_of("sjakk") if "-parti-" in e.uid]
        self.assertEqual(len(games), 14)
        dates = [e.start for e in games]
        self.assertEqual(dates, sorted(dates))
        for rest in (date(2026, 11, 27), date(2026, 12, 1), date(2026, 12, 5), date(2026, 12, 9)):
            self.assertNotIn(rest, dates)
        self.assertEqual((dates[0], dates[-1]), (date(2026, 11, 24), date(2026, 12, 11)))

    def test_falun_championships_span(self):
        vm = next(e for e in events_of("langrenn") if e.uid.startswith("langrenn-vm-"))
        self.assertEqual(vm.start, date(2027, 2, 24))
        self.assertEqual(vm.start + vm.duration, date(2027, 3, 8))  # siste dag 7. mars, eksklusiv slutt

    def test_nm_weekdays_match_the_documented_pattern(self):
        nm = {e.start: e for e in events_of("langrenn") if "-nm-" in e.uid}
        self.assertEqual([d.weekday() for d in sorted(nm) if d.month == 1], [3, 4, 5])  # tor, fre, lør
        self.assertEqual([d.weekday() for d in sorted(nm) if d.month == 4], [4, 5, 6])  # fre, lør, søn

    def test_world_cup_dates_are_ordered_and_in_season(self):
        wc = sorted(e.start for e in events_of("langrenn") if "-vc-" in e.uid)
        self.assertEqual(wc[0], date(2026, 11, 27))
        self.assertEqual(wc[-1], date(2027, 3, 21))
        self.assertEqual(len(wc), len(set(wc)))  # aldri to renn samme dag

    def test_every_event_url_is_https(self):
        for feed in SOURCE_FEEDS:
            for e in feed.module.build_events(load_data(feed)):
                self.assertTrue(e.url.startswith("https://"), e.uid)


class NorgesBankRefresh(unittest.TestCase):
    PAGE = """
      <a href="/aktuelt/kalender/rentemoter/26-12-17/">Rentebeslutning og Pengepolitisk rapport</a>
      <a href="/aktuelt/kalender/rentemoter/27-01-21/">Rentebeslutning</a>
      <a href="/aktuelt/kalender/rentemoter/27-05-05/">x</a>
      <a href="/aktuelt/kalender/rentemoter/27-11-4/">x</a>
      <a href="/aktuelt/kalender/rentemoter/27-02-30/">ugyldig dato</a>
      <a href="/aktuelt/kalender/rentemoter/27-01-23/">lørdag, skal forkastes</a>
    """

    def test_parser_handles_unpadded_day_and_rejects_bad_dates(self):
        dates = norges_bank.parse_meeting_dates(self.PAGE)
        self.assertEqual(
            dates, [date(2026, 12, 17), date(2027, 1, 21), date(2027, 5, 5), date(2027, 11, 4)]
        )

    def test_network_failure_keeps_stored_data(self):
        data = load_data(next(f for f in FEEDS if f.id == "norges-bank"))

        def boom(_url):
            raise OSError("blokkert")

        new, notes = norges_bank.refresh(data, date(2026, 11, 11), fetcher=boom)
        self.assertEqual(new, data)
        self.assertIn("lagrede datoer", notes[0])

    def test_too_few_dates_keeps_stored_data(self):
        data = load_data(next(f for f in FEEDS if f.id == "norges-bank"))
        new, _ = norges_bank.refresh(data, date(2026, 11, 11), fetcher=lambda _u: "<html>tom side</html>")
        self.assertEqual(new, data)

    def test_moved_date_is_replaced_and_later_dates_kept(self):
        data = load_data(next(f for f in FEEDS if f.id == "norges-bank"))
        page = """
          /aktuelt/kalender/rentemoter/26-12-18/
          /aktuelt/kalender/rentemoter/27-01-21/
          /aktuelt/kalender/rentemoter/27-03-18/
        """
        new, notes = norges_bank.refresh(data, date(2026, 11, 11), fetcher=lambda _u: page)
        got = [m["date"] for m in new["meetings"]]
        self.assertIn("2026-12-18", got)
        self.assertNotIn("2026-12-17", got)
        self.assertNotIn("2027-05-05", [m["date"] for m in new["meetings"] if m["date"] < "2027-03-19"])
        self.assertIn("2027-12-16", got)  # etter siste hentede dato: beholdes
        self.assertTrue(any("nye datoer" in n for n in notes))


class SiteDisplay(unittest.TestCase):
    def test_short_title_drops_only_redundant_source_prefixes(self):
        self.assertEqual(build.short_title("Norges Bank: Rentebeslutning"), "Rentebeslutning")
        self.assertEqual(build.short_title("Fotball: Norge–Wales (Nations League)"), "Norge–Wales (Nations League)")
        # Disse bærer informasjon og skal beholdes:
        self.assertEqual(build.short_title("Sjakk-VM: parti 1 av 14"), "Sjakk-VM: parti 1 av 14")
        title = "Langrenn verdenscup, Ruka: sprint klassisk"
        self.assertEqual(build.short_title(title), title)

    def test_every_event_payload_has_short_title(self):
        results, _ = build.collect(date(2026, 11, 11), offline=True)
        for _feed, _data, events in results:
            for e in events:
                payload = build._event_payload(e)
                self.assertTrue(payload["short"])
                self.assertIn(payload["allDay"], (True, False))


class Freshness(unittest.TestCase):
    def test_current_data_is_fresh_today(self):
        results, _ = build.collect(date(2026, 11, 11), offline=True)
        self.assertEqual(build.stale_problems(results, date(2026, 11, 11)), [])

    def test_old_data_is_flagged(self):
        results, _ = build.collect(date(2027, 12, 1), offline=True)
        problems = build.stale_problems(results, date(2027, 12, 1))
        self.assertTrue(problems)

    def test_sport_feeds_never_trigger_freshness_failures(self):
        results, _ = build.collect(date(2030, 1, 1), offline=True)
        flagged = " ".join(build.stale_problems(results, date(2030, 1, 1)))
        for name in ("Fotball", "Langrenn", "Sjakk", "Alle hendelser"):
            self.assertNotIn(name, flagged)


if __name__ == "__main__":
    unittest.main()


class CustomFeeds(unittest.TestCase):
    """Nye kalendere som bare er en JSON-fil i data/custom/."""

    def _template(self):
        import json
        from calfeeds import feeds
        return json.loads((feeds.CUSTOM_DIR / "_mal.json").read_text(encoding="utf-8"))

    def test_template_builds_all_three_event_kinds(self):
        from calfeeds.sources import enkel
        events = enkel.build_events(self._template())
        self.assertEqual(len(events), 3)
        day, span, timed = events
        self.assertTrue(day.all_day and day.duration == timedelta(days=1))
        self.assertEqual(span.duration, timedelta(days=3))  # 5., 6. og 7. mars
        self.assertFalse(timed.all_day)
        self.assertEqual(timed.start.astimezone(timezone.utc).hour, 17)  # 18:00 norsk vintertid
        self.assertEqual(timed.duration, timedelta(minutes=90))

    def test_template_renders_to_valid_calendar(self):
        from calfeeds.sources import enkel
        data = self._template()
        text = ics.render_calendar(name="x", description="y", events=enkel.build_events(data),
                               color=data["color"], now=datetime(2026, 11, 11, tzinfo=timezone.utc))
        self.assertEqual(text.count("BEGIN:VEVENT"), 3)

    def test_end_before_start_is_rejected(self):
        from calfeeds.sources import enkel
        bad = {"id": "x", "events": [{"id": "a", "title": "A", "start": "2027-03-05", "end": "2027-03-01"}]}
        with self.assertRaises(ValueError):
            enkel.build_events(bad)

    def test_discovery_adds_feed_new_group_and_combined_feed(self):
        import json, tempfile
        from pathlib import Path
        from unittest import mock
        import build
        from calfeeds import feeds
        data = self._template()
        data.update(id="ny-test", name="Ny test", group="Kultur")
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "ny-test.json").write_text(json.dumps(data), encoding="utf-8")
            Path(tmp, "_skjult.json").write_text("ikke json", encoding="utf-8")  # må hoppes over
            with mock.patch.object(feeds, "CUSTOM_DIR", Path(tmp)):
                found = feeds._discover_custom()
        self.assertEqual([f.id for f in found], ["ny-test"])
        self.assertEqual(found[0].group, "Kultur")
        self.assertEqual(found[0].data_file, "custom/ny-test.json")

    def test_missing_required_field_gives_clear_error(self):
        import json, tempfile
        from pathlib import Path
        from unittest import mock
        from calfeeds import feeds
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.json").write_text(json.dumps({"id": "a"}), encoding="utf-8")
            with mock.patch.object(feeds, "CUSTOM_DIR", Path(tmp)):
                with self.assertRaisesRegex(ValueError, "mangler"):
                    feeds._discover_custom()
