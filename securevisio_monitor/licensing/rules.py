"""Reguły dostępu wersji demonstracyjnej (część lokalna).

Ten moduł jest czystą logiką - nie czyta dysku, rejestru ani sieci. Dostaje
odczytany stan, bieżący czas i odcisk maszyny, a zwraca werdykt. Dzięki temu
całą regułę fail-closed da się przetestować na sztucznych danych, bez Windows.

Weryfikacja czasu z zewnętrznego serwera należy do osobnego modułu (Etap 2) -
tutaj sprawdzamy tylko to, co wynika z danych lokalnych i zegara systemowego.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from .state_store import DemoState, StoreReadResult

logger = logging.getLogger(__name__)

DEMO_PERIOD_DAYS = 7

# Tolerancja dla drobnego cofnięcia zegara między uruchomieniami (np. korekta
# synchronizacji NTP w tle). Powyżej tej wartości traktujemy jako manipulację.
CLOCK_BACKWARD_TOLERANCE = timedelta(minutes=15)


class Verdict(Enum):
    """Możliwe rozstrzygnięcia reguł dostępu."""

    ALLOW_FIRST_RUN = "allow_first_run"      # pierwsze uruchomienie - zapisz stan
    ALLOW = "allow"                          # w okresie demo, wszystko zgodne
    BLOCK_EXPIRED = "block_expired"          # minął okres demo
    BLOCK_TAMPERED = "block_tampered"        # niespójność / manipulacja stanem
    BLOCK_CLOCK = "block_clock"              # cofnięty zegar systemowy
    BLOCK_FINGERPRINT = "block_fingerprint"  # stan z innego komputera


@dataclass
class Decision:
    """Werdykt reguł wraz z danymi potrzebnymi do reakcji."""

    verdict: Verdict
    reason: str
    days_left: Optional[int] = None

    @property
    def allowed(self) -> bool:
        return self.verdict in (Verdict.ALLOW_FIRST_RUN, Verdict.ALLOW)

    @property
    def is_first_run(self) -> bool:
        return self.verdict == Verdict.ALLOW_FIRST_RUN


def _parse(iso: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


def evaluate(
    read_result: StoreReadResult,
    now: datetime,
    current_fingerprint: str,
) -> Decision:
    """Rozstrzyga, czy wolno uruchomić monitorowanie.

    Kolejność sprawdzeń jest istotna: najpierw manipulacja (najgroźniejsza),
    potem tożsamość maszyny, potem zegar, na końcu upływ czasu. Każdy nieznany
    lub niespójny przypadek prowadzi do blokady - to jest zasada fail-closed.

    Args:
        read_result: Wynik odczytu stanu ze wszystkich kopii.
        now: Bieżący czas (zegar systemowy).
        current_fingerprint: Odcisk maszyny, na której program działa teraz.
    """
    # 1. Niespójność kopii = manipulacja. Ma najwyższy priorytet.
    if read_result.inconsistent:
        return Decision(
            Verdict.BLOCK_TAMPERED,
            "Wykryto niespójność danych wersji demonstracyjnej.",
        )

    # 2. Wszystkie kopie puste = prawdziwe pierwsze uruchomienie.
    if read_result.all_empty:
        return Decision(
            Verdict.ALLOW_FIRST_RUN,
            "Pierwsze uruchomienie - rozpoczęcie okresu demonstracyjnego.",
            days_left=DEMO_PERIOD_DAYS,
        )

    state = read_result.state
    if state is None:
        # Nie puste, nie niespójne, a mimo to brak stanu - sytuacja niemożliwa
        # w normalnym toku, więc traktujemy zachowawczo jako manipulację.
        return Decision(
            Verdict.BLOCK_TAMPERED,
            "Nieokreślony stan wersji demonstracyjnej.",
        )

    # 3. Odcisk maszyny musi się zgadzać - inaczej stan pochodzi z innego komputera.
    if state.fingerprint != current_fingerprint:
        return Decision(
            Verdict.BLOCK_FINGERPRINT,
            "Dane wersji demonstracyjnej pochodzą z innego komputera.",
        )

    first_run = _parse(state.first_run_iso)
    last_seen = _parse(state.last_seen_iso)
    if first_run is None or last_seen is None:
        return Decision(
            Verdict.BLOCK_TAMPERED,
            "Uszkodzone znaczniki czasu w stanie demonstracyjnym.",
        )

    # 4. Zegar cofnięty względem ostatniego uruchomienia = próba oszukania limitu.
    if now < last_seen - CLOCK_BACKWARD_TOLERANCE:
        return Decision(
            Verdict.BLOCK_CLOCK,
            "Wykryto cofnięcie zegara systemowego.",
        )

    # 5. Upływ okresu demonstracyjnego.
    expiry = first_run + timedelta(days=DEMO_PERIOD_DAYS)
    if now >= expiry:
        return Decision(
            Verdict.BLOCK_EXPIRED,
            "Okres wersji demonstracyjnej dobiegł końca.",
            days_left=0,
        )

    days_left = (expiry - now).days + (1 if (expiry - now).seconds else 0)
    return Decision(
        Verdict.ALLOW,
        "Wersja demonstracyjna aktywna.",
        days_left=max(0, days_left),
    )


def make_fresh_state(now: datetime, fingerprint: str) -> DemoState:
    """Tworzy stan dla pierwszego uruchomienia."""
    iso = now.isoformat()
    return DemoState(first_run_iso=iso, last_seen_iso=iso, fingerprint=fingerprint)


def touch_state(state: DemoState, now: datetime) -> DemoState:
    """Aktualizuje datę ostatniego uruchomienia, zachowując resztę stanu."""
    return DemoState(
        first_run_iso=state.first_run_iso,
        last_seen_iso=now.isoformat(),
        fingerprint=state.fingerprint,
    )