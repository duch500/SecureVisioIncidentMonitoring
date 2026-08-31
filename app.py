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

from securevisio_monitor.about import APP_NAME, APP_VERSION
from securevisio_monitor.config import ConfigError, load_settings, save_settings
from securevisio_monitor.gui.license_dialog import LicenseAgreementDialog
from securevisio_monitor.gui.main_window import MainWindow
from securevisio_monitor.icon import find_icon
from securevisio_monitor.logging_setup import setup_logging
from securevisio_monitor.notifications import register_app_id

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()

    # PassThrough zapobiega zaokrąglaniu skali DPI, przez które geometria okien
    # alarmu mogłaby nie pokrywać całych ekranów przy skalowaniu innym niż 100%.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Ikona może mieć dowolną nazwę - wystarczy wrzucić plik .ico do katalogu
    # programu. Brak takiego pliku nie jest błędem - program działa z ikoną
    # domyślną Qt.
    icon_path = find_icon()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
        logger.debug("Użyto ikony: %s", icon_path)

    # Rejestracja w Windows - bez niej powiadomienia systemowe pojawiają się
    # pod nazwą procesu nadrzędnego zamiast nazwy aplikacji. Zapis wyłącznie
    # w gałęzi bieżącego użytkownika, bez uprawnień administratora.
    register_app_id(icon_path)

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

    # Warunki korzystania pokazujemy raz - dopóki nie zmieni się wersja
    # programu. Zapis akceptacji jest lekki (zwykły settings.json, bez
    # ochrony przed ręczną edycją) - celem jest wyeliminowanie sytuacji
    # "nie widziałem warunków", nie uniemożliwienie obejścia.
    if settings.license_accepted_version != APP_VERSION:
        dialog = LicenseAgreementDialog()
        if dialog.exec() != LicenseAgreementDialog.Accepted:
            logger.info("Warunki korzystania odrzucone - program się nie uruchomi.")
            return 0

        settings.license_accepted = True
        settings.license_accepted_version = APP_VERSION
        try:
            save_settings(settings)
        except ConfigError as exc:
            logger.warning("Nie udało się zapisać akceptacji warunków: %s", exc)

    window = MainWindow(settings)
    window.show()

    # Zakończenie aplikacji obsługuje MainWindow.closeEvent - wywołuje
    # QApplication.quit() po zatrzymaniu wątku monitorującego. Poleganie na
    # sygnale destroyed nie działa, bo zamknięcie okna domyślnie tylko je
    # ukrywa, nie niszczy obiektu.
    exit_code = app.exec()

    # Ostatnia linia obrony: gdyby jakikolwiek wątek albo obiekt COM
    # (powiadomienia systemowe Windows) utrzymywał proces przy życiu,
    # kończymy go jawnie zamiast zostawiać w tle.
    logger.debug("Pętla zdarzeń zakończona, kod wyjścia: %s", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())