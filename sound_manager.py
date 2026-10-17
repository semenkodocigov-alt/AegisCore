"""Cross-platform sound playback manager.

Uses platform-native APIs: winsound on Windows, afplay on macOS,
beep/paplay on Linux. All calls are non-blocking and safe
(subprocess.Popen instead of os.system).
"""
import logging
import subprocess
import threading
import platform
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Shared sound-type → platform-specific mapping definitions
_WINDOWS_ALIAS_MAP: Dict[str, str] = {
    "threat": "SystemHand",
    "warning": "SystemExclamation",
    "success": "SystemAsterisk",
    "question": "SystemQuestion",
    "notification": "SystemDefault",
    "error": "SystemHand",
}

_MACOS_SOUND_MAP: Dict[str, str] = {
    "threat": "Glass",
    "warning": "Blow",
    "success": "Ping",
    "question": "Morse",
    "notification": "Bottle",
    "error": "Sosumi",
}

_LINUX_FREQ_MAP: Dict[str, int] = {
    "threat": 1000,
    "warning": 800,
    "success": 1200,
    "question": 600,
    "notification": 900,
    "error": 500,
}


class SoundManager:
    """Cross-platform sound manager with async playback support."""

    def __init__(self, enable_sound: bool = True) -> None:
        """Initialize the sound manager.

        Args:
            enable_sound: Whether sound playback is enabled.
        """
        self.enabled: bool = enable_sound
        self.system: str = platform.system()
        self.sound_cache: Dict[str, object] = {}

        # Lazy-load winsound on Windows
        self.has_winsound: bool = False
        self.winsound = None
        if self.system == "Windows":
            try:
                import winsound
                self.winsound = winsound
                self.has_winsound = True
            except ImportError:
                logger.debug("winsound module not available")

    def play_async(self, sound_type: str = "notification") -> None:
        """Play a sound asynchronously in a daemon thread.

        Args:
            sound_type: One of 'threat', 'warning', 'success',
                        'question', 'notification', 'error'.
        """
        if not self.enabled:
            return
        thread = threading.Thread(
            target=self._play_sound_internal,
            args=(sound_type,),
            daemon=True,
        )
        thread.start()

    def play_sync(self, sound_type: str = "notification") -> None:
        """Play a sound synchronously (blocks until finished).

        Args:
            sound_type: One of 'threat', 'warning', 'success',
                        'question', 'notification', 'error'.
        """
        if not self.enabled:
            return
        self._play_sound_internal(sound_type)

    def _play_sound_internal(self, sound_type: str) -> None:
        """Route sound playback to the platform-specific implementation."""
        try:
            if self.system == "Windows":
                self._play_windows_sound(sound_type)
            elif self.system == "Darwin":
                self._play_macos_sound(sound_type)
            elif self.system == "Linux":
                self._play_linux_sound(sound_type)
        except Exception as e:
            # Sound errors are non-critical; log and continue
            logger.debug("Sound playback error: %s", e)

    def _play_windows_sound(self, sound_type: str) -> None:
        """Play a system sound on Windows via winsound."""
        if not self.has_winsound or self.winsound is None:
            return

        sound_alias = _WINDOWS_ALIAS_MAP.get(sound_type, "SystemDefault")
        try:
            self.winsound.PlaySound(
                sound_alias,
                self.winsound.SND_ALIAS | self.winsound.SND_ASYNC,
            )
        except RuntimeError:
            # Alias not available — fall back to MessageBeep
            try:
                beep_map = {
                    "threat": self.winsound.MB_ICONHAND,
                    "warning": self.winsound.MB_ICONEXCLAMATION,
                    "success": self.winsound.MB_ICONASTERISK,
                    "question": self.winsound.MB_ICONQUESTION,
                    "notification": 0,
                    "error": self.winsound.MB_ICONHAND,
                }
                beep_type = beep_map.get(sound_type, 0)
                if beep_type:
                    self.winsound.MessageBeep(beep_type)
                else:
                    self.winsound.Beep(1000, 200)
            except (RuntimeError, OSError) as e:
                logger.debug("Windows beep fallback failed: %s", e)
        except (AttributeError, OSError) as e:
            logger.debug("Windows sound playback failed: %s", e)

    def _play_macos_sound(self, sound_type: str) -> None:
        """Play a system sound on macOS via afplay (no shell injection)."""
        sound_name = _MACOS_SOUND_MAP.get(sound_type, "Bottle")
        sound_path = f"/System/Library/Sounds/{sound_name}.aiff"
        try:
            # subprocess.Popen with list args — safe, non-blocking
            subprocess.Popen(
                ["afplay", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.debug("afplay not found on this system")
        except OSError as e:
            logger.debug("macOS sound playback failed: %s", e)

    def _play_linux_sound(self, sound_type: str) -> None:
        """Play a beep on Linux via the beep utility (no shell injection)."""
        freq = _LINUX_FREQ_MAP.get(sound_type, 900)
        try:
            # subprocess.Popen with list args — safe, non-blocking
            subprocess.Popen(
                ["beep", "-f", str(freq), "-l", "200"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.debug("beep utility not found on this system")
        except OSError as e:
            logger.debug("Linux sound playback failed: %s", e)

    def test_sound(self) -> bool:
        """Test sound playback with a notification sound.

        Returns True (always succeeds; errors are logged silently).
        """
        logger.info("Testing sound playback...")
        self.play_sync("notification")
        return True


# ---------------------------------------------------------------------------
# Thread-safe singleton
# ---------------------------------------------------------------------------

_sound_manager: Optional[SoundManager] = None
_sound_lock = threading.Lock()


def get_sound_manager(enable: bool = True) -> SoundManager:
    """Get the global SoundManager singleton (thread-safe).

    Args:
        enable: Whether sound is enabled (used only on first call).
    """
    global _sound_manager
    if _sound_manager is None:
        with _sound_lock:
            if _sound_manager is None:
                _sound_manager = SoundManager(enable)
    return _sound_manager
