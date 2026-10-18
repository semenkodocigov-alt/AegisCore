import os
import sys
import unittest
from unittest.mock import patch

import privileges


@unittest.skipUnless(os.name == "nt", "Windows privilege APIs are only available on Windows")
class PrivilegeTests(unittest.TestCase):
    def test_admin_check_reads_windows_token_status(self):
        with patch.object(privileges.ctypes.windll.shell32, "IsUserAnAdmin", return_value=1):
            self.assertTrue(privileges.is_admin())

    def test_elevation_relaunch_uses_runas_and_preserves_arguments(self):
        with patch.object(privileges.ctypes.windll.shell32, "ShellExecuteW", return_value=33) as execute:
            with patch.object(sys, "frozen", False, create=True), patch.object(
                sys, "argv", ["main.py", "--scan", "C:\\test file.exe"]
            ):
                self.assertTrue(privileges.request_admin_elevation(sys.argv[1:]))

        self.assertEqual(execute.call_args.args[1], "runas")
        self.assertTrue(execute.call_args.args[3].endswith('--scan "C:\\test file.exe"'))

    def test_elevation_reports_when_windows_does_not_start_relaunch(self):
        with patch.object(privileges.ctypes.windll.shell32, "ShellExecuteW", return_value=5):
            self.assertFalse(privileges.request_admin_elevation([]))


if __name__ == "__main__":
    unittest.main()
