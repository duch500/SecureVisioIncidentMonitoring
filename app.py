"""Punkt wejścia aplikacji SecureVisio Monitor.

URUCHOMIENIE:
    python app.py
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from securevisio_monitor.config import ConfigError, load_settings
from securevisio_monitor.gui.main_window import MainWindow
from securevisio_monitor.icon import find_icon
from securevisio_monitor.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()

    # PassThrough zapobiega zaokrąglaniu skali DPI, przez które geometria okien
    # alarmu mogłaby nie pokrywać całych ekranów przy skalowaniu innym niż 100%.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SecureVisio Monitor")

    # Ikona może mieć dowolną nazwę - wystarczy wrzucić plik .ico do katalogu
    # programu. Brak takiego pliku nie jest błędem - program działa z ikoną
    # domyślną Qt.
    icon_path = find_icon()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
        logger.debug("Użyto ikony: %s", icon_path)

    # Zamknięcie okna alarmu nie może kończyć aplikacji - alarmy pojawiają się
    # i znikają wielokrotnie w trakcie pracy.
    app.setQuitOnLastWindowClosed(False)

    try:
        settings = load_settings()
    except ConfigError as exc:
        logger.error("Błąd konfiguracji: %s", exc)
        QMessageBox.critical(
            None,
            "Błąd konfiguracji",
            f"Nie udało się wczytać ustawień:\n\n{exc}\n\n"
            "Uruchamiam z ustawieniami domyślnymi.",
        )
        from securevisio_monitor.config import AppSettings

        settings = AppSettings()

    window = MainWindow(settings)
    window.show()

    # Aplikacja kończy się dopiero po zamknięciu okna głównego.
    window.destroyed.connect(app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())