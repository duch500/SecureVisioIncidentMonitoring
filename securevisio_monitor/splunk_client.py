"""Klient REST API Splunka - odczyt lookupa es_notable_events.

Zaprojektowany zgodnie z ustaleniami z fazy PoC (test_splunk_connection.py):
- Uwierzytelnianie: nagłówek "Authorization: Bearer <token>" (potwierdzone
  empirycznie i zgodne z oficjalną dokumentacją Splunka).
- Odczyt przez zapytanie SPL w trybie "oneshot" - synchroniczne, bez
  tworzenia trwałego search joba do odpytywania.
- Źródło danych: `| inputlookup es_notable_events` - gotowy, odświeżany co
  ok. 5 minut przez wewnętrzny mechanizm Splunk ES (search "ESS - Notable
  Events"), nie searcha tworzonego przez tę aplikację. Aplikacja nigdy nie
  tworzy własnego, kosztownego zapytania po indeksie - to była kluczowa
  ustalona z adminem zasada, żeby nie obciążać Search Heada.
- Wykrywanie nowych incydentów: `status=1`, potwierdzone empirycznie na
  żywym incydencie w środowisku testowym (nie założone z dokumentacji
  ogólnej Splunka, która bywa dostosowywana per-instalacja).

To jest moduł czysto sieciowy/parsujący - nie zna nic o GUI, wątkach ani
o pozostałej części aplikacji. Integracja z wątkiem monitorującym i
z istniejącym mechanizmem wykrywania przejść stanów (state_machine.py)
następuje w kolejnym etapie.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .config import SplunkEnvironment

logger = logging.getLogger(__name__)

# Pole statusu, dla którego es_notable_events oznacza nowy, nieprzejrzany
# incydent. Potwierdzone empirycznie na żywym incydencie - NIE jest to
# założenie ze standardowej dokumentacji Splunk ES, bo numeracja bywa
# dostosowywana per-instalacja (patrz historia PoC tej integracji).
NEW_INCIDENT_STATUS = "1"

# Pola pobierane z lookupa - zawężone do tego, czego wymaga wykrywanie
# i wyświetlanie (ustalone zakresowo: "nazwa reguły + środowisko i tyle",
# bez urgency/security_domain na start).
_FIELDS = ("event_id", "status", "rule_name", "_time", "owner")

_REQUEST_TIMEOUT_SEC = 15


def decode_token_expiry(token: str) -> Optional[datetime]:
    """Odczytuje rzeczywisty termin ważności z tokenu JWT (pole "exp").

    Tokeny Splunk Authentication Token to JWT (zaczynają się od "eyJ") - drugi
    segment (payload), zdekodowany z base64url, to zwykły JSON zawierający
    m.in. "exp" (czas wygaśnięcia jako Unix timestamp), jeśli admin ustawił
    taki token z określonym czasem życia. To jest RZECZYWISTA wartość, nie
    założenie - różne tokeny mogą mieć różny okres ważności (potwierdzone
    wprost: "nie każdy token ma 14 dni ważności"), więc nie zgadujemy, tylko
    czytamy to, co token faktycznie o sobie mówi.

    Nie weryfikuje podpisu JWT - to nie jest kontrola bezpieczeństwa (o tym
    i tak decyduje wyłącznie serwer Splunk przy każdym zapytaniu), tylko
    odczyt metadanych do wyświetlenia operatorowi.

    Returns:
        Termin ważności jako datetime (UTC), albo None, jeśli token nie jest
        poprawnym JWT, nie ma pola "exp", albo cokolwiek innego nie pozwala
        tego jednoznacznie odczytać - w takim wypadku po prostu NIE MAMY tej
        informacji, nie zgadujemy zastępczej wartości.
    """
    if not token or token.count(".") != 2:
        return None

    try:
        payload_b64 = token.split(".")[1]
        # base64url wymaga uzupełnienia do wielokrotności 4 znaków paddingiem "=".
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes)
        exp = payload.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(float(exp), tz=timezone.utc)
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error):
        return None


class SplunkErrorKind(Enum):
    """Rodzaj niepowodzenia - rozstrzyga, jaki komunikat pokazać operatorowi.

    Rozróżnienie jest celowe (ustalone wprost): pokazywanie "za dużo zapytań"
    przy realnej awarii sieci wprowadzałoby w błąd co do prawdziwej przyczyny,
    i odwrotnie.
    """

    RATE_LIMITED = "rate_limited"      # HTTP 429
    AUTH_FAILED = "auth_failed"        # HTTP 401/403 - token zły/wygasł/wyłączony
    TIMEOUT = "timeout"                # brak odpowiedzi w czasie
    CONNECTION = "connection"          # host nieosiągalny, TLS, DNS
    SERVER_ERROR = "server_error"      # HTTP 5xx
    UNEXPECTED = "unexpected"          # cokolwiek innego (parsowanie, itp.)


@dataclass(frozen=True)
class SplunkQueryError(Exception):
    """Niepowodzenie zapytania do Splunka, z rozstrzygniętym rodzajem przyczyny."""

    kind: SplunkErrorKind
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class SplunkIncident:
    """Pojedynczy wiersz z es_notable_events, po parsowaniu.

    Odpowiednik Incident z uia_reader.py (SecureVisio) - ta sama rola,
    inny format źródłowy. incident_id odpowiada Id, is_new zastępuje
    porównanie tekstu statusu (Splunk koduje stan liczbowo, nie opisowo).
    """

    incident_id: str
    status: str
    rule_name: str
    owner: str
    time_raw: str

    @property
    def is_new(self) -> bool:
        return self.status == NEW_INCIDENT_STATUS

    @property
    def network_map(self) -> str:
        """Zgodność z duck-typingiem state_machine.py (Incident.network_map).

        state_machine.py odczytuje tę właściwość przez getattr(...,"") jako
        opis miejsca zdarzenia do wyświetlenia na alarmie. Dla Splunka
        najbardziej sensowną wartością jest nazwa reguły korelacyjnej -
        ustalone wprost: "wystarczy nazwa reguły, klient środowisko i tyle".
        Dzięki tej właściwości state_machine.py działa z SplunkIncident bez
        żadnego adaptera pośredniczącego.
        """
        return self.rule_name


def classify_exception(exc: Exception) -> SplunkErrorKind:
    """Rozstrzyga rodzaj błędu na podstawie wyjątku biblioteki requests."""
    if isinstance(exc, Timeout):
        return SplunkErrorKind.TIMEOUT
    if isinstance(exc, RequestsConnectionError):
        return SplunkErrorKind.CONNECTION
    return SplunkErrorKind.UNEXPECTED


def classify_status_code(status_code: int) -> SplunkErrorKind:
    """Rozstrzyga rodzaj błędu na podstawie kodu HTTP odpowiedzi."""
    if status_code == 429:
        return SplunkErrorKind.RATE_LIMITED
    if status_code in (401, 403):
        return SplunkErrorKind.AUTH_FAILED
    if 500 <= status_code < 600:
        return SplunkErrorKind.SERVER_ERROR
    return SplunkErrorKind.UNEXPECTED


def error_message_for(kind: SplunkErrorKind, detail: str = "") -> str:
    """Buduje komunikat dla operatora, dopasowany do rodzaju błędu.

    Ustalone wprost: komunikaty mają odzwierciedlać rzeczywistą przyczynę,
    nie jeden uniwersalny opis "błąd połączenia" dla wszystkiego.
    """
    messages = {
        SplunkErrorKind.RATE_LIMITED: "TOO MANY REQUESTS - Search Head odrzucił zapytanie z powodu przeciążenia.",
        SplunkErrorKind.AUTH_FAILED: "Błąd autoryzacji - token nieprawidłowy, wygasły albo wyłączony.",
        SplunkErrorKind.TIMEOUT: "Brak odpowiedzi Search Heada w wyznaczonym czasie.",
        SplunkErrorKind.CONNECTION: "Nie udało się połączyć z Search Headem (host nieosiągalny).",
        SplunkErrorKind.SERVER_ERROR: "Błąd po stronie serwera Splunk.",
        SplunkErrorKind.UNEXPECTED: "Nieoczekiwany błąd podczas komunikacji ze Splunkiem.",
    }
    base = messages.get(kind, messages[SplunkErrorKind.UNEXPECTED])
    return f"{base} ({detail})" if detail else base


class SplunkClient:
    """Klient do odczytu es_notable_events z jednego środowiska Splunk.

    Jeden klient obsługuje jedno SplunkEnvironment - odpowiednik jednej pary
    (adres, token). Nie utrzymuje żadnego stanu między wywołaniami poza samą
    konfiguracją; wykrywanie przejść stanów (co jest "nowe") należy do
    warstwy wyższej (state_machine.py / adapter, w kolejnym etapie).
    """

    def __init__(self, environment: SplunkEnvironment) -> None:
        self._env = environment

    def fetch_incidents(self) -> list[SplunkIncident]:
        """Odczytuje pełną zawartość es_notable_events.

        Zwraca WSZYSTKIE wiersze, nie tylko status=1 - zgodnie z ustaloną
        zasadą "Splunk dostarcza pełny, bieżący obraz; to warstwa wyższa
        aplikacji pamięta, co już widziała, i wykrywa różnicę" (ta sama
        zasada co przy pełnym zrzucie stanu w SecureVisio).

        Raises:
            SplunkQueryError: z rozstrzygniętym rodzajem przyczyny.
        """
        spl = "| inputlookup es_notable_events | table " + ", ".join(_FIELDS)
        rows = self._run_oneshot(spl)
        return [self._parse_row(row) for row in rows]

    def _parse_row(self, row: dict) -> SplunkIncident:
        return SplunkIncident(
            incident_id=str(row.get("event_id", "")),
            status=str(row.get("status", "")),
            rule_name=str(row.get("rule_name", "")),
            owner=str(row.get("owner", "")),
            time_raw=str(row.get("_time", "")),
        )

    def _run_oneshot(self, spl: str) -> list[dict]:
        headers = {"Authorization": f"Bearer {self._env.token}"}
        payload = {
            "search": spl if spl.strip().startswith("|") else f"search {spl}",
            "output_mode": "json",
            "exec_mode": "oneshot",
        }

        try:
            resp = requests.post(
                f"{self._env.rest_base_url}/services/search/jobs",
                headers=headers,
                data=payload,
                verify=self._env.verify_ssl,
                timeout=_REQUEST_TIMEOUT_SEC,
            )
        except RequestException as exc:
            kind = classify_exception(exc)
            logger.warning(
                "Środowisko %s: błąd zapytania Splunk (%s): %s",
                self._env.label, kind.value, exc,
            )
            raise SplunkQueryError(kind, error_message_for(kind, str(exc))) from exc

        if resp.status_code != 200:
            kind = classify_status_code(resp.status_code)
            detail = f"HTTP {resp.status_code}"
            logger.warning(
                "Środowisko %s: %s (%s)", self._env.label, error_message_for(kind), detail
            )
            raise SplunkQueryError(kind, error_message_for(kind, detail))

        try:
            data = resp.json()
        except ValueError as exc:
            raise SplunkQueryError(
                SplunkErrorKind.UNEXPECTED,
                error_message_for(SplunkErrorKind.UNEXPECTED, "nieprawidłowa odpowiedź JSON"),
            ) from exc

        return data.get("results", [])


def fetch_with_retry(client: SplunkClient, max_attempts: int = 2) -> list[SplunkIncident]:
    """Ponawia odczyt do max_attempts razy, zanim zgłosi ostateczne niepowodzenie.

    Ustalone wprost: "dłuższa próba, a po dwóch próbach ma informować" -
    stąd domyślnie 2 próby, nie więcej. Zwraca wynik pierwszej udanej próby;
    jeśli wszystkie zawiodą, propaguje błąd z OSTATNIEJ próby (najbardziej
    aktualny obraz sytuacji).
    """
    last_error: Optional[SplunkQueryError] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.fetch_incidents()
        except SplunkQueryError as exc:
            last_error = exc
            logger.debug(
                "Próba %d/%d nieudana (%s): %s", attempt, max_attempts, exc.kind.value, exc
            )

    assert last_error is not None  # pętla wykonała się co najmniej raz
    raise last_error