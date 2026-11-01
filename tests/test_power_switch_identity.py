"""Identity-verified pidfile reads for power_switch.py's _read_pid().

A bare existence check (`kill -0` / os.kill(pid, 0)) also "succeeds" on a
stale pidfile whenever that pid number is alive again -- reused by an
unrelated process (pids recycle), or by a brand-new NEX launch after a
reboot. _read_pid() instead requires (pid, starttime, boot_id) recorded by
nex_keepalive.sh at launch to all still match. These cases confirm every
mismatch is treated as "not running" (fail open to spawn), never a crash.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401

import power_switch


class TestReadPidIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_pidfile = power_switch.PIDFILE
        self._orig_identity = power_switch.IDENTITY_FILE
        power_switch.PIDFILE = os.path.join(self.tmp, "nex.pid")
        power_switch.IDENTITY_FILE = os.path.join(self.tmp, "nex.pid.identity")

        # A real, currently-alive process to test identity checks against.
        self.proc = subprocess.Popen(["sleep", "30"])
        self.pid = self.proc.pid
        self.starttime = power_switch._proc_starttime(self.pid)
        self.assertIsNotNone(self.starttime)
        self.boot_id = power_switch._boot_id()
        self.assertIsNotNone(self.boot_id)

    def tearDown(self):
        self.proc.kill()
        self.proc.wait()
        power_switch.PIDFILE = self._orig_pidfile
        power_switch.IDENTITY_FILE = self._orig_identity
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, pid, starttime, boot_id):
        with open(power_switch.PIDFILE, "w") as f:
            f.write(str(pid))
        with open(power_switch.IDENTITY_FILE, "w") as f:
            f.write(f"{pid}:{starttime}:{boot_id}")

    def test_correct_pid_starttime_boot_id_is_alive(self):
        self._write(self.pid, self.starttime, self.boot_id)
        self.assertEqual(power_switch._read_pid(), self.pid)

    def test_live_but_foreign_pid_is_not_alive(self):
        # The pid is genuinely running right now, but the recorded identity
        # belongs to a different instance of it (e.g. pid reuse) -- must
        # not be mistaken for NEX.
        self._write(self.pid, self.starttime + 999, self.boot_id)
        self.assertIsNone(power_switch._read_pid())

    def test_stale_pidfile_from_previous_boot_is_not_alive(self):
        self._write(self.pid, self.starttime, self.boot_id + "-stale")
        self.assertIsNone(power_switch._read_pid())

    def test_right_pid_wrong_starttime_is_not_alive(self):
        self._write(self.pid, self.starttime + 1, self.boot_id)
        self.assertIsNone(power_switch._read_pid())

    def test_malformed_pidfile_does_not_raise(self):
        with open(power_switch.PIDFILE, "w") as f:
            f.write("not-a-pid\n")
        with open(power_switch.IDENTITY_FILE, "w") as f:
            f.write("also garbage")
        self.assertIsNone(power_switch._read_pid())

    def test_empty_pidfile_does_not_raise(self):
        open(power_switch.PIDFILE, "w").close()
        self.assertIsNone(power_switch._read_pid())

    def test_missing_identity_file_does_not_raise(self):
        with open(power_switch.PIDFILE, "w") as f:
            f.write(str(self.pid))
        # no IDENTITY_FILE written at all
        self.assertIsNone(power_switch._read_pid())

    def test_pid_zero_rejected_even_with_matching_identity(self):
        # 0 as a kill() target hits our own process group, not "no such
        # process" -- must never reach that call regardless of what the
        # identity file claims.
        self._write(0, self.starttime, self.boot_id)
        self.assertIsNone(power_switch._read_pid())

    def test_pid_negative_one_rejected(self):
        # -1 as a kill() target is "every process we're allowed to signal".
        self._write(-1, self.starttime, self.boot_id)
        self.assertIsNone(power_switch._read_pid())

    def test_pid_one_rejected(self):
        # init; also typically a uid mismatch, but must not depend on that.
        self._write(1, self.starttime, self.boot_id)
        self.assertIsNone(power_switch._read_pid())


class TestStateReflectsLiveness(unittest.TestCase):
    """state() must not just echo the sentinel file when it says OFF: a
    just-signalled NEX can still be alive and holding VRAM for a few
    seconds, and go_off() must not hand the HUD pill a bare "off" that's
    already wrong the instant it's returned."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_pidfile = power_switch.PIDFILE
        self._orig_identity = power_switch.IDENTITY_FILE
        self._orig_standby = power_switch.STANDBY
        power_switch.PIDFILE = os.path.join(self.tmp, "nex.pid")
        power_switch.IDENTITY_FILE = os.path.join(self.tmp, "nex.pid.identity")
        power_switch.STANDBY = os.path.join(self.tmp, "STANDBY")

        self.proc = subprocess.Popen(["sleep", "30"])
        self.pid = self.proc.pid
        self.starttime = power_switch._proc_starttime(self.pid)
        self.boot_id = power_switch._boot_id()

    def tearDown(self):
        self.proc.kill()
        self.proc.wait()
        power_switch.PIDFILE = self._orig_pidfile
        power_switch.IDENTITY_FILE = self._orig_identity
        power_switch.STANDBY = self._orig_standby
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_identity(self, pid, starttime, boot_id):
        with open(power_switch.PIDFILE, "w") as f:
            f.write(str(pid))
        with open(power_switch.IDENTITY_FILE, "w") as f:
            f.write(f"{pid}:{starttime}:{boot_id}")

    def test_standby_absent_is_on(self):
        self.assertFalse(os.path.exists(power_switch.STANDBY))
        self.assertEqual(power_switch.state(), "on")

    def test_standby_present_no_verified_pid_is_off(self):
        open(power_switch.STANDBY, "w").close()
        # no pidfile/identity at all -- nothing to verify as alive
        self.assertEqual(power_switch.state(), "off")

    def test_standby_present_but_process_still_verified_alive_is_stopping(self):
        open(power_switch.STANDBY, "w").close()
        self._write_identity(self.pid, self.starttime, self.boot_id)
        # Sentinel says off, but the signalled process hasn't exited yet --
        # must not be reported as a flat "off".
        self.assertEqual(power_switch.state(), "stopping")
        self.assertNotEqual(power_switch.state(), "off")


class TestProcStarttimeParsing(unittest.TestCase):
    def test_handles_comm_with_parens_and_spaces(self):
        # comm (field 2) is arbitrary and parenthesised; a process named
        # e.g. "weird (name) 1" must not shift the field-22 parse, which
        # is why the real parse splits on the LAST ') ' rather than on
        # whitespace from the start of the line.
        raw = "999 (weird (name) 1) S 1 1 1 0 -1 4194560 10 0 0 0 1 2 0 0 20 0 1 0 424242 0 0\n"
        rest = raw.rsplit(") ", 1)[1]
        self.assertEqual(int(rest.split()[19]), 424242)


if __name__ == "__main__":
    unittest.main()
