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


class DataSanity(unittest.TestCase):
    def test_uids_unique_across_all_feeds(self):
        uids = [e.uid for f in FEEDS for e in f.module.build_events(load_data(f))]
        self.assertEqual(len(uids), len(set(uids)))

    def test_all_events_on_weekdays(self):
        for feed in FEEDS:
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
        for feed in FEEDS:
            events = feed.module.build_events(load_data(feed))
            text = ics.render_calendar(
                name=feed.name, description=feed.description, events=events, color=feed.color, now=NOW
            )
            self.assertEqual(text.count("BEGIN:VEVENT"), len(events))
            self.assertEqual(text.count("END:VEVENT"), len(events))


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


class Freshness(unittest.TestCase):
    def test_current_data_is_fresh_today(self):
        results, _ = build.collect(date(2026, 11, 11), offline=True)
        self.assertEqual(build.stale_problems(results, date(2026, 11, 11)), [])

    def test_old_data_is_flagged(self):
        results, _ = build.collect(date(2027, 12, 1), offline=True)
        self.assertTrue(build.stale_problems(results, date(2027, 12, 1)))


if __name__ == "__main__":
    unittest.main()
