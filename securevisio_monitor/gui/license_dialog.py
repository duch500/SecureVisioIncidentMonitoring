"""Okno akceptacji warunków korzystania.

Pokazywane przed uruchomieniem okna głównego, jednorazowo - dopóki nie zmieni
się wersja programu. Treść pochodzi z pliku LICENCJA.txt leżącego obok
programu, więc edycja tego pliku od razu odzwierciedla się w oknie, bez
zmian w kodzie.

To jest lekkie zabezpieczenie: zapis akceptacji trafia do zwykłego
settings.json, bez żadnej ochrony przed ręczną edycją. Celem nie jest
uniemożliwienie obejścia, tylko wyeliminowanie sytuacji "nie widziałem
warunków" - każdy uruchamiający program raz je zobaczy i świadomie zaakceptuje
albo odrzuci.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..icon import get_app_dir

logger = logging.getLogger(__name__)

LICENSE_FILE_NAME = "LICENCJA.txt"

# Pokazywany wyłącznie, gdy plik LICENCJA.txt nie zostanie znaleziony -
# program i tak wymaga jawnej akceptacji przed startem, nawet bez pliku.
_FALLBACK_TEXT = (
    "Nie znaleziono pliku LICENCJA.txt obok programu.\n\n"
    "Mimo to potwierdź, że wiesz, iż korzystasz z tego programu na "
    "odpowiedzialność własną i zgodnie z ustaleniami z jego autorem."
)


def find_license_file() -> Optional[Path]:
    """Szuka pliku LICENCJA.txt w katalogu programu."""
    path = get_app_dir() / LICENSE_FILE_NAME
    return path if path.exists() else None


def _read_license_text() -> str:
    path = find_license_file()
    if path is None:
        logger.warning("Nie znaleziono pliku %s obok programu.", LICENSE_FILE_NAME)
        return _FALLBACK_TEXT

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Nie udało się odczytać %s: %s", path, exc)
        return _FALLBACK_TEXT


class LicenseAgreementDialog(QDialog):
    """Modalne okno z warunkami korzystania i przyciskami decyzji.

    Blokuje dalsze działanie programu do czasu podjęcia decyzji - wywołujący
    sprawdza result() (QDialog.Accepted / QDialog.Rejected) po exec().
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Warunki korzystania")
        self.setMinimumSize(640, 480)
        # Modalność niezależna od okna głównego - to okno pokazuje się,
        # zanim MainWindow w ogóle powstanie.
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Przed pierwszym uruchomieniem zapoznaj się z warunkami korzystania "
            "z programu."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        text_view = QTextEdit()
        text_view.setReadOnly(True)
        text_view.setPlainText(_read_license_text())
        text_view.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(text_view)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.btn_reject = QPushButton("Nie akceptuję")
        self.btn_reject.clicked.connect(self.reject)
        buttons.addWidget(self.btn_reject)

        self.btn_accept = QPushButton("Akceptuję")
        self.btn_accept.setDefault(True)
        self.btn_accept.clicked.connect(self.accept)
        buttons.addWidget(self.btn_accept)

        layout.addLayout(buttons)

    def closeEvent(self, event) -> None:  # noqa: N802 - API Qt
        # Zamknięcie krzyżykiem traktujemy tak samo jak "Nie akceptuję" -
        # brak jawnej zgody nie może po cichu uruchomić programu.
        self.reject()
        event.accept()