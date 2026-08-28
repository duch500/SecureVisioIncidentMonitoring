"""Konfiguracja aplikacji: profile klientów i ustawienia globalne.

Odpowiedzialność modułu ogranicza się do wczytywania, walidacji i zapisu
ustawień - nie zawiera logiki odczytu okien ani wykrywania zdarzeń.

Plik konfiguracyjny (domyślnie settings.json) jest edytowalny ręcznie, ale
docelowo ma być zarządzany przez GUI. Struktura jest projektowana pod kątem
czytelności przy ręcznej edycji, na wypadek potrzeby szybkiej poprawki.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = Path("settings.json")
DEFAULT_INTERVAL_SEC = 10
DEFAULT_ALARM_DISPLAY_SEC = 10
DEFAULT_ALARM_REPEAT_SEC = 60
DEFAULT_PHRASES = ("Nowe Zdarzenie", "New Event")

# Tryby alarmowania. Wzajemnie wykluczające się - jednocześnie aktywny jest
# dokładnie jeden.
ALARM_MODE_FULLSCREEN = "fullscreen"
ALARM_MODE_TOAST = "toast"
ALARM_MODES = (ALARM_MODE_FULLSCREEN, ALARM_MODE_TOAST)

# Zabezpieczenie przed błędem w konfiguracji (np. wpisanym ręcznie 0 lub
# ujemną wartością), który zamieniłby monitor w pętlę obciążającą CPU.
MIN_INTERVAL_SEC = 2


class ConfigError(Exception):
    """Błąd wczytywania lub walidacji konfiguracji."""


@dataclass
class ClientProfile:
    """Konfiguracja pojedynczego monitorowanego środowiska/klienta.

    Attributes:
        label: Nazwa wyświetlana na alarmie i w GUI (np. "Klient A").
        exe_path: Pełna ścieżka do pliku wykonywalnego tej instancji.
            Gdy ustawiona, ma pierwszeństwo przed automatycznym wykrywaniem
            po wzorcu ścieżki (odpowiednik strategii "manual" w resolverze).
        phrases: Frazy statusu oznaczające nowe zdarzenie. Pusta krotka
            oznacza użycie globalnych ustawień z AppSettings.
        enabled: Czy klient ma być aktywnie monitorowany.
    """

    label: str
    exe_path: str = ""
    phrases: tuple[str, ...] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ConfigError("Etykieta klienta nie może być pusta.")
        # Normalizacja do krotki - łatwiej porównywać i hashować przy potrzebie.
        self.phrases = tuple(p for p in self.phrases if p.strip())

    def effective_phrases(self, global_phrases: tuple[str, ...]) -> tuple[str, ...]:
        """Frazy tego klienta, z fallbackiem na ustawienia globalne."""
        return self.phrases if self.phrases else global_phrases


@dataclass
class AppSettings:
    """Ustawienia globalne aplikacji.

    Attributes:
        base_dir: Katalog bazowy, pod którym leżą katalogi klientów -
            podstawa automatycznego rozpoznawania po wzorcu ścieżki.
            Pusty string wyłącza tę strategię (zostaje tylko manual/nierozpoznany).
        interval_sec: Odstęp między kolejnymi sprawdzeniami wszystkich okien.
        alarm_display_sec: Czas wyświetlania ekranu alarmu przed auto-ukryciem.
        alarm_repeat_sec: Odstęp do ponownego pokazania nieobsłużonego alarmu.
        default_phrases: Domyślne frazy nowego zdarzenia dla klientów bez
            własnej konfiguracji.
        alert_on_first_scan: Czy alarmować o zdarzeniach zastanych przy starcie.
        alarm_mode: Sposób alarmowania - "fullscreen" (pełnoekranowe ekrany
            na wszystkich monitorach) albo "toast" (powiadomienia systemowe
            Windows w rogu ekranu).
        sound_enabled: Czy odtwarzać dźwięk przy alarmie o nowym zdarzeniu.
        sound_file: Nazwa pliku z katalogu sounds/. Pusta oznacza domyślny.
        sound_volume: Głośność 0-100, nakładana na głośność systemu.
        clients: Lista skonfigurowanych profili klientów.
    """

    base_dir: str = ""
    interval_sec: int = DEFAULT_INTERVAL_SEC
    alarm_display_sec: int = DEFAULT_ALARM_DISPLAY_SEC
    alarm_repeat_sec: int = DEFAULT_ALARM_REPEAT_SEC
    default_phrases: tuple[str, ...] = DEFAULT_PHRASES
    alert_on_first_scan: bool = True
    alarm_mode: str = ALARM_MODE_FULLSCREEN
    sound_enabled: bool = True
    sound_file: str = ""
    sound_volume: int = 80
    clients: list[ClientProfile] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.interval_sec < MIN_INTERVAL_SEC:
            raise ConfigError(
                f"interval_sec musi wynosić co najmniej {MIN_INTERVAL_SEC}s "
                f"(otrzymano {self.interval_sec})."
            )
        if self.alarm_display_sec <= 0:
            raise ConfigError("alarm_display_sec musi być dodatnie.")
        if self.alarm_repeat_sec <= 0:
            raise ConfigError("alarm_repeat_sec musi być dodatnie.")
        if not 0 <= self.sound_volume <= 100:
            raise ConfigError("sound_volume musi mieścić się w zakresie 0-100.")
        if self.alarm_mode not in ALARM_MODES:
            raise ConfigError(
                f"alarm_mode musi być jedną z wartości: {', '.join(ALARM_MODES)} "
                f"(otrzymano '{self.alarm_mode}')."
            )

        self.default_phrases = tuple(p for p in self.default_phrases if p.strip())
        if not self.default_phrases:
            logger.warning(
                "Brak domyślnych fraz nowego zdarzenia - klienci bez własnych "
                "fraz nie wygenerują żadnego alarmu."
            )

        self._check_duplicate_labels()

    def _check_duplicate_labels(self) -> None:
        seen: dict[str, str] = {}
        for client in self.clients:
            key = client.label.strip().casefold()
            if key in seen:
                raise ConfigError(
                    f"Zduplikowana etykieta klienta: '{client.label}' "
                    f"(koliduje z '{seen[key]}'). Etykiety muszą być unikalne."
                )
            seen[key] = client.label

    def manual_map(self) -> dict[str, str]:
        """Mapa ścieżka_exe -> etykieta dla klientów z ręcznie przypisaną ścieżką.

        Format zgodny z ClientResolver.manual_map (window_resolver.py).
        """
        return {c.exe_path: c.label for c in self.clients if c.exe_path.strip()}

    def enabled_clients(self) -> list[ClientProfile]:
        """Zwraca tylko klientów oznaczonych jako aktywnie monitorowani."""
        return [c for c in self.clients if c.enabled]

    def find_client(self, label: str) -> Optional[ClientProfile]:
        """Wyszukuje profil klienta po etykiecie (bez uwzględniania wielkości liter)."""
        key = label.strip().casefold()
        for client in self.clients:
            if client.label.strip().casefold() == key:
                return client
        return None

    def add_client(self, client: ClientProfile) -> None:
        """Dodaje nowego klienta, odrzucając duplikat etykiety."""
        if self.find_client(client.label) is not None:
            raise ConfigError(f"Klient '{client.label}' już istnieje.")
        self.clients.append(client)

    def remove_client(self, label: str) -> bool:
        """Usuwa klienta po etykiecie. Zwraca True, jeśli coś usunięto."""
        client = self.find_client(label)
        if client is None:
            return False
        self.clients.remove(client)
        return True

    # --- Serializacja ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["default_phrases"] = list(self.default_phrases)
        for client_dict in data["clients"]:
            client_dict["phrases"] = list(client_dict["phrases"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        raw_clients = data.get("clients", [])
        clients = [
            ClientProfile(
                label=c["label"],
                exe_path=c.get("exe_path", ""),
                phrases=tuple(c.get("phrases", ())),
                enabled=c.get("enabled", True),
            )
            for c in raw_clients
        ]
        return cls(
            base_dir=data.get("base_dir", ""),
            interval_sec=data.get("interval_sec", DEFAULT_INTERVAL_SEC),
            alarm_display_sec=data.get("alarm_display_sec", DEFAULT_ALARM_DISPLAY_SEC),
            alarm_repeat_sec=data.get("alarm_repeat_sec", DEFAULT_ALARM_REPEAT_SEC),
            default_phrases=tuple(data.get("default_phrases", DEFAULT_PHRASES)),
            alert_on_first_scan=data.get("alert_on_first_scan", True),
            alarm_mode=data.get("alarm_mode", ALARM_MODE_FULLSCREEN),
            sound_enabled=data.get("sound_enabled", True),
            sound_file=data.get("sound_file", ""),
            sound_volume=data.get("sound_volume", 80),
            clients=clients,
        )


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    """Wczytuje ustawienia z pliku JSON.

    Gdy plik nie istnieje, zwraca ustawienia domyślne (bez klientów) zamiast
    rzucać wyjątek - naturalny stan przy pierwszym uruchomieniu aplikacji.

    Raises:
        ConfigError: Gdy plik istnieje, ale jest uszkodzony albo zawiera
            nieprawidłowe dane (walidacja w AppSettings.__post_init__).
    """
    if not path.exists():
        logger.debug("Plik konfiguracyjny %s nie istnieje - używam ustawień domyślnych.", path)
        return AppSettings()

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Nie udało się odczytać pliku {path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Plik {path} zawiera nieprawidłowy JSON: {exc}") from exc

    try:
        return AppSettings.from_dict(data)
    except (KeyError, TypeError, ConfigError) as exc:
        raise ConfigError(f"Plik {path} ma nieprawidłową strukturę: {exc}") from exc


def save_settings(settings: AppSettings, path: Path = DEFAULT_SETTINGS_PATH) -> None:
    """Zapisuje ustawienia do pliku JSON.

    Zapis przez plik tymczasowy + atomowa podmiana - zabezpieczenie przed
    pozostawieniem pliku w połowie zapisanym (np. przy nagłym zamknięciu
    aplikacji albo błędzie dysku w trakcie zapisu).
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(path)
    except OSError as exc:
        raise ConfigError(f"Nie udało się zapisać pliku {path}: {exc}") from exc
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass