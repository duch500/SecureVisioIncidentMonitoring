"""Wykrywanie pliku ikony aplikacji.

Ikona może mieć dowolną nazwę - użytkownik po prostu wrzuca plik .ico do
katalogu programu. Szukamy pierwszego pasującego pliku, żeby nie wymuszać
konkretnej nazwy.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Katalogi pomijane przy szukaniu - dane robocze programu, nie miejsce na ikonę.
_SKIP_DIRS = {"logs", "sounds", "build", "dist", "__pycache__", ".git"}


def find_icon(base_dir: Path = Path(".")) -> Optional[Path]:
    """Szuka pliku .ico w katalogu programu (bez podkatalogów).

    Gdy jest więcej niż jeden plik .ico, wybierany jest pierwszy alfabetycznie -
    zachowanie deterministyczne, żeby przy dwóch plikach nie zmieniało się
    losowo między uruchomieniami.

    Args:
        base_dir: Katalog, w którym szukamy. Domyślnie katalog roboczy
            (czyli katalog programu przy normalnym uruchomieniu).

    Returns:
        Ścieżka do pliku ikony albo None, gdy żadnego nie znaleziono.
    """
    try:
        candidates = sorted(base_dir.glob("*.ico"))
    except OSError as exc:
        logger.debug("Nie udało się przeszukać katalogu w poszukiwaniu ikony: %s", exc)
        return None

    if not candidates:
        return None

    if len(candidates) > 1:
        logger.debug(
            "Znaleziono %d plików .ico, używam pierwszego: %s",
            len(candidates), candidates[0].name,
        )

    return candidates[0]