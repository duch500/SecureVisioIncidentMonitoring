"""Wykrywanie przejścia incydentów w stan "nowe zdarzenie".

Moduł jest celowo wolny od zależności od Windows, UI Automation i GUI -
przyjmuje listę incydentów, zwraca listę alarmów. Dzięki temu całą logikę
da się przetestować na sztucznych danych, bez uruchomionego SecureVisio.

Kluczowa zasada: alarmujemy przy PRZEJŚCIU na status nowego zdarzenia,
nie przy samej jego obecności. Stan śledzony jest per incydent (po jego Id),
a nie per okno - dzięki temu poprawnie obsługujemy sytuacje, w których
kilka incydentów jednocześnie ma status nowego zdarzenia.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# Domyślne frazy oznaczające nowe, nieobsłużone zdarzenie. Różni klienci
# korzystają z różnych wersji językowych SecureVisio.
DEFAULT_NEW_EVENT_PHRASES = ("Nowe Zdarzenie", "New Event")

_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Normalizuje tekst statusu do porównania.

    Ujednolica wielkość liter i białe znaki - status odczytany z UI Automation
    bywa otoczony spacjami albo zapisany inną wielkością liter niż w konfiguracji.
    """
    return _WHITESPACE.sub(" ", text.strip()).casefold()


@dataclass(frozen=True)
class EventAlert:
    """Pojedynczy incydent kwalifikujący się do zaalarmowania.

    Attributes:
        client: Etykieta klienta (np. "Klient A").
        incident_id: Id incydentu w SecureVisio.
        network_map: Wartość kolumny "Mapa sieci". Pusta, gdy dane środowisko
            nie udostępnia tej kolumny.
        status: Status, który wywołał alarm.
    """

    client: str
    incident_id: str
    network_map: str
    status: str

    @property
    def location_label(self) -> str:
        """Opis miejsca do wyświetlenia na alarmie - mapa sieci albo Id incydentu."""
        return self.network_map or f"Incydent {self.incident_id}"


@dataclass
class _IncidentRecord:
    """Zapamiętany stan pojedynczego incydentu."""

    status: str
    network_map: str
    is_new_event: bool
    acknowledged: bool = False


class ClientStateMachine:
    """Śledzi stan incydentów jednego klienta i wykrywa przejścia.

    Args:
        client: Etykieta klienta, przenoszona do generowanych alarmów.
        phrases: Frazy statusu oznaczające nowe zdarzenie.
        alert_on_first_scan: Czy alarmować o incydentach zastanych już przy
            pierwszym odczycie. Domyślnie True - jeśli przy uruchomieniu
            monitora czeka nieobsłużone zdarzenie, operator powinien je zobaczyć.
    """

    def __init__(
        self,
        client: str,
        phrases: Iterable[str] = DEFAULT_NEW_EVENT_PHRASES,
        alert_on_first_scan: bool = True,
    ) -> None:
        self.client = client
        self._phrases = {_normalize(p) for p in phrases if p.strip()}
        self._alert_on_first_scan = alert_on_first_scan
        self._records: dict[str, _IncidentRecord] = {}
        self._first_scan_done = False

        if not self._phrases:
            logger.warning(
                "Klient %s: nie skonfigurowano żadnej frazy - alarmy nie będą generowane.",
                client,
            )

    def _matches(self, status: str) -> bool:
        return _normalize(status) in self._phrases

    @property
    def is_initialized(self) -> bool:
        """Czy wykonano już pierwszy udany odczyt."""
        return self._first_scan_done

    def update(self, incidents: Iterable) -> list[EventAlert]:
        """Przetwarza wynik jednego udanego odczytu siatki.

        Args:
            incidents: Obiekty z polami incident_id, status, network_map
                (typowo uia_reader.Incident).

        Returns:
            Lista incydentów, które WŁAŚNIE przeszły w stan nowego zdarzenia.
            Pusta lista oznacza brak nowych przejść - również wtedy, gdy nadal
            istnieją nieobsłużone zdarzenia wykryte wcześniej.
        """
        alerts: list[EventAlert] = []
        seen_ids: set[str] = set()

        for incident in incidents:
            incident_id = incident.incident_id
            seen_ids.add(incident_id)

            status = incident.status
            network_map = getattr(incident, "network_map", "")
            is_new = self._matches(status)
            previous = self._records.get(incident_id)

            if previous is None:
                # Incydent widziany po raz pierwszy.
                should_alert = is_new and (self._first_scan_done or self._alert_on_first_scan)
                self._records[incident_id] = _IncidentRecord(
                    status=status, network_map=network_map, is_new_event=is_new
                )
                if should_alert:
                    alerts.append(self._build_alert(incident_id, status, network_map))
                    logger.debug(
                        "Klient %s: nowy incydent %s ze statusem '%s'.",
                        self.client,
                        incident_id,
                        status,
                    )
                continue

            if is_new and not previous.is_new_event:
                # Przejście istniejącego incydentu na status nowego zdarzenia
                # (np. ponowne otwarcie). Wcześniejsze potwierdzenie traci ważność.
                previous.acknowledged = False
                alerts.append(self._build_alert(incident_id, status, network_map))
                logger.debug(
                    "Klient %s: incydent %s zmienił status '%s' -> '%s'.",
                    self.client,
                    incident_id,
                    previous.status,
                    status,
                )
            elif not is_new and previous.is_new_event:
                # Zdarzenie zostało podjęte przez operatora.
                previous.acknowledged = False
                logger.debug(
                    "Klient %s: incydent %s obsłużony (status '%s').",
                    self.client,
                    incident_id,
                    status,
                )

            previous.status = status
            previous.network_map = network_map
            previous.is_new_event = is_new

        # Incydenty, które zniknęły z listy, przestają być śledzone.
        for incident_id in self._records.keys() - seen_ids:
            del self._records[incident_id]

        self._first_scan_done = True
        return alerts

    def _build_alert(self, incident_id: str, status: str, network_map: str) -> EventAlert:
        return EventAlert(
            client=self.client,
            incident_id=incident_id,
            network_map=network_map,
            status=status,
        )

    def acknowledge(self, incident_ids: Optional[Iterable[str]] = None) -> None:
        """Oznacza incydenty jako potwierdzone przez operatora.

        Potwierdzony incydent nie generuje kolejnych przypomnień, dopóki jego
        status nie zmieni się na inny i ponownie na nowe zdarzenie.

        Args:
            incident_ids: Id incydentów do potwierdzenia. None potwierdza
                wszystkie aktualnie aktywne.
        """
        targets = (
            set(incident_ids)
            if incident_ids is not None
            else {i for i, r in self._records.items() if r.is_new_event}
        )
        for incident_id in targets:
            record = self._records.get(incident_id)
            if record is not None:
                record.acknowledged = True

    def active_alerts(self) -> list[EventAlert]:
        """Zwraca nieobsłużone i niepotwierdzone zdarzenia.

        Wykorzystywane do cyklicznych przypomnień - w odróżnieniu od update(),
        które zwraca wyłącznie świeże przejścia.
        """
        return [
            self._build_alert(incident_id, record.status, record.network_map)
            for incident_id, record in self._records.items()
            if record.is_new_event and not record.acknowledged
        ]

    def mark_unavailable(self) -> None:
        """Sygnalizuje nieudany odczyt (okno zamknięte, brak dostępu).

        Stan incydentów pozostaje nienaruszony. Jest to celowe: potraktowanie
        nieudanego odczytu jako "brak zdarzeń" spowodowałoby uznanie
        nieobsłużonych incydentów za zamknięte, a po odzyskaniu dostępu -
        lawinę fałszywych alarmów o "nowych" zdarzeniach.
        """
        logger.debug(
            "Klient %s: odczyt nieudany, zachowuję %d śledzonych incydentów.",
            self.client,
            len(self._records),
        )

    def reset(self) -> None:
        """Czyści cały stan (np. po zmianie konfiguracji klienta)."""
        self._records.clear()
        self._first_scan_done = False


class MonitorState:
    """Zbiorczy stan wszystkich monitorowanych klientów."""

    def __init__(
        self,
        phrases: Iterable[str] = DEFAULT_NEW_EVENT_PHRASES,
        alert_on_first_scan: bool = True,
    ) -> None:
        self._default_phrases = tuple(phrases)
        self._alert_on_first_scan = alert_on_first_scan
        self._machines: dict[str, ClientStateMachine] = {}

    def machine_for(
        self, client: str, phrases: Optional[Iterable[str]] = None
    ) -> ClientStateMachine:
        """Zwraca maszynę stanów klienta, tworząc ją przy pierwszym użyciu."""
        machine = self._machines.get(client)
        if machine is None:
            machine = ClientStateMachine(
                client=client,
                phrases=phrases if phrases is not None else self._default_phrases,
                alert_on_first_scan=self._alert_on_first_scan,
            )
            self._machines[client] = machine
        return machine

    def active_alerts(self) -> list[EventAlert]:
        """Nieobsłużone zdarzenia ze wszystkich klientów."""
        alerts: list[EventAlert] = []
        for machine in self._machines.values():
            alerts.extend(machine.active_alerts())
        return alerts

    def acknowledge_all(self) -> None:
        """Potwierdza wszystkie aktywne zdarzenia u wszystkich klientów."""
        for machine in self._machines.values():
            machine.acknowledge()

    def remove_client(self, client: str) -> None:
        """Usuwa klienta ze śledzenia (np. po usunięciu z konfiguracji)."""
        self._machines.pop(client, None)