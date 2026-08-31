"""Trwały stan wersji demonstracyjnej, zapisany redundantnie.

Ten sam zestaw danych (data pierwszego uruchomienia, data ostatniego
uruchomienia, odcisk maszyny) zapisujemy w kilku niezależnych miejscach:
plik w %LOCALAPPDATA% oraz wpis w rejestrze Windows. Dzięki temu usunięcie
jednej kopii nie wystarcza do zresetowania stanu - a wykryta niezgodność
między kopiami jest sygnałem manipulacji.

Zawartość jest zaciemniona, nie zaszyfrowana kryptograficznie. Celem jest
uniemożliwienie zmiany wartości zwykłym edytorem tekstu, nie ochrona przed
kimś, kto zdekompiluje program. To świadome, uczciwie nazwane ograniczenie.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Niepozorna nazwa - ma nie sugerować przeznaczenia przy przypadkowym natknięciu.
_DIR_NAME = "Microsoft Telemetry Cache"
_FILE_NAME = "mtc.dat"
_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\AppCache"
_REGISTRY_VALUE = "InstanceData"

# "Sekret" do zaciemnienia. Nie jest to prawdziwy klucz - patrz docstring modułu.
_OBFUSCATION_KEY = b"sv-monitor-demo-2026-state-guard"


@dataclass
class DemoState:
    """Trwały stan wersji demonstracyjnej.

    Attributes:
        first_run_iso: Data pierwszego uruchomienia (ISO 8601). Od niej liczony
            jest limit dni.
        last_seen_iso: Data ostatniego uruchomienia. Służy do wykrycia cofnięcia
            zegara systemowego.
        fingerprint: Odcisk maszyny z momentu pierwszego uruchomienia.
    """

    first_run_iso: str
    last_seen_iso: str
    fingerprint: str


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _encode(state: DemoState) -> str:
    """Serializuje i zaciemnia stan do postaci tekstowej.

    Dokłada skrót kontrolny, żeby wykryć ręczną próbę modyfikacji bajtów -
    zmieniona zawartość nie przejdzie weryfikacji przy odczycie.
    """
    payload = json.dumps(asdict(state), separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(payload + _OBFUSCATION_KEY).digest()[:8]
    obfuscated = _xor(checksum + payload, _OBFUSCATION_KEY)
    return base64.b64encode(obfuscated).decode("ascii")


def _decode(text: str) -> Optional[DemoState]:
    """Odwraca _encode. Zwraca None, gdy dane są uszkodzone lub zmodyfikowane."""
    try:
        obfuscated = base64.b64decode(text.encode("ascii"))
        raw = _xor(obfuscated, _OBFUSCATION_KEY)
        checksum, payload = raw[:8], raw[8:]

        expected = hashlib.sha256(payload + _OBFUSCATION_KEY).digest()[:8]
        if checksum != expected:
            logger.warning("Suma kontrolna stanu niezgodna - dane zmodyfikowane.")
            return None

        data = json.loads(payload.decode("utf-8"))
        return DemoState(
            first_run_iso=data["first_run_iso"],
            last_seen_iso=data["last_seen_iso"],
            fingerprint=data["fingerprint"],
        )
    except (ValueError, KeyError, TypeError) as exc:
        logger.debug("Nie udało się odczytać stanu: %s", exc)
        return None


# --- Kopia w pliku --------------------------------------------------------


def _file_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / _DIR_NAME / _FILE_NAME


def _read_file() -> Optional[DemoState]:
    path = _file_path()
    if not path.exists():
        return None
    try:
        return _decode(path.read_text(encoding="ascii"))
    except OSError as exc:
        logger.debug("Nie udało się odczytać pliku stanu: %s", exc)
        return None


def _write_file(state: DemoState) -> bool:
    path = _file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_encode(state), encoding="ascii")
        return True
    except OSError as exc:
        logger.warning("Nie udało się zapisać pliku stanu: %s", exc)
        return False


# --- Kopia w rejestrze ----------------------------------------------------


def _read_registry() -> Optional[DemoState]:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REGISTRY_PATH, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, _REGISTRY_VALUE)
            return _decode(str(value))
    except (OSError, ImportError) as exc:
        logger.debug("Nie udało się odczytać stanu z rejestru: %s", exc)
        return None


def _write_registry(state: DemoState) -> bool:
    try:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, _REGISTRY_PATH, 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, _REGISTRY_VALUE, 0, winreg.REG_SZ, _encode(state))
        return True
    except (OSError, ImportError) as exc:
        logger.warning("Nie udało się zapisać stanu do rejestru: %s", exc)
        return False


# --- Interfejs publiczny --------------------------------------------------


@dataclass
class StoreReadResult:
    """Wynik odczytu ze wszystkich kopii stanu.

    Attributes:
        state: Odczytany stan, jeśli dało się go ustalić.
        all_empty: Czy WSZYSTKIE kopie były puste (kandydat na pierwsze uruchomienie).
        inconsistent: Czy kopie istnieją, ale się różnią lub część zniknęła
            (sygnał manipulacji).
    """

    state: Optional[DemoState]
    all_empty: bool
    inconsistent: bool


def read_state() -> StoreReadResult:
    """Odczytuje stan ze wszystkich kopii i ocenia ich spójność.

    Rozróżnienie jest sednem zasady fail-closed:
    - wszystkie kopie puste  -> prawdziwe pierwsze uruchomienie (dozwolone),
    - kopie zgodne           -> normalny stan (dozwolone, jeśli reguły przejdą),
    - część pusta / rozbieżne -> manipulacja (blokada).
    """
    copies = [_read_file(), _read_registry()]
    present = [c for c in copies if c is not None]

    if not present:
        return StoreReadResult(state=None, all_empty=True, inconsistent=False)

    if len(present) < len(copies):
        # Któraś kopia zniknęła lub uległa uszkodzeniu, a inna nie - to nie jest
        # zwykłe pierwsze uruchomienie, tylko naruszenie kompletu.
        logger.warning("Część kopii stanu jest nieobecna - możliwa manipulacja.")
        return StoreReadResult(state=present[0], all_empty=False, inconsistent=True)

    first = present[0]
    for other in present[1:]:
        if (first.first_run_iso != other.first_run_iso
                or first.fingerprint != other.fingerprint):
            logger.warning("Kopie stanu różnią się między sobą - możliwa manipulacja.")
            return StoreReadResult(state=first, all_empty=False, inconsistent=True)

    return StoreReadResult(state=first, all_empty=False, inconsistent=False)


def write_state(state: DemoState) -> bool:
    """Zapisuje stan do wszystkich kopii. Zwraca True, jeśli KAŻDA się powiodła.

    Wymóg powodzenia wszystkich kopii jest celowy: gdyby jedna się nie zapisała,
    przy następnym uruchomieniu komplet byłby niespójny i program by się
    zablokował. Lepiej wiedzieć o problemie od razu.
    """
    ok_file = _write_file(state)
    ok_reg = _write_registry(state)
    if not (ok_file and ok_reg):
        logger.warning(
            "Nie udało się zapisać wszystkich kopii stanu (plik=%s, rejestr=%s).",
            ok_file, ok_reg,
        )
    return ok_file and ok_reg