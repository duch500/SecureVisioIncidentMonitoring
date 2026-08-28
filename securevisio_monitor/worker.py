"""Pętla monitorująca - spina wykrywanie okien, odczyt i maszynę stanów.

Worker działa w osobnym wątku i komunikuje się z GUI wyłącznie przez sygnały.
Jest to celowe: odczyt UI Automation potrafi zająć ułamek sekundy na okno,
a wykonywany w wątku GUI zamrażałby interfejs przy każdym sprawdzeniu.

Worker nie tworzy okien Qt - decyzję o pokazaniu alarmu podejmuje odbiorca
sygnałów w wątku GUI. Widgety Qt wolno tworzyć wyłącznie w wątku głównym.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QThread, Signal

from .config import AppSettings
from .state_machine import EventAlert, MonitorState
from .uia_reader import GridReadError, read_incidents
from .window_resolver import (
    ClientResolver,
    enumerate_error_dialogs,
    is_window_minimized,
)

logger = logging.getLogger(__name__)

# Ziarnistość przerywania oczekiwania między sprawdzeniami. Pętla śpi krótkimi
# odcinkami, żeby zatrzymanie monitora nie czekało na pełny interwał.
_SLEEP_STEP_SEC = 0.1


@dataclass
class ClientStatus:
    """Bieżący stan monitorowania jednego klienta - na potrzeby GUI i diagnostyki."""

    label: str
    is_available: bool = False
    last_read_at: Optional[datetime] = None
    last_read_duration: float = 0.0
    incident_count: int = 0
    active_events: int = 0
    is_minimized: bool = False
    error: str = ""
    method: str = "UI Automation"
    connection_lost: bool = False

    @property
    def state_text(self) -> str:
        """Krótki opis stanu do wyświetlenia w tabeli GUI."""
        if not self.is_available:
            return "NIEDOSTĘPNY"
        # Zerwane połączenie ma pierwszeństwo przed liczbą zdarzeń: dane
        # w siatce są wtedy zamrożone sprzed utraty łączności, więc
        # pokazywanie ich jako aktualnych wprowadzałoby w błąd.
        if self.connection_lost:
            return "BRAK POŁĄCZENIA"
        if self.active_events:
            return f"NOWE ZDARZENIE ({self.active_events})"
        return "OK"

    @property
    def last_read_text(self) -> str:
        if self.last_read_at is None:
            return "-"
        return self.last_read_at.strftime("%H:%M:%S")


@dataclass
class _ClientRuntime:
    """Wewnętrzny stan śledzenia dostępności klienta między cyklami."""

    status: ClientStatus
    was_available: bool = False
    # Zgłoszone zerwanie połączenia - zapobiega powtarzaniu alarmu w każdym
    # cyklu, dopóki dialog błędu pozostaje otwarty.
    connection_error_reported: bool = False
    # Klient uznany za utracony, dla którego już zaalarmowano - zapobiega
    # powtarzaniu alarmu przy każdym cyklu, gdy SecureVisio pozostaje zamknięte.
    loss_reported: bool = False


class MonitorWorker(QThread):
    """Cyklicznie sprawdza wszystkie skonfigurowane środowiska SecureVisio.

    Sygnały:
        new_alerts: Świeżo wykryte przejścia na status nowego zdarzenia.
        clients_lost: Etykiety klientów, których okno właśnie zniknęło.
        clients_returned: Etykiety klientów, których okno wróciło.
        connection_lost: Etykiety klientów z wykrytym zerwaniem połączenia.
        status_updated: Pełny stan wszystkich klientów po każdym cyklu.
        tick: Zakończono cykl sprawdzania (do odliczania przypomnień).
        log_message: Komunikat do wyświetlenia w logu GUI.
    """

    new_alerts = Signal(list)
    clients_lost = Signal(list)
    clients_returned = Signal(list)
    connection_lost = Signal(list)
    status_updated = Signal(list)
    tick = Signal(list)
    log_message = Signal(str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._state = MonitorState(
            phrases=settings.default_phrases,
            alert_on_first_scan=settings.alert_on_first_scan,
        )
        self._resolver = ClientResolver(
            base_dir=settings.base_dir or None,
            manual_map=settings.manual_map(),
        )
        self._runtimes: dict[str, _ClientRuntime] = {}
        # Klienci pilnowani w bieżącej sesji - patrz _expected_clients.
        self._session_clients: set[str] = set()
        self._running = False
        self._check_now = False

    # --- Sterowanie --------------------------------------------------------

    def stop(self) -> None:
        """Sygnalizuje zatrzymanie pętli. Bezpieczne do wywołania z GUI."""
        self._running = False

    def check_now(self) -> None:
        """Wymusza natychmiastowe sprawdzenie, bez czekania na interwał."""
        self._check_now = True

    def acknowledge(self, alerts: list[EventAlert]) -> None:
        """Oznacza wskazane zdarzenia jako potwierdzone przez operatora."""
        by_client: dict[str, list[str]] = {}
        for alert in alerts:
            by_client.setdefault(alert.client, []).append(alert.incident_id)

        for client, incident_ids in by_client.items():
            self._state.machine_for(client).acknowledge(incident_ids)

    def acknowledge_ids(
        self, client: str, incident_ids: Optional[list[str]] = None
    ) -> None:
        """Potwierdza zdarzenia jednego klienta po identyfikatorach.

        Wykorzystywane przy potwierdzeniu z powiadomienia systemowego, gdzie
        znamy klienta i identyfikator, ale nie mamy pełnego obiektu zdarzenia.

        Args:
            client: Etykieta klienta.
            incident_ids: Identyfikatory do potwierdzenia. None potwierdza
                wszystkie aktywne zdarzenia tego klienta.
        """
        self._state.machine_for(client).acknowledge(incident_ids)

    def active_alerts(self) -> list[EventAlert]:
        """Zdarzenia nadal nieobsłużone i niepotwierdzone."""
        return self._state.active_alerts()

    # --- Pętla -------------------------------------------------------------

    def run(self) -> None:  # noqa: D102 - API QThread
        self._running = True
        # Nowa sesja - lista pilnowanych środowisk budowana od zera.
        self._session_clients.clear()
        self._runtimes.clear()
        self.log_message.emit("Rozpoczęto monitorowanie.")
        logger.debug("Worker wystartował (interwał %ds).", self._settings.interval_sec)

        # Pierwsze sprawdzenie od razu - bez czekania pełnego interwału.
        self._run_cycle()

        while self._running:
            self._sleep_interval()
            if not self._running:
                break
            self._run_cycle()

        self.log_message.emit("Zatrzymano monitorowanie.")
        logger.debug("Worker zakończył pracę.")

    def _sleep_interval(self) -> None:
        """Czeka do następnego cyklu, reagując na stop i wymuszone sprawdzenie."""
        deadline = time.monotonic() + self._settings.interval_sec
        while self._running and time.monotonic() < deadline:
            if self._check_now:
                self._check_now = False
                return
            time.sleep(_SLEEP_STEP_SEC)

    def _run_cycle(self) -> None:
        """Wykonuje jeden pełny przebieg: wykrycie okien, odczyt, analiza."""
        try:
            resolved = self._resolver.resolve_all()
        except Exception as exc:  # noqa: BLE001 - pętla nie może umrzeć
            logger.exception("Błąd wykrywania okien: %s", exc)
            self.log_message.emit(f"Błąd wykrywania okien: {exc}")
            return

        # Mapa klient -> okno. Przy duplikacie ścieżki wygrywa pierwsze
        # znalezione okno, a fakt kolizji trafia do logu.
        windows: dict[str, object] = {}
        for item in resolved:
            if not item.is_recognized or item.client_label is None:
                continue
            if item.client_label in windows:
                self.log_message.emit(
                    f"Uwaga: wykryto więcej niż jedno okno dla '{item.client_label}'. "
                    "Monitoruję pierwsze."
                )
                continue
            windows[item.client_label] = item

        # Mapa okno_główne -> klient, do powiązania dialogów błędu z klientem.
        hwnd_to_client = {
            item.window.hwnd: label for label, item in windows.items()
        }
        clients_with_error = self._detect_connection_errors(hwnd_to_client)

        expected = self._expected_clients(windows.keys())
        fresh_alerts: list[EventAlert] = []
        lost_clients: list[str] = []
        returned_clients: list[str] = []
        new_connection_errors: list[str] = []

        for label in expected:
            item = windows.get(label)
            runtime = self._runtime_for(label)

            if item is None:
                if runtime.was_available and not runtime.loss_reported:
                    lost_clients.append(label)
                    runtime.loss_reported = True
                    self.log_message.emit(f"{label}: okno SecureVisio zniknęło.")
                    logger.warning("Klient %s: utracono okno.", label)
                runtime.was_available = False
                runtime.status.is_available = False
                runtime.status.error = "Okno SecureVisio niedostępne"
                # Stan incydentów pozostaje nienaruszony - patrz mark_unavailable.
                self._state.machine_for(label).mark_unavailable()
                continue

            if runtime.loss_reported:
                returned_clients.append(label)

            has_error = label in clients_with_error

            if has_error:
                if not runtime.connection_error_reported:
                    new_connection_errors.append(label)
                    runtime.connection_error_reported = True
                    self.log_message.emit(f"{label}: wykryto zerwanie połączenia.")
                    logger.warning("Klient %s: zerwane połączenie z serwerem.", label)
            elif runtime.connection_error_reported:
                runtime.connection_error_reported = False
                self.log_message.emit(f"{label}: połączenie przywrócone.")

            fresh_alerts.extend(
                self._read_client(label, item, runtime, connection_lost=has_error)
            )

        statuses = [r.status for r in self._runtimes.values()]
        self.status_updated.emit(statuses)

        if new_connection_errors:
            self.connection_lost.emit(new_connection_errors)

        if returned_clients:
            self.clients_returned.emit(returned_clients)

        if lost_clients:
            self.clients_lost.emit(lost_clients)

        if fresh_alerts:
            self.new_alerts.emit(fresh_alerts)

        self.tick.emit(self._state.active_alerts())

    def _detect_connection_errors(self, hwnd_to_client: dict[int, str]) -> set[str]:
        """Zwraca etykiety klientów z otwartym dialogiem błędu połączenia.

        Dialog rozpoznajemy dwuetapowo: po klasie okna (tanie, niezależne od
        języka) i po treści (bo ta sama klasa okna może obsługiwać także inne
        błędy niż zerwanie połączenia).
        """
        if not self._settings.detect_connection_errors:
            return set()

        phrases = self._settings.connection_error_phrases
        if not phrases:
            return set()

        affected: set[str] = set()

        try:
            dialogs = enumerate_error_dialogs()
        except Exception as exc:  # noqa: BLE001 - pętla nie może umrzeć
            logger.warning("Błąd wykrywania dialogów: %s", exc)
            return set()

        for dialog in dialogs:
            if not dialog.matches_any(phrases):
                logger.debug(
                    "Dialog błędu HWND=%d nie pasuje do fraz połączenia - pomijam.",
                    dialog.hwnd,
                )
                continue

            client = hwnd_to_client.get(dialog.owner_hwnd)
            if client is None:
                logger.debug(
                    "Dialog błędu HWND=%d: nie udało się powiązać z klientem "
                    "(okno nadrzędne=%d).",
                    dialog.hwnd, dialog.owner_hwnd,
                )
                continue

            affected.add(client)

        return affected

    def _read_client(
        self,
        label: str,
        item,
        runtime: _ClientRuntime,
        connection_lost: bool = False,
    ) -> list[EventAlert]:
        """Odczytuje jedno środowisko i aktualizuje jego stan.

        Args:
            connection_lost: Gdy True, dane w siatce pochodzą sprzed utraty
                łączności. Odczyt jest wykonywany na potrzeby diagnostyki,
                ale NIE służy do wykrywania nowych zdarzeń - każda zmiana
                wykryta w zamrożonych danych byłaby fałszywa.
        """
        hwnd = item.window.hwnd
        status = runtime.status

        start = time.perf_counter()
        try:
            snapshot = read_incidents(hwnd)
        except GridReadError as exc:
            status.is_available = False
            status.error = str(exc)
            self._state.machine_for(label).mark_unavailable()
            logger.warning("Klient %s: %s", label, exc)
            self.log_message.emit(f"{label}: nie udało się odczytać listy incydentów.")
            return []
        except Exception as exc:  # noqa: BLE001 - nieoczekiwany błąd nie może zabić pętli
            status.is_available = False
            status.error = f"Nieoczekiwany błąd: {exc}"
            self._state.machine_for(label).mark_unavailable()
            logger.exception("Klient %s: nieoczekiwany błąd odczytu.", label)
            return []

        duration = time.perf_counter() - start

        profile = self._settings.find_client(label)
        phrases = (
            profile.effective_phrases(self._settings.default_phrases)
            if profile
            else self._settings.default_phrases
        )
        machine = self._state.machine_for(label, phrases)

        if connection_lost:
            # Stan incydentów pozostaje nienaruszony - tak samo jak przy
            # nieudanym odczycie. Nowe zdarzenia i tak nie docierają do
            # zamrożonej siatki, więc nie ma ryzyka ich przeoczenia.
            machine.mark_unavailable()
            alerts = []
        else:
            alerts = machine.update(snapshot.incidents)

        status.is_available = True
        status.error = ""
        status.last_read_at = datetime.now()
        status.last_read_duration = duration
        status.incident_count = len(snapshot.incidents)
        status.active_events = len(machine.active_alerts())
        status.is_minimized = is_window_minimized(hwnd)
        status.connection_lost = connection_lost

        runtime.was_available = True
        runtime.loss_reported = False

        if alerts:
            self.log_message.emit(
                f"{label}: wykryto {len(alerts)} nowe zdarzenie(a)."
            )

        return alerts

    def _expected_clients(self, detected_labels) -> list[str]:
        """Ustala listę klientów pilnowanych w tej sesji monitorowania.

        Lista rośnie o każde nowo wykryte środowisko i nie kurczy się przy
        zniknięciu - dzięki temu zamknięcie SecureVisio jest wykrywane jako
        utrata, a nie jako "tego klienta nigdy nie było". Zakres sesji kończy
        się przy zatrzymaniu monitorowania: kolejny start buduje listę od nowa.
        """
        configured = self._settings.enabled_clients()
        if configured:
            self._session_clients.update(c.label for c in configured)
        else:
            self._session_clients.update(detected_labels)
        return sorted(self._session_clients)

    def _runtime_for(self, label: str) -> _ClientRuntime:
        runtime = self._runtimes.get(label)
        if runtime is None:
            runtime = _ClientRuntime(status=ClientStatus(label=label))
            self._runtimes[label] = runtime
        return runtime