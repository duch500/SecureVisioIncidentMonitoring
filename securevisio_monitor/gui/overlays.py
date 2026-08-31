"""Pełnoekranowy alarm wizualny.

Alarm pokazywany jest jednocześnie na wszystkich monitorach: czerwone tło,
biały napis "NOWE ZDARZENIE", pod spodem lista środowisk, których dotyczy.

Każda pozycja ma przycisk "Pokaż", który maksymalizuje odpowiadające jej okno
SecureVisio. Kliknięcie w tło (poza przyciskami) zamyka alarm i potwierdza
wszystkie zdarzenia, nie ruszając żadnego okna.

Wariant pomarańczowy sygnalizuje zamknięcie monitorowanego środowiska -
bez przycisków i bez dźwięku, bo nie ma tam czego pokazywać.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    DEFAULT_COLOR_CONNECTION,
    DEFAULT_COLOR_EVENT,
    DEFAULT_COLOR_UNAVAILABLE,
    contrast_text_color,
)

logger = logging.getLogger(__name__)

ALARM_TITLE = "NOWE ZDARZENIE"
ALARM_TITLE_UNAVAILABLE = "ŚRODOWISKO ZAMKNIĘTE"
ALARM_TITLE_CONNECTION = "ZERWANE POŁĄCZENIE"

# Liczba pozycji pokazywanych na ekranie, zanim przejdziemy na skrót
# "i N kolejnych" - przy większej liczbie napis przestaje być czytelny
# z odległości, a to jest alarm, nie raport.
MAX_VISIBLE_ENTRIES = 6

# Kolory tła pochodzą z ustawień użytkownika. Kolor tekstu dobierany jest
# automatycznie do jasności tła - przy jasnym kolorze biały napis byłby
# nieczytelny.


def _style_title(text_color: str) -> str:
    return f"color: {text_color}; font-size: 72px; font-weight: bold;"


def _style_entry(text_color: str) -> str:
    return f"color: {text_color}; font-size: 30px;"


def _style_hint(text_color: str) -> str:
    # Podpowiedź celowo słabiej widoczna niż główna treść.
    opacity = "rgba(255, 255, 255, 180)" if text_color == "#FFFFFF" else "rgba(0, 0, 0, 150)"
    return f"color: {opacity}; font-size: 20px;"


def _style_button(background: str, text_color: str) -> str:
    """Buduje styl przycisku odwrócony względem tła alarmu.

    Przy ciemnym tle alarmu przycisk jest jasny z ciemnym napisem, przy jasnym -
    odwrotnie. Użycie koloru tła alarmu jako koloru napisu działa tylko dla
    ciemnych tł: na jasnym tle (np. żółtym) napis stawał się nieczytelny.
    """
    if text_color == "#FFFFFF":
        # Ciemne tło alarmu - jasny przycisk z napisem w kolorze tła.
        button_bg, button_fg, hover = "white", background, "rgb(240, 240, 240)"
    else:
        # Jasne tło alarmu - ciemny przycisk z jasnym napisem.
        button_bg, button_fg, hover = "#1A1A1A", "white", "#333333"

    return f"""
QPushButton {{
    color: {button_fg};
    background-color: {button_bg};
    font-size: 22px;
    font-weight: bold;
    padding: 8px 28px;
    border: none;
    border-radius: 6px;
}}
QPushButton:hover {{
    background-color: {hover};
}}
"""


class AlarmScreen(QWidget):
    """Pełnoekranowe okno alarmu na jednym monitorze."""

    background_clicked = Signal()
    show_requested = Signal(str)  # etykieta klienta

    def __init__(
        self,
        geometry,
        title: str,
        entries: list[tuple[str, str]],
        hint: str,
        background: str = DEFAULT_COLOR_EVENT,
        with_buttons: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setGeometry(geometry)
        self.setStyleSheet(f"background-color: {background};")
        self.setCursor(Qt.PointingHandCursor)

        # Kolor tekstu dobrany do jasności tła wybranego przez użytkownika.
        text_color = contrast_text_color(background)
        self._background = background
        self._text_color = text_color

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setStyleSheet(_style_title(text_color))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addSpacing(20)

        visible = entries[:MAX_VISIBLE_ENTRIES]
        for location, client in visible:
            layout.addLayout(self._build_entry_row(location, client, with_buttons))

        remaining = len(entries) - len(visible)
        if remaining > 0:
            more_label = QLabel(f"...i {remaining} więcej")
            more_label.setStyleSheet(_style_entry(text_color))
            more_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(more_label)

        layout.addSpacing(24)
        hint_label = QLabel(hint)
        hint_label.setStyleSheet(_style_hint(text_color))
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)

    def _build_entry_row(
        self, location: str, client: str, with_buttons: bool
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        row.setSpacing(24)

        label = QLabel(f"{location}   —   {client}")
        label.setStyleSheet(_style_entry(self._text_color))
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setMinimumWidth(420)
        row.addWidget(label)

        if with_buttons:
            button = QPushButton("Pokaż")
            button.setStyleSheet(_style_button(self._background, self._text_color))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, c=client: self.show_requested.emit(c))
            row.addWidget(button)
        else:
            # Zachowanie wyrównania listy, gdy przycisków nie ma.
            row.addSpacing(120)

        return row

    def mousePressEvent(self, event) -> None:  # noqa: N802 - API Qt
        """Kliknięcie w tło zamyka alarm.

        Kliknięcia w przyciski nie docierają tutaj - Qt obsługuje je najpierw
        w samym przycisku, więc nie ma ryzyka przypadkowego zamknięcia alarmu
        przy próbie rozwinięcia środowiska.
        """
        self.background_clicked.emit()


class AlarmOverlay(QWidget):
    """Zarządza wyświetlaniem alarmu na wszystkich monitorach jednocześnie.

    Alarm znika automatycznie po zadanym czasie albo natychmiast po kliknięciu.
    Rozróżnienie tych dwóch sytuacji jest istotne: kliknięcie oznacza
    potwierdzenie przez operatora, samo wygaśnięcie - nie.
    """

    acknowledged = Signal()
    dismissed = Signal()
    show_requested = Signal(str)

    def __init__(self, display_seconds: int = 10) -> None:
        super().__init__()
        self._display_seconds = display_seconds
        # Kolory tła dla trzech rodzajów alarmu - nadpisywane z ustawień
        # przez set_colors(). Wartości domyślne pozwalają używać klasy
        # samodzielnie (np. w skrypcie podglądu alarmu).
        self._color_event = DEFAULT_COLOR_EVENT
        self._color_unavailable = DEFAULT_COLOR_UNAVAILABLE
        self._color_connection = DEFAULT_COLOR_CONNECTION
        self._screens: list[AlarmScreen] = []
        self._entry_count = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def set_colors(self, event: str, unavailable: str, connection: str) -> None:
        """Ustawia kolory tła alarmów zgodnie z konfiguracją użytkownika."""
        self._color_event = event
        self._color_unavailable = unavailable
        self._color_connection = connection

    @property
    def is_visible(self) -> bool:
        return bool(self._screens)

    @property
    def entry_count(self) -> int:
        """Liczba pozycji na aktualnie wyświetlanym alarmie."""
        return self._entry_count

    def show_alarm(
        self,
        entries: Iterable[tuple[str, str]],
        display_seconds: Optional[int] = None,
        unavailable: bool = False,
        connection_error: bool = False,
    ) -> None:
        """Pokazuje alarm na wszystkich monitorach.

        Args:
            entries: Pary (lokalizacja, klient) - np. ("Mapa logiczna", "Klient A").
            display_seconds: Czas wyświetlania. None używa wartości z konstruktora.
            unavailable: Wariant "środowisko zamknięte" - inny napis i kolor,
                bez przycisków przywracania okna.
            connection_error: Wariant "zerwane połączenie" - z przyciskiem
                "Pokaż", żeby móc od razu sięgnąć po opcję ponowienia próby.
        """
        entry_list = list(entries)
        if not entry_list:
            logger.debug("Próba pokazania alarmu bez pozycji - pomijam.")
            return

        self.hide_alarm(emit_signal=False)

        if connection_error:
            title = ALARM_TITLE_CONNECTION
            background = self._color_connection
            hint = "Kliknij „Pokaż”, aby przejść do środowiska"
            with_buttons = True
        elif unavailable:
            title = ALARM_TITLE_UNAVAILABLE
            background = self._color_unavailable
            hint = "Kliknij, aby zamknąć"
            with_buttons = False
        else:
            title = ALARM_TITLE
            background = self._color_event
            hint = "Kliknij tło, aby potwierdzić wszystkie"
            with_buttons = True

        screens = QGuiApplication.screens()
        if not screens:
            logger.error("Brak wykrytych monitorów - nie można pokazać alarmu.")
            return

        for screen in screens:
            alarm_screen = AlarmScreen(
                screen.geometry(),
                title,
                entry_list,
                hint,
                background,
                with_buttons=with_buttons,
            )
            alarm_screen.background_clicked.connect(self._on_clicked)
            alarm_screen.show_requested.connect(self.show_requested)
            alarm_screen.show()
            self._screens.append(alarm_screen)

        self._entry_count = len(entry_list)
        seconds = display_seconds if display_seconds is not None else self._display_seconds
        self._timer.start(seconds * 1000)

        logger.debug(
            "Alarm wyświetlony na %d monitorach, %d pozycji, na %ds.",
            len(screens),
            len(entry_list),
            seconds,
        )

    def close_screen_at(self, point: tuple[int, int]) -> None:
        """Zamyka alarm tylko na monitorze zawierającym wskazany punkt.

        Wykorzystywane po przywróceniu okna SecureVisio: alarm ustępuje miejsca
        oknu na tym jednym monitorze, a na pozostałych pozostaje widoczny.
        """
        x, y = point
        remaining: list[AlarmScreen] = []

        for screen in self._screens:
            geometry = screen.geometry()
            if geometry.contains(x, y):
                try:
                    screen.close()
                    screen.deleteLater()
                except RuntimeError:
                    pass
            else:
                remaining.append(screen)

        self._screens = remaining

        if not self._screens:
            self._timer.stop()

    def hide_alarm(self, emit_signal: bool = True) -> None:
        """Ukrywa alarm na wszystkich monitorach."""
        self._timer.stop()

        for screen in self._screens:
            try:
                screen.close()
                screen.deleteLater()
            except RuntimeError:
                # Okno mogło zostać już zniszczone przez Qt - nieszkodliwe.
                pass

        self._screens.clear()
        self._entry_count = 0

        if emit_signal:
            self.dismissed.emit()

    def _on_clicked(self) -> None:
        logger.debug("Alarm potwierdzony kliknięciem.")
        self.hide_alarm(emit_signal=False)
        self.acknowledged.emit()

    def _on_timeout(self) -> None:
        logger.debug("Alarm wygasł automatycznie (bez potwierdzenia).")
        self.hide_alarm()