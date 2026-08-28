"""Natywne powiadomienia Windows (Toast) jako alternatywa dla alarmu pełnoekranowego.

Powiadomienia wyświetlają się w prawym dolnym rogu ekranu, tak jak powiadomienia
systemowe Windows. Każde zdarzenie generuje osobne powiadomienie - Windows sam
układa je w stos, więc nie ma potrzeby łączenia ich w jedną listę.

Każde powiadomienie o nowym zdarzeniu ma przycisk "Pokaż", który maksymalizuje
odpowiadające mu okno SecureVisio. Kliknięcie w treść powiadomienia oznacza
potwierdzenie zapoznania się ze zdarzeniem.

Wszystkie powiadomienia są oznaczone jako ciche (audio silent) - dźwiękiem
steruje moduł sound.py, żeby uniknąć nakładania się sygnału systemowego
na własny sygnał alarmowy.

OGRANICZENIE: obsługa kliknięć działa wyłącznie, gdy aplikacja jest uruchomiona.
Kliknięcie w powiadomienie z Centrum akcji Windows po zamknięciu programu nie
wywoła żadnej akcji. Jest to świadomy kompromis - pełna obsługa wymagałaby
rejestracji komponentu COM w systemie.
"""

from __future__ import annotations

import ctypes
import logging
import winreg
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from .about import APP_ID, APP_NAME

logger = logging.getLogger(__name__)

# Import Windows Runtime. Pakiety winrt bywają rozbite na moduły w różny
# sposób zależnie od wersji, dlatego próbujemy kolejnych wariantów.
_BACKEND = None
_ToastNotificationManager = None
_ToastNotification = None
_XmlDocument = None

try:
    from winrt.windows.data.xml.dom import XmlDocument as _XmlDocument
    from winrt.windows.ui.notifications import (
        ToastNotification as _ToastNotification,
        ToastNotificationManager as _ToastNotificationManager,
    )

    _BACKEND = "winrt"
except ImportError:
    try:
        from winsdk.windows.data.xml.dom import XmlDocument as _XmlDocument
        from winsdk.windows.ui.notifications import (
            ToastNotification as _ToastNotification,
            ToastNotificationManager as _ToastNotificationManager,
        )

        _BACKEND = "winsdk"
    except ImportError:
        logger.debug(
            "Brak bibliotek Windows Runtime - powiadomienia systemowe niedostępne."
        )

NOTIFICATIONS_AVAILABLE = _BACKEND is not None

# Separator w identyfikatorze akcji. Znak nie występuje w nazwach klientów
# ani w identyfikatorach incydentów.
_SEP = "|"

# Rodzaje akcji przekazywane w argumentach powiadomienia.
ACTION_ACKNOWLEDGE = "ack"
ACTION_SHOW = "show"
ACTION_MAIN_WINDOW = "main"


def register_app_id(icon_path: Optional[Path] = None) -> bool:
    """Rejestruje aplikację w Windows, żeby powiadomienia miały poprawną nazwę.

    Zapis odbywa się w gałęzi bieżącego użytkownika (HKEY_CURRENT_USER), więc
    nie wymaga uprawnień administratora. Rejestracja jest nadpisywana przy
    każdym starcie - to najprostszy sposób na utrzymanie aktualnej ścieżki
    do ikony, gdy aplikacja zostanie przeniesiona.

    Args:
        icon_path: Ścieżka do pliku ikony pokazywanej na powiadomieniu.

    Returns:
        True, jeśli rejestracja się powiodła.
    """
    try:
        # Powiązanie bieżącego procesu z identyfikatorem aplikacji. Bez tego
        # Windows przypisuje powiadomienia do procesu nadrzędnego (np. python.exe).
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nie udało się ustawić identyfikatora procesu: %s", exc)

    key_path = rf"Software\Classes\AppUserModelId\{APP_ID}"
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            if icon_path is not None and icon_path.exists():
                winreg.SetValueEx(
                    key, "IconUri", 0, winreg.REG_SZ, str(icon_path.resolve())
                )
            # Wyłączenie grupowania powiadomień tej aplikacji w Centrum akcji
            # jako jednej pozycji - każde zdarzenie ma pozostać widoczne osobno.
            winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, 1)

        logger.debug("Zarejestrowano aplikację w Windows jako '%s'.", APP_NAME)
        return True

    except OSError as exc:
        logger.warning("Nie udało się zarejestrować aplikacji w rejestrze: %s", exc)
        return False


def _escape(text: str) -> str:
    """Zabezpiecza tekst przed uszkodzeniem struktury XML powiadomienia."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class ToastNotifier(QObject):
    """Wyświetla natywne powiadomienia Windows i obsługuje kliknięcia.

    Sygnały emitowane są w wątku, w którym Windows zgłasza aktywację
    powiadomienia. Połączenie sygnału z Qt zapewnia przekazanie obsługi
    do wątku głównego, gdzie wolno operować na widgetach.

    Sygnały:
        acknowledged: Kliknięto w treść powiadomienia. Argumenty: klient, Id incydentu.
        show_requested: Kliknięto przycisk "Pokaż". Argument: etykieta klienta.
        main_window_requested: Kliknięto powiadomienie o zamkniętym środowisku.
    """

    acknowledged = Signal(str, str)
    show_requested = Signal(str)
    main_window_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._notifier = None
        # Wyświetlone powiadomienia trzeba utrzymywać przy życiu - inaczej
        # mechanizm odśmiecania Pythona usunie obiekt razem z podpiętą obsługą
        # kliknięcia, zanim użytkownik zdąży zareagować.
        self._active: list = []

        if not NOTIFICATIONS_AVAILABLE:
            logger.warning(
                "Powiadomienia systemowe niedostępne - brak bibliotek Windows Runtime."
            )
            return

        self._notifier = self._create_notifier()

    @staticmethod
    def _create_notifier():
        """Tworzy mechanizm powiadomień, próbując kolejnych wariantów API.

        Projekcja Windows Runtime dla Pythona rozbija warianty tej samej metody
        na osobne nazwy, a nazewnictwo różni się między wersjami bibliotek.
        Zamiast zakładać jedną, próbujemy kolejno tych, które występują
        w praktyce.
        """
        attempts = (
            ("create_toast_notifier_with_id", (APP_ID,)),
            ("create_toast_notifier", (APP_ID,)),
            ("createToastNotifierWithId", (APP_ID,)),
            ("create_toast_notifier", ()),
        )

        errors: list[str] = []

        for method_name, args in attempts:
            method = getattr(_ToastNotificationManager, method_name, None)
            if method is None:
                continue
            try:
                notifier = method(*args)
                logger.debug(
                    "Utworzono mechanizm powiadomień: %s(%d arg.)",
                    method_name, len(args),
                )
                return notifier
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{method_name}({len(args)} arg.): {exc}")

        logger.error(
            "Nie udało się utworzyć mechanizmu powiadomień. Próby: %s",
            "; ".join(errors) or "brak pasujących metod",
        )
        logger.error(
            "Dostępne metody ToastNotificationManager: %s",
            ", ".join(n for n in dir(_ToastNotificationManager) if not n.startswith("_")),
        )
        return None

    @property
    def is_available(self) -> bool:
        return self._notifier is not None

    def show_event(self, client: str, location: str, incident_id: str) -> bool:
        """Wyświetla powiadomienie o nowym zdarzeniu, z przyciskiem "Pokaż".

        Args:
            client: Etykieta klienta (np. "Klient A").
            location: Opis lokalizacji (mapa sieci albo numer incydentu).
            incident_id: Identyfikator incydentu - przekazywany do potwierdzenia.

        Returns:
            True, jeśli powiadomienie zostało wyświetlone.
        """
        ack_arg = _SEP.join((ACTION_ACKNOWLEDGE, client, incident_id))
        show_arg = _SEP.join((ACTION_SHOW, client, incident_id))

        xml = f"""<toast launch="{_escape(ack_arg)}" scenario="reminder">
    <visual>
        <binding template="ToastGeneric">
            <text>NOWE ZDARZENIE</text>
            <text>{_escape(client)}</text>
            <text>{_escape(location)}</text>
        </binding>
    </visual>
    <actions>
        <action content="Pokaż" arguments="{_escape(show_arg)}" activationType="foreground"/>
        <action content="Potwierdź" arguments="{_escape(ack_arg)}" activationType="foreground"/>
    </actions>
    <audio silent="true"/>
</toast>"""

        return self._show(xml, f"zdarzenie {client}/{incident_id}")

    def show_unavailable(self, client: str) -> bool:
        """Wyświetla powiadomienie o zamkniętym środowisku.

        Bez przycisku "Pokaż" - nie ma okna, które można by pokazać.
        Kliknięcie przywraca główne okno programu.
        """
        arg = _SEP.join((ACTION_MAIN_WINDOW, client, ""))

        xml = f"""<toast launch="{_escape(arg)}">
    <visual>
        <binding template="ToastGeneric">
            <text>ŚRODOWISKO ZAMKNIĘTE</text>
            <text>{_escape(client)}</text>
            <text>Okno SecureVisio nie jest już dostępne.</text>
        </binding>
    </visual>
    <audio silent="true"/>
</toast>"""

        return self._show(xml, f"zamknięcie {client}")

    def show_connection_error(self, client: str) -> bool:
        """Wyświetla powiadomienie o zerwanym połączeniu.

        Zawiera przycisk "Pokaż", ponieważ w oknie SecureVisio czeka decyzja
        operatora (ponowienie próby albo zamknięcie aplikacji).
        """
        ack_arg = _SEP.join((ACTION_ACKNOWLEDGE, client, ""))
        show_arg = _SEP.join((ACTION_SHOW, client, ""))

        xml = f"""<toast launch="{_escape(ack_arg)}">
    <visual>
        <binding template="ToastGeneric">
            <text>ZERWANE POŁĄCZENIE</text>
            <text>{_escape(client)}</text>
            <text>SecureVisio utracił połączenie z serwerem. Dane mogą być nieaktualne.</text>
        </binding>
    </visual>
    <actions>
        <action content="Pokaż" arguments="{_escape(show_arg)}" activationType="foreground"/>
    </actions>
    <audio silent="true"/>
</toast>"""

        return self._show(xml, f"zerwane połączenie {client}")

    def _show(self, xml: str, description: str) -> bool:
        if not self.is_available:
            logger.debug("Pominięto powiadomienie (%s) - mechanizm niedostępny.", description)
            return False

        try:
            document = _XmlDocument()
            # load_xml w zależności od wersji biblioteki bywa też loadXml.
            loader = getattr(document, "load_xml", None) or getattr(document, "loadXml")
            loader(xml)

            toast = _ToastNotification(document)

            # Nazwy metod rejestrujących obsługę zdarzeń również się różnią.
            self._connect(toast, ("add_activated", "addActivated"), self._on_activated)
            self._connect(
                toast, ("add_dismissed", "addDismissed"),
                lambda sender, args: self._forget(sender),
            )
            self._connect(
                toast, ("add_failed", "addFailed"),
                lambda sender, args: self._forget(sender),
            )

            self._active.append(toast)
            self._notifier.show(toast)

            logger.debug("Wyświetlono powiadomienie: %s", description)
            return True

        except Exception as exc:  # noqa: BLE001
            # Brak powiadomienia nie może zatrzymać monitorowania.
            logger.warning("Nie udało się wyświetlić powiadomienia (%s): %s", description, exc)
            return False

    @staticmethod
    def _connect(toast, method_names: tuple[str, ...], handler) -> None:
        """Podpina obsługę zdarzenia, próbując kolejnych nazw metod."""
        for name in method_names:
            method = getattr(toast, name, None)
            if method is not None:
                try:
                    method(handler)
                    return
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Nie udało się podpiąć %s: %s", name, exc)
        logger.debug("Nie znaleziono metody do podpięcia: %s", method_names[0])

    def _on_activated(self, sender, args) -> None:
        """Obsługa kliknięcia w powiadomienie lub jego przycisk.

        Wywoływane przez Windows w wątku innym niż główny - dalsza obsługa
        odbywa się przez sygnały Qt, które przekazują ją do wątku GUI.
        """
        try:
            arguments = self._extract_arguments(args)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nie udało się odczytać akcji powiadomienia: %s", exc)
            self._forget(sender)
            return

        self._forget(sender)

        if not arguments:
            return

        parts = arguments.split(_SEP)
        action = parts[0] if parts else ""
        client = parts[1] if len(parts) > 1 else ""
        incident_id = parts[2] if len(parts) > 2 else ""

        if action == ACTION_SHOW and client:
            self.show_requested.emit(client)
            self.acknowledged.emit(client, incident_id)
        elif action == ACTION_ACKNOWLEDGE and client:
            self.acknowledged.emit(client, incident_id)
        elif action == ACTION_MAIN_WINDOW:
            self.main_window_requested.emit()

    @staticmethod
    def _extract_arguments(args) -> str:
        """Wyciąga treść akcji z argumentów zdarzenia aktywacji."""
        # Zależnie od wersji biblioteki argumenty są dostępne wprost albo
        # wymagają rzutowania na typ zdarzenia aktywacji.
        arguments = getattr(args, "arguments", None)
        if arguments:
            return str(arguments)

        try:
            from winrt.windows.ui.notifications import ToastActivatedEventArgs
        except ImportError:
            try:
                from winsdk.windows.ui.notifications import ToastActivatedEventArgs
            except ImportError:
                return ""

        try:
            activated = ToastActivatedEventArgs._from(args)
            return str(activated.arguments or "")
        except Exception:  # noqa: BLE001
            return ""

    def _forget(self, toast) -> None:
        """Zwalnia powiadomienie, którego obsługa się zakończyła."""
        try:
            self._active.remove(toast)
        except ValueError:
            pass

    def clear_all(self) -> None:
        """Zwalnia wszystkie utrzymywane powiadomienia.

        Nie usuwa ich z ekranu ani z Centrum akcji - tym zarządza Windows.
        """
        self._active.clear()