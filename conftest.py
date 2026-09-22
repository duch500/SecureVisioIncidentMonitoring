"""Konfiguracja współdzielona dla całej sesji pytest.

Tworzy jedną instancję QApplication na cały przebieg testów. Bez tego
pierwszy test korzystający z QPixmap (m.in. gui/themes.py generujący ikony
interfejsu) może zawiesić proces zamiast zgłosić czytelny błąd - zależy to
od tego, w jakiej kolejności pytest odkrywa i uruchamia poszczególne pliki
na danym systemie, więc objaw bywał niepowtarzalny między uruchomieniami.

Fixture ma scope="session" i autouse=True - działa automatycznie dla
wszystkich testów, bez potrzeby jawnego odwoływania się do niej.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app