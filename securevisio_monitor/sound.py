"""Sygnał dźwiękowy alarmu.

Dźwięk odtwarzany jest w pętli przez cały czas wyświetlania alarmu i milknie
przy jego zamknięciu. Dotyczy wyłącznie alarmów o nowym zdarzeniu - alarm
o zamkniętym środowisku pozostaje cichy.

Pliki dźwiękowe trzymane są w katalogu sounds/. Domyślny sygnał generowany
jest programowo przy pierwszym uruchomieniu, więc aplikacja działa od razu,
bez dostarczania jakichkolwiek plików z zewnątrz.
"""

from __future__ import annotations

import logging
import math
import shutil
import struct
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SOUNDS_DIR = Path("sounds")
DEFAULT_SOUND_NAME = "alarm_domyslny.wav"

_SAMPLE_RATE = 44100
_AMPLITUDE = 22000


def _generate_default_sound(path: Path) -> bool:
    """Tworzy domyślny sygnał alarmowy.

    Dźwięk to seria przemiatanych tonów w zakresie 700-1300 Hz - pasmo, na
    które ludzki słuch jest najbardziej wrażliwy, a zmienna wysokość jest
    trudniejsza do przespania niż ton stały.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        samples: list[int] = []
        sweep_duration = 0.45
        gap_duration = 0.15
        sweeps = 3

        for _ in range(sweeps):
            sweep_samples = int(_SAMPLE_RATE * sweep_duration)
            for i in range(sweep_samples):
                progress = i / sweep_samples
                frequency = 700 + (1300 - 700) * progress

                # Krótkie wybrzmienie na krańcach zapobiega trzaskom
                # na styku powtórzeń pętli.
                envelope = min(1.0, progress * 20, (1.0 - progress) * 20)

                value = math.sin(2 * math.pi * frequency * i / _SAMPLE_RATE)
                samples.append(int(_AMPLITUDE * value * envelope))

            samples.extend([0] * int(_SAMPLE_RATE * gap_duration))

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(_SAMPLE_RATE)
            wav_file.writeframes(
                b"".join(struct.pack("<h", s) for s in samples)
            )

        logger.debug("Wygenerowano domyślny dźwięk alarmu: %s", path)
        return True

    except Exception as exc:  # noqa: BLE001
        logger.warning("Nie udało się wygenerować domyślnego dźwięku: %s", exc)
        return False


def ensure_default_sound(sounds_dir: Path = SOUNDS_DIR) -> Optional[Path]:
    """Zapewnia istnienie domyślnego dźwięku, tworząc go w razie potrzeby."""
    path = sounds_dir / DEFAULT_SOUND_NAME
    if path.exists():
        return path
    return path if _generate_default_sound(path) else None


def list_available_sounds(sounds_dir: Path = SOUNDS_DIR) -> list[Path]:
    """Zwraca pliki .wav dostępne w katalogu dźwięków, posortowane po nazwie."""
    ensure_default_sound(sounds_dir)
    try:
        return sorted(sounds_dir.glob("*.wav"))
    except OSError as exc:
        logger.warning("Nie udało się odczytać katalogu dźwięków: %s", exc)
        return []


def import_sound(source: Path, sounds_dir: Path = SOUNDS_DIR) -> Optional[Path]:
    """Kopiuje wskazany plik .wav do katalogu dźwięków.

    Kopiowanie (zamiast zapamiętania ścieżki) chroni przed sytuacją, w której
    użytkownik wskaże plik z katalogu Pobrane, a następnie go usunie -
    alarm ucichłby wtedy bez żadnego ostrzeżenia.

    Returns:
        Ścieżka skopiowanego pliku albo None przy niepowodzeniu.
    """
    if source.suffix.lower() != ".wav":
        logger.warning("Odrzucono plik o nieobsługiwanym formacie: %s", source)
        return None

    try:
        sounds_dir.mkdir(parents=True, exist_ok=True)
        target = sounds_dir / source.name

        # Nie nadpisujemy istniejących plików - dokładamy numer do nazwy.
        counter = 1
        while target.exists() and target.resolve() != source.resolve():
            target = sounds_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1

        if target.resolve() == source.resolve():
            return target

        shutil.copy2(source, target)
        logger.debug("Zaimportowano dźwięk: %s", target)
        return target

    except OSError as exc:
        logger.warning("Nie udało się skopiować pliku dźwiękowego: %s", exc)
        return None


class AlarmSound:
    """Odtwarzanie dźwięku alarmu w pętli.

    Wykorzystuje QSoundEffect (obsługuje pętlę i regulację głośności).
    Gdy moduł multimediów Qt jest niedostępny, przechodzi na winsound
    z biblioteki standardowej - wtedy działa pętla, ale bez regulacji
    głośności.
    """

    def __init__(self) -> None:
        self._effect = None
        self._backend = "none"
        self._current_path: Optional[Path] = None
        self._volume = 0.8
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            from PySide6.QtMultimedia import QSoundEffect

            self._effect = QSoundEffect()
            self._effect.setLoopCount(QSoundEffect.Infinite)
            self._effect.setVolume(self._volume)
            self._backend = "qt"
            return
        except Exception as exc:  # noqa: BLE001
            logger.debug("QSoundEffect niedostępny (%s), próbuję winsound.", exc)

        try:
            import winsound  # noqa: F401

            self._backend = "winsound"
        except ImportError:
            logger.warning("Brak dostępnego mechanizmu odtwarzania dźwięku.")
            self._backend = "none"

    @property
    def is_available(self) -> bool:
        return self._backend != "none"

    @property
    def supports_volume(self) -> bool:
        """winsound nie pozwala regulować głośności z poziomu aplikacji."""
        return self._backend == "qt"

    def set_volume(self, volume: float) -> None:
        """Ustawia głośność w zakresie 0.0-1.0 (względem głośności systemu)."""
        self._volume = max(0.0, min(1.0, volume))
        if self._backend == "qt" and self._effect is not None:
            self._effect.setVolume(self._volume)

    def play(self, path: Optional[Path]) -> None:
        """Rozpoczyna odtwarzanie w pętli."""
        if not self.is_available or path is None:
            return

        if not path.exists():
            logger.warning("Plik dźwiękowy nie istnieje: %s", path)
            return

        try:
            if self._backend == "qt":
                from PySide6.QtCore import QUrl

                if self._current_path != path:
                    self._effect.setSource(QUrl.fromLocalFile(str(path.resolve())))
                    self._current_path = path
                self._effect.setVolume(self._volume)
                self._effect.play()
            else:
                import winsound

                winsound.PlaySound(
                    str(path.resolve()),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
                )
        except Exception as exc:  # noqa: BLE001
            # Brak dźwięku nie może przeszkodzić w wyświetleniu alarmu.
            logger.warning("Nie udało się odtworzyć dźwięku alarmu: %s", exc)

    def stop(self) -> None:
        """Zatrzymuje odtwarzanie."""
        if not self.is_available:
            return

        try:
            if self._backend == "qt" and self._effect is not None:
                self._effect.stop()
            else:
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Błąd zatrzymywania dźwięku: %s", exc)