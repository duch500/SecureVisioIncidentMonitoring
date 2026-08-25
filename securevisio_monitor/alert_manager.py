"""Sterowanie cyklem życia alarmów.

Odpowiada za decyzję KIEDY pokazać alarm i CO na nim umieścić. Samo rysowanie
należy do gui.overlays.AlarmOverlay.

Reguły czasowe:
- alarm wyświetla się przez alarm_display_sec (domyślnie 10s), po czym znika,
- jeśli zdarzenie pozostaje nieobsłużone i niepotwierdzone, alarm wraca
  po alarm_repeat_sec (domyślnie 60s) liczonych od jego ukrycia,
- kliknięcie potwierdza wszystkie wyświetlone zdarzenia i kończy przypomnienia
  dla nich - do czasu, aż status zmieni się i ponownie wróci na nowe zdarzenie.
"""

from __future__ import annotations

import logging
import time
from typing import Iterable, Optional, Protocol

from .state_machine import EventAlert

logger = logging.getLogger(__name__)


class AlarmDisplay(Protocol):
    """Interfejs warstwy wizualnej wymagany przez AlertManager.

    Wydzielony jako protokół, żeby logikę czasową dało się testować
    bez uruchamiania Qt.
    """

    @property
    def is_visible(self) -> bool: ...

    def show_alarm(
        self, entries: Iterable[tuple[str, str]], display_seconds: Optional[int] = None
    ) -> None: ...

    def hide_alarm(self, emit_signal: bool = True) -> None: ...


class AlertManager:
    """Decyduje o pokazywaniu alarmów i przypomnień.

    Args:
        display: Warstwa wizualna alarmu.
        display_seconds: Czas wyświetlania alarmu.
        repeat_seconds: Odstęp do przypomnienia o nieobsłużonym zdarzeniu,
            liczony od ukrycia poprzedniego alarmu.
        time_source: Źródło czasu (wstrzykiwane na potrzeby testów).
    """

    def __init__(
        self,
        display: AlarmDisplay,
        display_seconds: int = 10,
        repeat_seconds: int = 60,
        time_source=time.monotonic,
    ) -> None:
        self._display = display
        self._display_seconds = display_seconds
        self._repeat_seconds = repeat_seconds
        self._now = time_source

        # Moment ostatniego ukrycia alarmu - podstawa odliczania przypomnienia.
        self._last_hidden_at: Optional[float] = None
        # Zdarzenia pokazane na aktualnie widocznym alarmie - potrzebne, żeby
        # kliknięcie potwierdziło dokładnie to, co operator widział.
        self._displayed: list[EventAlert] = []

    def on_new_alerts(self, alerts: list[EventAlert]) -> None:
        """Obsługuje świeżo wykryte przejścia na status nowego zdarzenia.

        Nowe zdarzenie ma pierwszeństwo: jeśli alarm jest już widoczny,
        zostaje odświeżony o dodatkową pozycję, a licznik startuje od nowa.
        """
        if not alerts:
            return

        if self._display.is_visible:
            # Dołączamy nowe zdarzenia do już widocznych, bez duplikatów.
            combined = self._merge(self._displayed, alerts)
            logger.debug(
                "Nowe zdarzenie w trakcie wyświetlania alarmu - odświeżam (%d pozycji).",
                len(combined),
            )
            self._show(combined)
        else:
            self._show(alerts)

    def on_tick(self, active_alerts: list[EventAlert]) -> None:
        """Wywoływane cyklicznie - decyduje o przypomnieniu.

        Args:
            active_alerts: Zdarzenia nadal nieobsłużone i niepotwierdzone
                (typowo MonitorState.active_alerts()).
        """
        if self._display.is_visible:
            return

        if not active_alerts:
            # Nie ma o czym przypominać - zerujemy licznik, żeby kolejne
            # zdarzenie pokazało się natychmiast, a nie po resztce odstępu.
            self._last_hidden_at = None
            return

        if self._last_hidden_at is None:
            return

        elapsed = self._now() - self._last_hidden_at
        if elapsed >= self._repeat_seconds:
            logger.debug(
                "Przypomnienie o %d nieobsłużonych zdarzeniach (po %.0fs).",
                len(active_alerts),
                elapsed,
            )
            self._show(active_alerts)

    def on_acknowledged(self) -> list[EventAlert]:
        """Obsługuje potwierdzenie kliknięciem.

        Returns:
            Zdarzenia, które operator faktycznie widział na ekranie - do
            oznaczenia jako potwierdzone w maszynie stanów.
        """
        acknowledged = list(self._displayed)
        self._displayed.clear()
        self._last_hidden_at = None
        logger.debug("Potwierdzono %d zdarzeń.", len(acknowledged))
        return acknowledged

    def on_dismissed(self) -> None:
        """Obsługuje samoczynne wygaśnięcie alarmu (bez potwierdzenia)."""
        self._last_hidden_at = self._now()
        self._displayed.clear()

    def force_hide(self) -> None:
        """Ukrywa alarm bez traktowania tego jako potwierdzenia (np. przy stopie)."""
        if self._display.is_visible:
            self._display.hide_alarm(emit_signal=False)
        self._displayed.clear()
        self._last_hidden_at = None

    def _show(self, alerts: list[EventAlert]) -> None:
        self._displayed = list(alerts)
        entries = [(a.location_label, a.client) for a in alerts]
        self._display.show_alarm(entries, self._display_seconds)

    @staticmethod
    def _merge(current: list[EventAlert], new: list[EventAlert]) -> list[EventAlert]:
        """Łączy listy zdarzeń, pomijając duplikaty (ten sam klient i Id)."""
        seen = {(a.client, a.incident_id) for a in current}
        merged = list(current)
        for alert in new:
            key = (alert.client, alert.incident_id)
            if key not in seen:
                seen.add(key)
                merged.append(alert)
        return merged