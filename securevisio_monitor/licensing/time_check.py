"""Weryfikacja zegara systemowego względem zewnętrznego źródła czasu.

Cofnięcie zegara systemowego wykrywamy lokalnie (rules.py, porównanie
z ostatnią zapamiętaną datą), ale to nie chroni przed przestawieniem zegara
PRZED pierwszym uruchomieniem albo między dwoma uruchomieniami w sposób,
który nie zostawia lokalnego śladu. Dlatego dodatkowo pytamy zewnętrzny,
publiczny serwer czasu "która jest teraz naprawdę" i porównujemy z zegarem
systemowym.

Ustalone zachowanie: brak możliwości potwierdzenia czasu z zewnątrz (offline,
zablokowany port, serwer nie odpowiada) = odmowa działania. Program i tak
wymaga sieci do monitorowania SecureVisio, więc to nie jest dodatkowe
ograniczenie dla legalnego użytkownika.
"""

from __future__ import annotations

import logging
import socket
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Tolerancja rozbieżności między zegarem systemowym a czasem z serwera.
MAX_CLOCK_DRIFT = timedelta(minutes=10)

# Publiczne serwery NTP (Network Time Protocol) - ten sam mechanizm, z którego
# korzysta Windows do własnej synchronizacji czasu. Kilka adresów na wypadek,
# gdyby jeden akurat nie odpowiadał.
_NTP_SERVERS = (
    "time.windows.com",
    "pool.ntp.org",
    "time.google.com",
)

_NTP_PORT = 123
_NTP_TIMEOUT_SEC = 4
# Różnica między epoką NTP (1900) a epoką Unix (1970), w sekundach.
_NTP_TO_UNIX_EPOCH = 2208988800


@dataclass
class TimeCheckResult:
    """Wynik próby weryfikacji czasu.

    Attributes:
        available: Czy udało się uzyskać czas z jakiegokolwiek serwera.
        server_time: Czas zgłoszony przez serwer (UTC), jeśli dostępny.
        drift: Różnica |zegar systemowy - czas serwera|, jeśli dostępna.
        within_tolerance: Czy rozbieżność mieści się w dozwolonym progu.
            False zarówno przy przekroczonym progu, jak i przy braku
            odpowiedzi - fail-closed obejmuje oba przypadki jednakowo.
        source: Nazwa serwera, który odpowiedział, albo powód niepowodzenia.
    """

    available: bool
    server_time: Optional[datetime]
    drift: Optional[timedelta]
    within_tolerance: bool
    source: str


def _query_ntp(server: str) -> Optional[datetime]:
    """Odpytuje pojedynczy serwer NTP. Zwraca czas UTC albo None."""
    # Standardowy pakiet zapytania NTPv3/v4 - pierwszy bajt ustawia wersję
    # protokołu i tryb "client request".
    packet = b"\x1b" + 47 * b"\0"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(_NTP_TIMEOUT_SEC)
            sock.sendto(packet, (server, _NTP_PORT))
            response, _ = sock.recvfrom(48)
    except (OSError, socket.timeout) as exc:
        logger.debug("Serwer czasu %s nie odpowiedział: %s", server, exc)
        return None

    if len(response) < 48:
        return None

    # Znacznik czasu "transmit timestamp" w polu od bajtu 40, format NTP
    # (32-bitowe sekundy od 1900 + 32-bitowy ułamek sekundy).
    seconds, fraction = struct.unpack("!II", response[40:48])
    unix_seconds = seconds - _NTP_TO_UNIX_EPOCH + fraction / 2**32
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def check_time(servers: tuple[str, ...] = _NTP_SERVERS) -> TimeCheckResult:
    """Sprawdza zegar systemowy względem pierwszego odpowiadającego serwera.

    Próbuje kolejnych serwerów z listy, dopóki żaden nie odpowie albo któryś
    się nie powiedzie - pojedynczy niedostępny serwer nie blokuje weryfikacji.
    """
    local_now = datetime.now(timezone.utc)

    for server in servers:
        server_time = _query_ntp(server)
        if server_time is None:
            continue

        drift = abs(local_now - server_time)
        within = drift <= MAX_CLOCK_DRIFT

        if not within:
            logger.warning(
                "Rozbieżność zegara %s przekracza tolerancję %s (serwer: %s).",
                drift, MAX_CLOCK_DRIFT, server,
            )
        else:
            logger.debug("Zegar zweryfikowany przez %s, rozbieżność %s.", server, drift)

        return TimeCheckResult(
            available=True,
            server_time=server_time,
            drift=drift,
            within_tolerance=within,
            source=server,
        )

    logger.warning("Żaden serwer czasu nie odpowiedział - brak weryfikacji.")
    return TimeCheckResult(
        available=False,
        server_time=None,
        drift=None,
        within_tolerance=False,
        source="brak odpowiedzi żadnego serwera",
    )