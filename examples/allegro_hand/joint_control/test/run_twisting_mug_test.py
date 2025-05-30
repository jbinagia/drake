"""Simple regression test that the twisting_mug demo can perform at least one
twist.
"""

import hashlib
import os
import subprocess
import sys
import time
import unittest

from python.runfiles import Create as CreateRunfiles


def _unique_lcm_url(path):
    """Returns a unique LCM url given a path."""
    rand = [int(c) for c in hashlib.sha256(path.encode("utf8")).digest()]
    return "udpm://239.{:d}.{:d}.{:d}:{:d}?ttl=0".format(
        rand[0], rand[1], rand[2], 20000 + rand[3])


class TestRunTwistingMug(unittest.TestCase):

    def _find_resource(self, basename):
        respath = f"drake/examples/allegro_hand/joint_control/{basename}"
        runfiles = CreateRunfiles()
        result = runfiles.Rlocation(respath)
        self.assertTrue(result, respath)
        self.assertTrue(os.path.exists(result), respath)
        return result

    def setUp(self):
        self._test_tmpdir = os.environ["TEST_TMPDIR"]

        # Find the two binaries under test.
        self._sim = self._find_resource("allegro_single_object_simulation")
        self._control = self._find_resource("run_twisting_mug")

        # Let the sim and controller talk to (only) each other.
        self._env = dict(**os.environ)
        self._env["LCM_DEFAULT_URL"] = _unique_lcm_url(self._test_tmpdir)

    def test_only_sim(self):
        subprocess.run([
            self._sim, "--simulation_time=0.01"],
            env=self._env, cwd=self._test_tmpdir, check=True)

    @unittest.skipIf(
        "--compilation_mode=dbg" in sys.argv,
        "This test is prohibitively slow in Debug builds.")
    @unittest.skipIf(sys.platform == "darwin", "Not supported on macOS")
    def test_sim_and_control(self):
        # Run both the simulator and controller.
        sim_process = subprocess.Popen([
            self._sim, "--simulation_time=30"],
            env=self._env, cwd=self._test_tmpdir)
        control_process = subprocess.Popen([
            self._control, "--max_cycles=1"],
            env=self._env, cwd=self._test_tmpdir)

        # Wait until one of them exits.  Nominally the first to exit will be
        # the controller, once it finishes one twist.
        child_processes = [sim_process, control_process]
        while all([x.poll() is None for x in child_processes]):
            time.sleep(0.1)
        self.assertEqual(sim_process.returncode, None)
        self.assertEqual(control_process.returncode, 0)

        # Silence "subprocess is still running" warnings.
        sim_process.kill()
        control_process.kill()
        sim_process.wait(timeout=10.0)
        control_process.wait(timeout=10.0)
