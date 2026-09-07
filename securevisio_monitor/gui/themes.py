"""Motywy kolorystyczne okna głównego.

Program nie dziedziczy motywu z Windows - użytkownik wybiera go jawnie
w ustawieniach. Powód: dziedziczenie motywu systemowego prowadziło do
niespójnego wyglądu (część kolorów wymuszona w kodzie, część z systemu),
a operatorzy pracujący na jednym stanowisku w różnych warunkach oświetlenia
chcą decydować o tym niezależnie od ustawień całego systemu.

Kolory alarmów pełnoekranowych są osobną, niezależną konfiguracją
(config.color_event i pokrewne) - motyw ich nie dotyczy.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

logger = logging.getLogger(__name__)

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEMES = (THEME_LIGHT, THEME_DARK)


@dataclass(frozen=True)
class Palette:
    """Komplet kolorów jednego motywu.

    Attributes:
        window: Tło okna i paneli.
        surface: Tło elementów wypełnionych (tabela, pola tekstowe, log).
        text: Kolor podstawowego tekstu.
        text_muted: Tekst drugorzędny (podsumowania, notki).
        border: Kolor ramek i linii siatki.
        accent: Kolor wyróżnienia (zaznaczenie, aktywne elementy).
        button: Tło przycisków.
        button_hover: Tło przycisku pod kursorem.
        row_ok: Tło wiersza tabeli - stan poprawny.
        row_alert: Tło wiersza - nowe zdarzenie.
        row_error: Tło wiersza - środowisko niedostępne.
        row_connection: Tło wiersza - brak połączenia.
        row_text: Tekst w kolorowych wierszach tabeli.
    """

    window: str
    surface: str
    text: str
    text_muted: str
    border: str
    accent: str
    button: str
    button_hover: str
    row_ok: str
    row_alert: str
    row_error: str
    row_connection: str
    row_text: str


# Motyw jasny - odpowiada dotychczasowemu wyglądowi programu, żeby zmiana
# nie zaskoczyła osób przyzwyczajonych do poprzedniej wersji.
LIGHT = Palette(
    window="#F0F0F0",
    surface="#FFFFFF",
    text="#1A1A1A",
    text_muted="#5A5A5A",
    border="#C0C0C0",
    accent="#2E5496",
    button="#E8E8E8",
    button_hover="#D8D8D8",
    row_ok="#D7F5D7",
    row_alert="#FFCDCD",
    row_error="#FFE6BE",
    row_connection="#E2D6F5",
    row_text="#191919",
)

# Motyw ciemny - kolorowe wiersze przyciemnione względem jasnego motywu,
# żeby nie raziły na ciemnym tle, ale nadal były jednoznacznie rozróżnialne.
DARK = Palette(
    window="#1E1E1E",
    surface="#252526",
    text="#E4E4E4",
    text_muted="#9A9A9A",
    border="#3C3C3C",
    accent="#4A9EFF",
    button="#333333",
    button_hover="#3F3F3F",
    row_ok="#1E3A24",
    row_alert="#4A1E1E",
    row_error="#4A3418",
    row_connection="#33244A",
    row_text="#E8E8E8",
)

_PALETTES = {THEME_LIGHT: LIGHT, THEME_DARK: DARK}


def get_palette(theme: str) -> Palette:
    """Zwraca paletę dla nazwy motywu, z fallbackiem na jasny."""
    return _PALETTES.get(theme, LIGHT)


def _icon_dir() -> Path:
    """Katalog na wygenerowane ikony elementów interfejsu."""
    path = Path(tempfile.gettempdir()) / "securevisio_monitor_icons"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _draw_arrow(color: str, direction: str, path: Path) -> None:
    """Rysuje strzałkę spinboxa i zapisuje ją jako PNG."""
    size = 12
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    if direction == "up":
        points = [QPointF(3, 7.5), QPointF(6, 4.5), QPointF(9, 7.5)]
    else:
        points = [QPointF(3, 4.5), QPointF(6, 7.5), QPointF(9, 4.5)]

    painter.drawPolyline(points)
    painter.end()

    pixmap.save(str(path), "PNG")


def _draw_check(color: str, path: Path) -> None:
    """Rysuje znacznik zaznaczenia pola wyboru i zapisuje go jako PNG."""
    size = 14
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    painter.drawPolyline([QPointF(3, 7.5), QPointF(6, 10.5), QPointF(11, 4)])
    painter.end()

    pixmap.save(str(path), "PNG")


def _ensure_icons(palette: Palette, theme_name: str) -> dict[str, str]:
    """Generuje ikony dopasowane do palety i zwraca ścieżki do nich.

    Qt w arkuszach stylów obsługuje w url() wyłącznie ścieżki do plików -
    osadzone identyfikatory danych (data:) są ignorowane, przez co elementy
    zostawałyby bez ikony. Dlatego rysujemy je programowo i zapisujemy jako
    pliki tymczasowe, osobno dla każdego motywu (nazwa zawiera motyw, więc
    przełączenie nie powoduje użycia ikon w złym kolorze).

    Ścieżki zwracamy z ukośnikami w przód - Qt wymaga takiego zapisu
    w arkuszu stylów także na Windows.
    """
    directory = _icon_dir()
    icons = {
        "arrow_up": directory / f"arrow_up_{theme_name}.png",
        "arrow_down": directory / f"arrow_down_{theme_name}.png",
        "check": directory / f"check_{theme_name}.png",
    }

    try:
        if not icons["arrow_up"].exists():
            _draw_arrow(palette.text, "up", icons["arrow_up"])
        if not icons["arrow_down"].exists():
            _draw_arrow(palette.text, "down", icons["arrow_down"])
        if not icons["check"].exists():
            # Znacznik zawsze biały - rysowany na tle w kolorze akcentu,
            # który w obu motywach jest wystarczająco ciemny.
            _draw_check("#FFFFFF", icons["check"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nie udało się wygenerować ikon interfejsu: %s", exc)
        return {}

    return {key: str(path).replace("\\", "/") for key, path in icons.items()}


def build_stylesheet(palette: Palette, theme_name: str = THEME_LIGHT) -> str:
    """Buduje arkusz stylów Qt dla całego okna na podstawie palety.

    Stylujemy jawnie wszystkie typy widgetów używane w oknie - poleganie na
    domyślnym wyglądzie Qt sprawiłoby, że część elementów zostałaby
    w kolorach systemu, dając niespójny efekt przy motywie ciemnym.
    """
    icons = _ensure_icons(palette, theme_name)

    # Gdy ikon nie udało się wygenerować, pomijamy reguły ich dotyczące -
    # elementy zachowają wygląd domyślny zamiast zostać bez żadnej ikony.
    if icons:
        icon_rules = f"""
QCheckBox::indicator:checked {{
    background-color: {palette.accent};
    border-color: {palette.accent};
    image: url({icons["check"]});
}}
QComboBox::down-arrow {{
    image: url({icons["arrow_down"]});
    width: 10px;
    height: 10px;
}}
QSpinBox::up-arrow {{
    image: url({icons["arrow_up"]});
    width: 10px;
    height: 10px;
}}
QSpinBox::down-arrow {{
    image: url({icons["arrow_down"]});
    width: 10px;
    height: 10px;
}}
"""
    else:
        icon_rules = f"""
QCheckBox::indicator:checked {{
    background-color: {palette.accent};
    border-color: {palette.accent};
}}
"""

    return f"""
QWidget {{
    background-color: {palette.window};
    color: {palette.text};
}}
QGroupBox {{
    border: 1px solid {palette.border};
    border-radius: 4px;
    margin-top: 6px;
    padding-top: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {palette.text_muted};
}}
QTableWidget {{
    background-color: {palette.surface};
    alternate-background-color: {palette.surface};
    gridline-color: {palette.border};
    border: 1px solid {palette.border};
}}
QHeaderView::section {{
    background-color: {palette.button};
    color: {palette.text};
    border: none;
    border-right: 1px solid {palette.border};
    border-bottom: 1px solid {palette.border};
    padding: 4px;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: {palette.surface};
    color: {palette.text};
    border: 1px solid {palette.border};
    border-radius: 3px;
    padding: 3px;
}}
QLineEdit:read-only {{
    color: {palette.text_muted};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
/* To samo co przy polach wyboru: bez jawnego opisania przycisków strzałek
   Qt rysuje je w surowej, awaryjnej postaci zamiast natywnej. */
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {palette.button};
    border-left: 1px solid {palette.border};
    width: 16px;
}}
QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-top-right-radius: 3px;
    border-bottom: 1px solid {palette.border};
}}
QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border-bottom-right-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {palette.button_hover};
}}
QComboBox QAbstractItemView {{
    background-color: {palette.surface};
    color: {palette.text};
    selection-background-color: {palette.accent};
    selection-color: #FFFFFF;
}}
QPushButton {{
    background-color: {palette.button};
    color: {palette.text};
    border: 1px solid {palette.border};
    border-radius: 3px;
    padding: 4px 12px;
}}
QPushButton:hover {{
    background-color: {palette.button_hover};
}}
QPushButton:disabled {{
    color: {palette.text_muted};
}}
QCheckBox {{
    color: {palette.text};
    spacing: 6px;
}}
/* Nadpisanie stylu widgetu wyłącza natywne rysowanie Windows także dla jego
   elementów składowych - bez jawnego opisania wskaźnika pole wyboru staje
   się niewidoczne (sam znaczek bez ramki). */
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {palette.border};
    border-radius: 3px;
    background-color: {palette.surface};
}}
QCheckBox::indicator:hover {{
    border-color: {palette.accent};
}}
QCheckBox::indicator:disabled {{
    background-color: {palette.window};
    border-color: {palette.border};
}}
QSlider::groove:horizontal {{
    background: {palette.border};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {palette.accent};
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {palette.window};
    border: none;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {palette.border};
    border-radius: 4px;
}}
""" + icon_rules