"""Weryfikacja wersji demonstracyjnej w osobnym wątku.

Zapytanie do serwera czasu może potrwać kilka sekund (timeout na serwer razy
liczba serwerów do wypróbowania), dlatego sprawdzenie nie może blokować wątku
GUI - okno musiałoby "zamarznąć" na czas trwania zapytania. Wzorzec identyczny
jak w worker.py: praca w tle, wynik przekazany do wątku głównego przez sygnał.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from .guard import LicenseCheckResult, check_license

logger = logging.getLogger(__name__)


class LicenseCheckWorker(QThread):
    """Wykonuje jednorazową weryfikację wersji demonstracyjnej w tle."""

    finished_check = Signal(object)  # LicenseCheckResult

    def run(self) -> None:  # noqa: D102 - API QThread
        try:
            result = check_license()
        except Exception as exc:  # noqa: BLE001 - wątek nie może umrzeć bez wyniku
            logger.exception("Nieoczekiwany błąd weryfikacji licencji: %s", exc)
            result = LicenseCheckResult(
                decision=None,  # type: ignore[arg-type]
                time_result=None,
                final_allowed=False,
                message=(
                    "Nie udało się zweryfikować wersji demonstracyjnej "
                    "z powodu nieoczekiwanego błędu."
                ),
            )
        self.finished_check.emit(result)