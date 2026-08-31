"""Odcisk sprzętowy komputera.

Służy do wykrycia, że stan wersji demonstracyjnej został skopiowany na inny
komputer razem z plikami. Odcisk liczony jest z cech sprzętu/systemu, które
przenoszą się razem z fizyczną maszyną, a nie razem z plikami programu.

OGRANICZENIE: to utrudnienie, nie zabezpieczenie kryptograficzne. Odcisk chroni
przed skopiowaniem całego folderu na inny komputer (odcisk się wtedy nie zgadza).
Nie chroni przed skopiowaniem samego .exe bez plików stanu - to świadomy,
zaakceptowany kompromis wybranego podejścia.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess

logger = logging.getLogger(__name__)

# Znacznik używany, gdy nie udało się odczytać żadnej cechy sprzętu. Odcisk
# nadal powstaje (spójny między uruchomieniami na tej samej maszynie), ale
# oparty na słabszych danych - patrz _fallback_identifiers.
_UNKNOWN = "unknown"


def _run_wmic(args: list[str]) -> list[str]:
    """Uruchamia zapytanie WMIC i zwraca niepuste wiersze wyniku.

    WMIC jest wycofywane w nowszych wersjach Windows, dlatego traktujemy jego
    brak jako sytuację normalną, nie błąd - odcisk oprze się wtedy na innych
    źródłach.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=0x08000000,  # CREATE_NO_WINDOW - bez migającego okna konsoli
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("Zapytanie %s nie powiodło się: %s", args, exc)
        return []

    lines = [line.strip() for line in result.stdout.splitlines()]
    # Pierwszy wiersz to zwykle nagłówek kolumny - pomijamy go.
    return [line for line in lines[1:] if line]


def _get_disk_serial() -> str:
    """Numer seryjny dysku systemowego (przez PowerShell, z fallbackiem na WMIC)."""
    # PowerShell jest dostępny na każdej wspieranej wersji Windows, w odróżnieniu
    # od wycofywanego WMIC.
    ps_cmd = (
        "Get-CimInstance Win32_DiskDrive | "
        "Select-Object -First 1 -ExpandProperty SerialNumber"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,
        )
        value = result.stdout.strip()
        if value:
            return value
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("PowerShell (dysk) nie powiódł się: %s", exc)

    lines = _run_wmic(["wmic", "diskdrive", "get", "serialnumber"])
    return lines[0] if lines else _UNKNOWN


def _get_baseboard_id() -> str:
    """Identyfikator (numer seryjny) płyty głównej."""
    ps_cmd = (
        "Get-CimInstance Win32_BaseBoard | "
        "Select-Object -First 1 -ExpandProperty SerialNumber"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,
        )
        value = result.stdout.strip()
        if value:
            return value
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("PowerShell (płyta) nie powiódł się: %s", exc)

    lines = _run_wmic(["wmic", "baseboard", "get", "serialnumber"])
    return lines[0] if lines else _UNKNOWN


def _get_machine_guid() -> str:
    """Identyfikator instalacji Windows z rejestru (MachineGuid).

    Stabilny w obrębie jednej instalacji systemu, nadpisywany dopiero przy
    reinstalacji Windows - dobre uzupełnienie cech czysto sprzętowych.
    """
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip() or _UNKNOWN
    except (OSError, ImportError) as exc:
        logger.debug("Odczyt MachineGuid nie powiódł się: %s", exc)
        return _UNKNOWN


def _fallback_identifiers() -> list[str]:
    """Słabsze cechy używane, gdy sprzętowe zawiodą - żeby odcisk nie był pusty."""
    import os
    import platform

    return [
        os.environ.get("COMPUTERNAME", _UNKNOWN),
        platform.node() or _UNKNOWN,
        platform.machine() or _UNKNOWN,
    ]


def compute_fingerprint() -> str:
    """Zwraca stabilny odcisk maszyny jako skrót heksadecymalny.

    Łączy kilka źródeł, żeby pojedyncza nieodczytana cecha nie zmieniała
    całości. Ta sama maszyna daje ten sam odcisk między uruchomieniami;
    inna maszyna niemal na pewno inny.
    """
    parts = [
        _get_machine_guid(),
        _get_disk_serial(),
        _get_baseboard_id(),
    ]

    # Jeśli wszystkie mocne źródła zawiodły, dokładamy słabsze - lepszy odcisk
    # oparty na nazwie komputera niż identyczny "unknown" na każdej maszynie.
    if all(p == _UNKNOWN for p in parts):
        logger.warning(
            "Nie odczytano żadnej cechy sprzętowej - odcisk oparty na danych zastępczych."
        )
        parts.extend(_fallback_identifiers())

    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()
    logger.debug("Obliczono odcisk maszyny (źródła: %d).", len([p for p in parts if p != _UNKNOWN]))
    return digest