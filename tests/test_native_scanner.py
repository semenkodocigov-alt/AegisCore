import hashlib
import math
import os
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import native_scanner
from analyzer import FileAnalyzer
from hash_utils import calculate_all_with_entropy
from scanner import FileScanner


class NativeScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="aegis-native-test-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_hashing_entropy_and_directory_python_fallback(self):
        target = self.root / "sample.bin"
        payload = bytes(range(256)) * 50
        target.write_bytes(payload)

        original_native = native_scanner._native
        original_attempted = native_scanner._attempted_load
        try:
            native_scanner._native = None
            native_scanner._attempted_load = True
            hashes, entropy = calculate_all_with_entropy(str(target))
            self.assertEqual(hashes, {
                "md5": hashlib.md5(payload).hexdigest(),
                "sha1": hashlib.sha1(payload).hexdigest(),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
            sample = payload[:10_000]
            expected_entropy = -sum(
                (count / len(sample)) * math.log2(count / len(sample))
                for count in Counter(sample).values()
            )
            self.assertAlmostEqual(entropy, expected_entropy)
            self.assertAlmostEqual(FileAnalyzer()._calculate_entropy(bytes(range(256))), 8.0)
            self.assertIsNone(
                native_scanner.walk_directory(
                    str(self.root), 0, 10, lambda path: bool(path)
                )
            )
        finally:
            native_scanner._native = original_native
            native_scanner._attempted_load = original_attempted

    def test_native_hash_signature_and_bounded_walk(self):
        if not native_scanner.is_available():
            self.skipTest("A supported C++ compiler or prebuilt native DLL is unavailable")

        target = self.root / "проверка.bin"
        payload = bytes(range(256)) * 50
        target.write_bytes(payload)
        native_result = native_scanner.calculate_file(str(target))
        self.assertIsNotNone(native_result)
        hashes, entropy = native_result
        self.assertEqual(hashes, {
            "md5": hashlib.md5(payload).hexdigest(),
            "sha1": hashlib.sha1(payload).hexdigest(),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
        sample = payload[:10_000]
        expected_entropy = -sum(
            (count / len(sample)) * math.log2(count / len(sample))
            for count in Counter(sample).values()
        )
        self.assertAlmostEqual(entropy, expected_entropy)

        index = native_scanner.NativeSignatureIndex(SimpleNamespace(
            signatures={hashes["sha256"]: {"name": "native test signature"}}
        ))
        try:
            self.assertEqual(index.match(hashes), {"name": "native test signature"})
        finally:
            index.close()

        (self.root / "nested").mkdir()
        (self.root / "nested" / "ignored.bin").write_bytes(b"nested")
        visited = []
        self.assertEqual(
            native_scanner.walk_directory(
                str(self.root) + os.sep, 0, 10, lambda path: visited.append(path) or True
            ),
            1,
        )
        self.assertEqual(visited, [str(target)])

    def test_scanner_uses_native_signature_index(self):
        if not native_scanner.is_available():
            self.skipTest("A supported C++ compiler or prebuilt native DLL is unavailable")

        target = self.root / "sample.txt"
        target.write_bytes(b"signature match")
        hashes, _ = calculate_all_with_entropy(str(target))
        database = SimpleNamespace(
            signatures={hashes["sha256"]: {"name": "native signature"}},
            _is_whitelisted=lambda _filename, _filepath: False,
            check_hash=lambda **kwargs: self.fail(f"Python signature matcher used: {kwargs}"),
        )
        scanner = FileScanner.__new__(FileScanner)
        scanner.sig_db = database
        scanner.analyzer = None
        scanner._native_signature_lock = threading.Lock()
        scanner._native_signature_index = None
        scanner._native_signature_unavailable = False
        try:
            result = scanner.scan_file(str(target))
            self.assertTrue(result["is_threat"])
            self.assertEqual(result["threat_name"], "native signature")
        finally:
            if scanner._native_signature_index is not None:
                scanner._native_signature_index.close()


if __name__ == "__main__":
    unittest.main()
