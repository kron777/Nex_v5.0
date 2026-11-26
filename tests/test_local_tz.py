"""NEX5_TZ — one clock for NEX's local-time behaviour."""
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
    def test_default_is_south_african_standard_time(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEX5_TZ", None)
            self.assertEqual(nex_config.local_tz().key, "Africa/Johannesburg")

    def test_env_override_and_invalid_value_fallback(self):
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Europe/Amsterdam"}):
            self.assertEqual(nex_config.local_tz().key, "Europe/Amsterdam")
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Not/A_Zone"}):
            nex_config._zone.cache_clear()
            with self.assertLogs("nex5.config", "WARNING"):
                self.assertEqual(nex_config.local_tz().key, "Africa/Johannesburg")

    def test_offset_uses_requested_zone_not_machine_zone(self):
        ts = _INSTANT.timestamp()
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Africa/Johannesburg"}):
            self.assertEqual(nex_config.local_utc_offset_seconds(ts), 2 * 3600)
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Europe/Amsterdam"}):
            self.assertEqual(nex_config.local_utc_offset_seconds(ts), 1 * 3600)

    def test_decoder_hour_features_follow_configured_zone(self):
        from theory_x.coincidence import decoder_loop as dl
        ts = _INSTANT.timestamp()
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Africa/Johannesburg"}):
            self.assertEqual(dl._local_hour_dow(ts), (18, 0))
        with mock.patch.dict(os.environ, {"NEX5_TZ": "Europe/Amsterdam"}):
            self.assertEqual(dl._local_hour_dow(ts), (17, 0))


class TestDailyScheduleTimezone(unittest.TestCase):
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

    def test_scheduled_activity_uses_the_configured_clock(self):
        hour, fired = self._fired("Africa/Johannesburg")
        self.assertEqual(hour, 18)
        self.assertIn("outreach_2", fired)
        self.assertNotIn("journal", fired)
        hour, fired = self._fired("Europe/Amsterdam")
        self.assertEqual(hour, 17)
        self.assertNotIn("outreach_2", fired)
        self.assertIn("reading_2", fired)


if __name__ == "__main__":
    unittest.main()
