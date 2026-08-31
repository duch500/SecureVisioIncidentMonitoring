"""Metadane aplikacji.

Jedno miejsce na nazwę, autora i identyfikator używany przez Windows.
Wartości stąd trafiają do okna "O programie", do rejestracji powiadomień
systemowych oraz do tytułu okna głównego.
"""

from __future__ import annotations

APP_NAME = "SecureVisio Monitor"
APP_AUTHOR = "Maciej Adamiok"
# Autor logo/ikony aplikacji. Pusty string ukrywa tę pozycję w oknie
# "O programie" - wpisz nazwisko, gdy logo pochodzi od innej osoby.
APP_LOGO_AUTHOR = "Dawid Zelinka"
# Kontakt pokazywany przy blokadzie wersji demonstracyjnej i w oknie
# "O programie". Pusty string ukrywa tę pozycję.
APP_CONTACT = "Pisz na TEAMS"
APP_VERSION = "1.2"

# Oznaczenie wersji demonstracyjnej - widoczne w tytule okna i w oknie
# "O programie". Ustaw na False dla wersji bez ograniczeń czasowych.
IS_DEMO = True
DEMO_PERIOD_DAYS = 7

LICENSE_TEXT = (
    "Wersja demonstracyjna, udostępniona wyłącznie do celów testowych.\n\n"
    "Program stanowi własność autora. Bez jego pisemnej zgody zabronione jest:\n"
    "kopiowanie i rozpowszechnianie programu, modyfikowanie go, dekompilacja "
    "oraz odtwarzanie kodu źródłowego, a także omijanie zabezpieczeń "
    "ograniczających okres używania.\n\n"
    "Korzystanie z programu oznacza akceptację powyższych warunków."
)
APP_DESCRIPTION = (
    "Monitorowanie wielu środowisk SecureVisio i wykrywanie nowych zdarzeń "
    "przez Windows UI Automation."
)

# Identyfikator aplikacji dla Windows (AppUserModelID). Windows używa go
# do powiązania powiadomień z aplikacją i wyświetlenia jej nazwy na toaście.
# Format zalecany przez Microsoft: Firma.Produkt.Komponent.Wersja
APP_ID = "MaciejAdamiok.SecureVisioMonitor.Monitor.1"