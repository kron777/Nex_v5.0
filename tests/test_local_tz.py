"""NEX5_TZ — one clock for NEX (nex_config.local_tz), default Africa/Johannesburg.

Behavioural: the real daily_tick decides which scheduled activities are due from
a frozen UTC instant chosen so the zones disagree -- 16:30 UTC is 18:30 in
Johannesburg (outreach_2, scheduled 18:00, IS due) but 17:30 in Amsterdam (NOT
due). Before this, daily_life hardcoded Europe/Amsterdam.
"""
import datetime as _dt
import os
import tempfile
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

import nex_config

_INSTANT = _dt.datetime(2026, 10, 26, 16, 30, tzinfo=_dt.timezone.utc)


class _FrozenDatetime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return _INSTANT.astimezone(tz) if tz else _INSTANT.replace(tzinfo=None)


class TestLocalTz(unittest.TestCase):

    def test_default_is_owner_zone(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEX5_TZ", None)
            self.assertEqual(nex_config.local_tz().key, "Africa/Johannesburg")

    def test_env_overrides_and_bad_value_falls_back(self):
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Europe/Amsterdam"}):
            self.assertEqual(nex_config.local_tz().key, "Europe/Amsterdam")
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Not/A_Zone"}):
            with self.assertLogs("nex5.config", "WARNING"):
                nex_config._zone.cache_clear()
                self.assertEqual(nex_config.local_tz().key, "Africa/Johannesburg")

    def test_sql_offset_is_the_zones_not_the_machines(self):
        ts = _INSTANT.timestamp()
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Africa/Johannesburg"}):
            self.assertEqual(nex_config.local_utc_offset_seconds(ts), 2 * 3600)
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Europe/Amsterdam"}):
            self.assertEqual(nex_config.local_utc_offset_seconds(ts), 1 * 3600)  # CET

    def test_decoder_hour_features_follow_the_zone(self):
        # Replaces the old fixed "+2 (May, CEST)" offset.
        from theory_x.coincidence import decoder_loop as dl
        ts = _INSTANT.timestamp()                       # a Monday
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Africa/Johannesburg"}):
            self.assertEqual(dl._local_hour_dow(ts), (18, 0))
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Europe/Amsterdam"}):
            self.assertEqual(dl._local_hour_dow(ts), (17, 0))


class TestScheduleFollowsZone(unittest.TestCase):

    def _fired(self, zone):
        from substrate.init_db import init_all
        from theory_x.life import daily_life as dl
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"NEX5_DATA_DIR": tmp, "NEX5_TZ": zone}), \
                mock.patch.object(dl, "datetime", _FrozenDatetime), \
                mock.patch.dict(dl._ACTIVITY_FUNCS,
                                {k: (lambda d: "stub") for k in dl.SCHEDULE.values()}):
            init_all()
            stats = dl.daily_tick()
        return stats["hour"], set(stats["fired"])

    def test_outreach_2_due_at_1830_sast_not_at_1730_cet(self):
        hour, fired = self._fired("Africa/Johannesburg")
        self.assertEqual(hour, 18)
        self.assertIn("outreach_2", fired)
        self.assertNotIn("journal", fired)              # 22:00 not reached
        hour, fired = self._fired("Europe/Amsterdam")
        self.assertEqual(hour, 17)
        self.assertNotIn("outreach_2", fired)
        self.assertIn("reading_2", fired)               # 14:00 passed in both


if __name__ == "__main__":
    unittest.main()
