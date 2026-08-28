"""Metadane aplikacji.

Jedno miejsce na nazwę, autora i identyfikator używany przez Windows.
Wartości stąd trafiają do okna "O programie", do rejestracji powiadomień
systemowych oraz do tytułu okna głównego.
"""

from __future__ import annotations

APP_NAME = "SecureVisio Monitor"
APP_AUTHOR = "Maciej Adamiok"
APP_LOGO_AUTHOR = "Dawid Zelinka"
APP_VERSION = "1.1"
APP_DESCRIPTION = (
    "Monitorowanie wielu środowisk SecureVisio i wykrywanie nowych zdarzeń "
    "przez Windows UI Automation."
)

# Identyfikator aplikacji dla Windows (AppUserModelID). Windows używa go
# do powiązania powiadomień z aplikacją i wyświetlenia jej nazwy na toaście.
# Format zalecany przez Microsoft: Firma.Produkt.Komponent.Wersja
APP_ID = "MaciejAdamiok.SecureVisioMonitor.Monitor.1"