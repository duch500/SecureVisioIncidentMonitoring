"""Konfiguracja logowania aplikacji.

Logi trafiają jednocześnie do pliku (z rotacją) i na konsolę. Plik jest
podstawą diagnostyki po fakcie - gdy alarm zadziała w nocy, rano trzeba móc
sprawdzić, co dokładnie zostało odczytane i kiedy.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_PATH = Path("logs") / "monitor.log"

# Świadomie mały budżet dyskowy: 256 KB na plik i jedna kopia zapasowa,
# czyli maksymalnie ~512 KB niezależnie od czasu pracy monitora. To wystarcza
# na kilka tysięcy wpisów wstecz - w praktyce diagnostyka dotyczy ostatnich
# godzin, nie tygodni.
MAX_BYTES = 256 * 1024
BACKUP_COUNT = 1

_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def setup_logging(
    log_path: Path = DEFAULT_LOG_PATH,
    level: int = logging.WARNING,
    console: bool = False,
) -> None:
    """Konfiguruje logowanie dla całej aplikacji.

    Domyślnie zapisywane są wyłącznie ostrzeżenia i błędy - normalna praca
    monitora nie generuje wtedy żadnych wpisów. Zdarzenia i przebieg pracy
    widoczne są na bieżąco w oknie aplikacji; plik służy do diagnostyki
    problemów, a nie do prowadzenia historii.

    Args:
        log_path: Ścieżka pliku logu. Katalog nadrzędny jest tworzony w razie potrzeby.
        level: Poziom logowania. logging.INFO lub DEBUG włącza tryb diagnostyczny -
            znacznie bardziej szczegółowy, przeznaczony do doraźnego użycia.
        console: Czy dublować logi na konsolę. Przy uruchomieniu jako .exe
            bez konsoli nie ma to znaczenia.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Usuwamy istniejące handlery - zapobiega podwójnym wpisom przy ponownej
    # konfiguracji (np. po zmianie poziomu logowania w GUI).
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:
        # Brak prawa zapisu nie może uniemożliwić uruchomienia monitora -
        # na komputerze zarządzanym przez organizację to realny scenariusz.
        print(f"Ostrzeżenie: nie można zapisywać logów do {log_path}: {exc}")

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    # Biblioteka comtypes (używana przez uiautomation) loguje bardzo obszernie
    # na poziomie DEBUG - wyciszamy, żeby nie zagłuszała naszych komunikatów.
    logging.getLogger("comtypes").setLevel(logging.WARNING)


def set_debug_mode(enabled: bool) -> None:
    """Przełącza tryb diagnostyczny w czasie działania.

    Włączony zapisuje szczegółowy przebieg każdego cyklu (przydatne przy
    diagnozowaniu problemu z konkretnym środowiskiem), wyłączony wraca do
    zapisywania wyłącznie ostrzeżeń i błędów.
    """
    logging.getLogger().setLevel(logging.DEBUG if enabled else logging.WARNING)