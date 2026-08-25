@echo off
REM Szybkie uruchomienie SecureVisio Monitor.
REM Zamknij okno konsoli - aplikacja dziala dalej w tle.

cd /d "%~dp0"
start "" pythonw app.py