@echo off
setlocal enabledelayedexpansion
REM Budowanie SecureVisioMonitor.exe
REM
REM Wymaga jednorazowo: pip install pyinstaller
REM Wynik: dist\SecureVisioMonitor.exe

cd /d "%~dp0"
set "EXE=dist\SecureVisioMonitor.exe"

echo Zamykanie dzialajacych instancji...
taskkill /F /IM SecureVisioMonitor.exe >nul 2>&1
if not errorlevel 1 (
    echo   Zamknieto dzialajaca aplikacje.
    REM Chwila na zwolnienie blokady pliku przez system.
    timeout /t 2 /nobreak >nul
)

echo Sprawdzanie PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller nie jest zainstalowany.
    echo Instaluje...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo BLAD: nie udalo sie zainstalowac PyInstaller.
        pause
        exit /b 1
    )
)

REM Zapamietanie nazwy pliku ikony do pozniejszego skopiowania.
set "ICON="
for %%f in (*.ico) do (
    if not defined ICON set "ICON=%%f"
)
if defined ICON (
    echo Znaleziono ikone: !ICON!
) else (
    echo Brak pliku .ico - zostanie uzyta ikona domyslna.
)

REM Usuniecie poprzedniego wyniku, zeby sprawdzenie ponizej bylo wiarygodne.
if exist "%EXE%" del /F /Q "%EXE%" >nul 2>&1

echo.
echo Budowanie aplikacji...
python -m PyInstaller SecureVisioMonitor.spec --noconfirm --clean

REM O powodzeniu decyduje istnienie pliku wynikowego, a nie kod wyjscia.
REM PyInstaller potrafi zglosic niezerowy kod mimo poprawnego zbudowania
REM (np. przy ostrzezeniu o nieznalezionym imporcie), co wczesniej powodowalo
REM przerwanie skryptu przed skopiowaniem ikony.
if not exist "%EXE%" (
    echo.
    echo BLAD: nie powstal plik %EXE%
    echo.
    echo Najczestsze przyczyny:
    echo   - aplikacja nadal dziala ^(sprawdz Menedzer zadan^)
    echo   - antywirus blokuje zapis do katalogu dist
    echo   - plik dist\SecureVisioMonitor.exe jest otwarty w innym programie
    echo.
    pause
    exit /b 1
)

REM Kopiowanie pliku ikony obok gotowego .exe. Ikona "wypalona" w samym .exe
REM (Eksplorator, skroty) dziala niezaleznie od tego kroku, ale zywa ikona
REM okna w czasie dzialania jest wyszukiwana jako luzny plik .ico lezacy
REM obok programu - bez tej kopii okno pokazuje ikone domyslna.
if defined ICON (
    copy /Y "!ICON!" "dist\!ICON!" >nul
    if exist "dist\!ICON!" (
        echo Skopiowano ikone do dist\!ICON!
    ) else (
        echo UWAGA: nie udalo sie skopiowac ikony do dist\
    )
)

echo.
echo ==========================================
echo Gotowe: %EXE%
echo ==========================================
echo.
echo Plik settings.json oraz katalog sounds\ zostana utworzone obok .exe
echo przy pierwszym uruchomieniu.
echo.
pause