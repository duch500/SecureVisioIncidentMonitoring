"""Pojedynczy punkt wejścia weryfikacji wersji demonstracyjnej.

Łączy: odcisk maszyny, magazyn stanu, reguły lokalne i weryfikację czasu
z zewnętrznego serwera w jedną decyzję "czy wolno uruchomić monitorowanie".

To jedyna funkcja tego podpakietu, którą powinna wywoływać reszta aplikacji -
worker.py i main_window.py nie muszą znać szczegółów odcisku, magazynu ani
protokołu NTP.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..about import APP_AUTHOR, APP_CONTACT
from . import rules, state_store, time_check
from .fingerprint import compute_fingerprint
from .rules import DEMO_PERIOD_DAYS, Decision, Verdict

logger = logging.getLogger(__name__)


@dataclass
class LicenseCheckResult:
    """Pełny wynik weryfikacji - decyzja lokalna plus informacja o czasie.

    Attributes:
        decision: Werdykt reguł lokalnych (fingerprint.py + rules.py).
        time_result: Wynik zapytania do serwera czasu.
        final_allowed: Ostateczna decyzja po uwzględnieniu obu źródeł.
        message: Komunikat gotowy do pokazania w GUI.
    """

    decision: Decision
    time_result: Optional[time_check.TimeCheckResult]
    final_allowed: bool
    message: str


def _contact_line() -> str:
    """Zwraca informację, z kim się kontaktować - pomija pusty kontakt."""
    if APP_CONTACT.strip():
        return f"Autor: {APP_AUTHOR} ({APP_CONTACT})"
    return f"Autor: {APP_AUTHOR}"


def _format_message(decision: Decision, time_result: Optional[time_check.TimeCheckResult]) -> str:
    """Buduje komunikat dla użytkownika - bez ujawniania mechaniki wykrywania.

    Celowo nie mówimy wprost "wykryto manipulację odciskiem/plikiem" - taki
    komunikat byłby wskazówką, co dokładnie ominąć. Rozróżniamy tylko
    "wygasło" (neutralne, oczekiwane) od "problem" (nieoczekiwane, każące
    skontaktować się z autorem).
    """
    if decision.verdict == Verdict.BLOCK_EXPIRED:
        return (
            f"Okres wersji demonstracyjnej ({DEMO_PERIOD_DAYS} dni) dobiegł końca.\n\n"
            "Aby kontynuować korzystanie z programu, skontaktuj się z autorem.\n"
            f"{_contact_line()}"
        )

    if time_result is not None and not time_result.available:
        return (
            "Nie udało się zweryfikować czasu z serwerem zewnętrznym.\n"
            "Sprawdź połączenie z internetem i spróbuj ponownie."
        )

    if time_result is not None and not time_result.within_tolerance:
        return (
            "Zegar systemowy komputera znacząco odbiega od czasu rzeczywistego.\n"
            "Sprawdź ustawienia daty i godziny, a następnie spróbuj ponownie."
        )

    if decision.verdict in (
        Verdict.BLOCK_TAMPERED,
        Verdict.BLOCK_CLOCK,
        Verdict.BLOCK_FINGERPRINT,
    ):
        return (
            "Nie można zweryfikować wersji demonstracyjnej na tym komputerze.\n\n"
            "Skontaktuj się z autorem w sprawie dalszego korzystania z programu.\n"
            f"{_contact_line()}"
        )

    return decision.reason


def check_license() -> LicenseCheckResult:
    """Wykonuje pełną weryfikację i zwraca decyzję gotową do użycia w GUI.

    Kolejność ma znaczenie i jest celowa:
    1. Reguły lokalne najpierw - jeśli stan jest jawnie zmanipulowany albo
       zegar lokalnie cofnięty, nie ma sensu obciążać sieci zapytaniem.
       Wyjątek: pierwsze uruchomienie i aktywne demo muszą przejść przez
       weryfikację czasu, zanim cokolwiek zapiszemy - inaczej ktoś mógłby
       ustawić zegar w przyszłość, "kupić" sobie dodatkowe dni, i dopiero
       potem zostać złapany przy kolejnym uruchomieniu.
    2. Weryfikacja czasu z zewnątrz - wymagana zawsze, gdy reguły lokalne
       nie zablokowały jeszcze wcześniej. Brak odpowiedzi = odmowa (program
       i tak wymaga sieci do monitorowania SecureVisio).
    """
    fingerprint = compute_fingerprint()
    read_result = state_store.read_state()
    local_now = datetime.now()

    decision = rules.evaluate(read_result, local_now, fingerprint)

    # Manipulacja lub cofnięty zegar wykryte lokalnie - blokada natychmiastowa,
    # bez odpytywania sieci. Rozbieżność, którą i tak wykrylibyśmy przez NTP,
    # już została złapana taniej.
    if decision.verdict in (Verdict.BLOCK_TAMPERED, Verdict.BLOCK_CLOCK, Verdict.BLOCK_FINGERPRINT):
        message = _format_message(decision, None)
        logger.warning("Weryfikacja lokalna zablokowała start: %s", decision.verdict.value)
        return LicenseCheckResult(decision, None, False, message)

    # Wygasłe demo - również nie ma potrzeby pytać sieci, wynik i tak jest negatywny.
    if decision.verdict == Verdict.BLOCK_EXPIRED:
        message = _format_message(decision, None)
        return LicenseCheckResult(decision, None, False, message)

    # Pozostały werdykt to ALLOW albo ALLOW_FIRST_RUN - wymaga potwierdzenia
    # czasu z zewnątrz przed dopuszczeniem albo zapisaniem stanu.
    time_result = time_check.check_time()

    if not time_result.available or not time_result.within_tolerance:
        message = _format_message(decision, time_result)
        logger.warning(
            "Weryfikacja czasu nie powiodła się (dostępna=%s, w_tolerancji=%s).",
            time_result.available, time_result.within_tolerance,
        )
        return LicenseCheckResult(decision, time_result, False, message)

    # Wszystko w porządku - zapisujemy/aktualizujemy stan.
    if decision.is_first_run:
        new_state = rules.make_fresh_state(local_now, fingerprint)
    else:
        new_state = rules.touch_state(read_result.state, local_now)

    if not state_store.write_state(new_state):
        # Zapis się nie powiódł (np. brak praw do rejestru) - nie blokujemy
        # bieżącej sesji z tego powodu, ale odnotowujemy w logu. Kolejne
        # uruchomienie i tak wykryje niespójność, jeśli część się zapisała.
        logger.warning("Nie udało się w pełni zapisać stanu wersji demonstracyjnej.")

    message = _format_message(decision, time_result)
    return LicenseCheckResult(decision, time_result, True, message)