"""Wykrywanie pliku ikony aplikacji.

Ikona może mieć dowolną nazwę - użytkownik po prostu wrzuca plik .ico do
katalogu programu. Szukamy pierwszego pasującego pliku, żeby nie wymuszać
konkretnej nazwy.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Katalogi pomijane przy szukaniu - dane robocze programu, nie miejsce na ikonę.
_SKIP_DIRS = {"logs", "sounds", "build", "dist", "__pycache__", ".git"}


def get_app_dir() -> Path:
    """Zwraca katalog, w którym faktycznie znajduje się uruchomiony program.

    To NIE jest to samo co katalog roboczy procesu (Path(".")) - ten zależy
    od tego, skąd i jak program został uruchomiony (np. "Start in" skrótu,
    katalog aktywny w terminalu), i bywa inny niż katalog z plikami programu.
    Szukanie względem katalogu roboczego jest częstą przyczyną tego, że plik
    leżący "obok" programu nie zostaje znaleziony.

    W wersji spakowanej PyInstallerem (--onefile) zwraca katalog zawierający
    plik .exe, a nie tymczasowy katalog rozpakowania (sys._MEIPASS) - ikona
    ma być plikiem obok .exe, widocznym i podmienialnym przez użytkownika,
    a nie zaszytym wewnątrz archiwum.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # __file__ tego modułu to securevisio_monitor/icon.py - katalog programu
    # to jeden poziom wyżej (tam, gdzie leży app.py).
    return Path(__file__).resolve().parent.parent


def find_icon(base_dir: Optional[Path] = None) -> Optional[Path]:
    """Szuka pliku .ico w katalogu programu (bez podkatalogów).

    Gdy jest więcej niż jeden plik .ico, wybierany jest pierwszy alfabetycznie -
    zachowanie deterministyczne, żeby przy dwóch plikach nie zmieniało się
    losowo między uruchomieniami.

    Args:
        base_dir: Katalog, w którym szukamy. Domyślnie katalog programu
            (get_app_dir()) - NIE katalog roboczy procesu, żeby wynik nie
            zależał od tego, skąd program został uruchomiony.

    Returns:
        Ścieżka do pliku ikony albo None, gdy żadnego nie znaleziono.
    """
    if base_dir is None:
        base_dir = get_app_dir()

    try:
        candidates = sorted(base_dir.glob("*.ico"))
    except OSError as exc:
        logger.debug("Nie udało się przeszukać katalogu w poszukiwaniu ikony: %s", exc)
        return None

    if not candidates:
        logger.debug("Brak pliku .ico w katalogu programu: %s", base_dir)
        return None

    if len(candidates) > 1:
        logger.debug(
            "Znaleziono %d plików .ico, używam pierwszego: %s",
            len(candidates), candidates[0].name,
        )

    return candidates[0]