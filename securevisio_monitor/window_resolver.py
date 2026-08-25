"""Wykrywanie okien SecureVisio i przypisywanie ich do klientów.

Wszystkie instancje SecureVisio mają identyczną nazwę procesu (SecureVisio.exe)
i identyczny tytuł okna (SecureVisio). Jedyną trwałą cechą odróżniającą klientów
jest ścieżka pliku wykonywalnego - stabilna między restartami, w przeciwieństwie
do PID i HWND.

Klient rozpoznawany jest według kolejności strategii (pierwsza pasująca wygrywa):
1. Ręczne przypisanie: pełna ścieżka .exe -> etykieta (z konfiguracji).
2. Wzorzec ścieżki: pierwszy katalog pod katalogiem bazowym.
3. Brak dopasowania: okno oznaczone jako nierozpoznane, bez zgadywania.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Optional

try:
    import win32api
    import win32con
    import win32gui
    import win32process
except ImportError as exc:  # pragma: no cover - zależność środowiskowa
    raise ImportError(
        "Brak biblioteki 'pywin32'. Zainstaluj: pip install pywin32"
    ) from exc

logger = logging.getLogger(__name__)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Cechy pozwalające odróżnić prawdziwe okno SecureVisio od okien, które tylko
# przypadkiem mają "securevisio" w tytule (np. edytor kodu z otwartym plikiem).
_EXE_NAME = "securevisio.exe"
_WINDOW_TITLE = "securevisio"


@dataclass(frozen=True)
class WindowInfo:
    """Surowe informacje o wykrytym oknie SecureVisio."""

    hwnd: int
    pid: int
    title: str
    exe_path: str


@dataclass(frozen=True)
class ResolvedWindow:
    """Okno SecureVisio z przypisanym (lub nie) klientem.

    Attributes:
        window: Surowe informacje o oknie.
        client_label: Nazwa klienta do wyświetlenia, albo None gdy nierozpoznany.
        is_recognized: Czy udało się jednoznacznie przypisać klienta.
        source: Skąd pochodzi etykieta ("manual", "pattern") - do diagnostyki.
    """

    window: WindowInfo
    client_label: Optional[str]
    is_recognized: bool
    source: str = ""

    @property
    def display_name(self) -> str:
        """Nazwa do pokazania w GUI/alarmie - etykieta albo oznaczenie nierozpoznanego."""
        if self.client_label:
            return self.client_label
        return f"(nierozpoznany: {self.window.exe_path})"


def enumerate_securevisio_windows() -> list[WindowInfo]:
    """Zwraca listę wszystkich aktualnie otwartych okien SecureVisio.

    Filtruje po nazwie pliku wykonywalnego (securevisio.exe), a nie tylko po
    tytule okna - to eliminuje fałszywe trafienia z innych aplikacji.
    """
    windows: list[WindowInfo] = []

    def callback(hwnd: int, _) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd)
        if not title or _WINDOW_TITLE not in title.lower():
            return True

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:  # noqa: BLE001
            return True

        exe_path = _get_process_path(pid)
        if not exe_path or not exe_path.lower().endswith(_EXE_NAME):
            return True

        windows.append(WindowInfo(hwnd=hwnd, pid=pid, title=title, exe_path=exe_path))
        return True

    win32gui.EnumWindows(callback, None)
    logger.debug("Wykryto %d okien SecureVisio.", len(windows))
    return windows


def _get_process_path(pid: int) -> Optional[str]:
    """Zwraca ścieżkę pliku wykonywalnego procesu o podanym PID, albo None."""
    handle = None
    try:
        handle = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        return win32process.GetModuleFileNameEx(handle, 0)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Nie udało się odczytać ścieżki procesu PID=%d: %s", pid, exc)
        return None
    finally:
        if handle is not None:
            try:
                win32api.CloseHandle(handle)
            except Exception:  # noqa: BLE001
                pass


def is_window_minimized(hwnd: int) -> bool:
    """Sprawdza, czy okno jest zminimalizowane.

    Odczyt danych działa również dla zminimalizowanego okna, ale ta informacja
    przydaje się w GUI (np. do oznaczenia stanu instancji).
    """
    try:
        return bool(win32gui.IsIconic(hwnd))
    except Exception:  # noqa: BLE001
        return False


def maximize_and_focus(hwnd: int) -> bool:
    """Maksymalizuje okno i wysuwa je na pierwszy plan.

    Wywoływane wyłącznie w bezpośredniej reakcji na kliknięcie użytkownika.
    Windows blokuje wymuszanie pierwszego planu przez aplikacje działające
    w tle, ale zezwala na to tuż po interakcji użytkownika - dlatego samo
    monitorowanie nigdy nie aktywuje okien, a ta funkcja działa niezawodnie.

    Returns:
        True, jeśli operacja się powiodła.
    """
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nie udało się zmaksymalizować okna %d: %s", hwnd, exc)
        return False

    # SetForegroundWindow bywa odrzucane przez system w zależności od tego,
    # które okno ma aktualnie fokus. Samo zmaksymalizowanie już zadziałało,
    # więc niepowodzenie tego kroku nie jest traktowane jako błąd.
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as exc:  # noqa: BLE001
        logger.debug("SetForegroundWindow odrzucone dla %d: %s", hwnd, exc)

    return True


def get_window_rect(hwnd: int) -> Optional[tuple[int, int, int, int]]:
    """Zwraca prostokąt okna (left, top, right, bottom) albo None.

    Używane do ustalenia, na którym monitorze okno faktycznie się znalazło.
    """
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:  # noqa: BLE001
        return None


def find_window_for_client(
    label: str, resolver: "ClientResolver"
) -> Optional[int]:
    """Wyszukuje aktualny HWND okna danego klienta.

    Uchwyt okna zapamiętany w momencie wykrycia zdarzenia mógł się już
    zdezaktualizować (np. użytkownik zrestartował SecureVisio), dlatego przed
    przywróceniem okna wyszukujemy je ponownie.
    """
    for item in resolver.resolve_all():
        if item.is_recognized and item.client_label == label:
            return item.window.hwnd
    return None


class ClientResolver:
    """Przypisuje okna SecureVisio do klientów według skonfigurowanych reguł.

    Args:
        base_dir: Katalog bazowy, pod którym leżą katalogi klientów. Nazwa
            klienta to pierwszy segment ścieżki .exe poniżej tego katalogu.
            Gdy None, strategia wzorca ścieżki jest wyłączona.
        manual_map: Mapa pełna_ścieżka_exe (lowercase) -> etykieta klienta.
            Ma najwyższy priorytet.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        manual_map: Optional[dict[str, str]] = None,
    ) -> None:
        self._base_dir = PureWindowsPath(base_dir) if base_dir else None
        # Klucze normalizujemy do lowercase - ścieżki Windows są nierozróżnialne
        # pod względem wielkości liter.
        self._manual_map = {
            self._normalize(path): label for path, label in (manual_map or {}).items()
        }

    @staticmethod
    def _normalize(path: str) -> str:
        return path.strip().lower()

    def _match_manual(self, exe_path: str) -> Optional[str]:
        return self._manual_map.get(self._normalize(exe_path))

    def _match_pattern(self, exe_path: str) -> Optional[str]:
        """Wyodrębnia nazwę klienta jako pierwszy katalog pod katalogiem bazowym."""
        if self._base_dir is None:
            return None

        path = PureWindowsPath(exe_path)
        base_parts = [p.lower() for p in self._base_dir.parts]
        path_parts = list(path.parts)

        # Znajdź katalog bazowy w ścieżce (case-insensitive).
        lower_parts = [p.lower() for p in path_parts]
        n = len(base_parts)
        for i in range(len(lower_parts) - n):
            if lower_parts[i : i + n] == base_parts:
                client_segment_index = i + n
                if client_segment_index < len(path_parts):
                    return path_parts[client_segment_index]
                return None

        return None

    def resolve(self, window: WindowInfo) -> ResolvedWindow:
        """Przypisuje pojedyncze okno do klienta."""
        label = self._match_manual(window.exe_path)
        if label:
            return ResolvedWindow(window, label, is_recognized=True, source="manual")

        label = self._match_pattern(window.exe_path)
        if label:
            return ResolvedWindow(window, label, is_recognized=True, source="pattern")

        logger.warning(
            "Okno nierozpoznane (brak reguły dla ścieżki): %s", window.exe_path
        )
        return ResolvedWindow(window, None, is_recognized=False)

    def resolve_all(self) -> list[ResolvedWindow]:
        """Wykrywa wszystkie okna SecureVisio i przypisuje je do klientów."""
        return [self.resolve(w) for w in enumerate_securevisio_windows()]