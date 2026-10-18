import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import desktop_app


@unittest.skipUnless(os.name == "nt", "Native window dragging is Windows-only")
class NativeWindowDragTests(unittest.TestCase):
    def test_sends_caption_drag_messages_to_native_window_handle(self):
        bridge = desktop_app.AegisDesktopBridge.__new__(desktop_app.AegisDesktopBridge)
        bridge.window = SimpleNamespace(
            native=SimpleNamespace(Handle=SimpleNamespace(ToInt32=lambda: 12345))
        )
        user32 = SimpleNamespace(ReleaseCapture=Mock(), SendMessageW=Mock())

        with patch.object(desktop_app.ctypes, "windll", SimpleNamespace(user32=user32)):
            bridge.start_native_drag()

        user32.ReleaseCapture.assert_called_once_with()
        user32.SendMessageW.assert_called_once_with(12345, 0x00A1, 2, 0)


if __name__ == "__main__":
    unittest.main()
