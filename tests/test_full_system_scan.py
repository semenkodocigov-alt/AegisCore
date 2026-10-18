import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from scanner import FileScanner


class FullSystemScanTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="aegis-full-scan-")
        self.root = Path(self.temp_dir.name)
        (self.root / "nested").mkdir()
        (self.root / "first.bin").write_bytes(b"first")
        (self.root / "nested" / "second.bin").write_bytes(b"second")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scans_all_regular_files_and_reports_live_progress(self):
        scanner = FileScanner()
        progress = []
        results = []
        try:
            with patch("scanner._full_system_scan_roots", return_value=[str(self.root)]):
                summary = scanner.scan_full_system(
                    progress_callback=lambda path, threat, count, total: progress.append(
                        (path, threat, count, total)
                    ),
                    result_callback=results.append,
                )

            self.assertEqual(summary["files_scanned"], 2)
            self.assertEqual(summary["files_discovered"], 2)
            self.assertFalse(summary["cancelled"])
            self.assertEqual({item["filepath"] for item in results}, {
                str(self.root / "first.bin"),
                str(self.root / "nested" / "second.bin"),
            })
            self.assertEqual([item[2] for item in progress], [1, 2])
            self.assertEqual(progress[-1][3], 2)
        finally:
            scanner.shutdown()

    def test_scan_waits_while_paused_and_resumes(self):
        scanner = FileScanner()
        resume_event = threading.Event()
        completed = threading.Event()
        outcome = []

        def scan() -> None:
            with patch("scanner._full_system_scan_roots", return_value=[str(self.root)]):
                outcome.append(scanner.scan_full_system(resume_event=resume_event))
            completed.set()

        thread = threading.Thread(target=scan, daemon=True)
        try:
            thread.start()
            time.sleep(0.1)
            self.assertFalse(completed.is_set())
            resume_event.set()
            thread.join(timeout=5)
            self.assertTrue(completed.is_set())
            self.assertEqual(outcome[0]["files_scanned"], 2)
        finally:
            resume_event.set()
            scanner.shutdown()


if __name__ == "__main__":
    unittest.main()
