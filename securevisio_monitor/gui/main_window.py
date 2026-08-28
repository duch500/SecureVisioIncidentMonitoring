"""Główne okno aplikacji.

Priorytetem jest czytelność stanu monitorowania: na pierwszy rzut oka musi być
widoczne, które środowiska są sprawdzane, kiedy ostatnio się to udało i czy
gdzieś czeka nowe zdarzenie.

Okno spina worker (wątek monitorujący) z warstwą alarmu. Widgety Qt wolno
tworzyć wyłącznie w wątku głównym, dlatego alarm jest pokazywany tutaj,
w odpowiedzi na sygnały workera, a nie w samym workerze.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..about import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_LOGO_AUTHOR,
    APP_NAME,
    APP_VERSION,
)
from ..alert_manager import AlertManager
from ..config import (
    ALARM_MODE_FULLSCREEN,
    ALARM_MODE_TOAST,
    AppSettings,
    ConfigError,
    save_settings,
)
from ..icon import find_icon
from ..logging_setup import set_debug_mode
from ..notifications import ToastNotifier
from ..sound import (
    SOUNDS_DIR,
    AlarmSound,
    ensure_default_sound,
    import_sound,
    list_available_sounds,
)
from ..window_resolver import (
    ClientResolver,
    find_window_for_client,
    get_window_rect,
    maximize_and_focus,
)
from ..worker import ClientStatus, MonitorWorker
from .overlays import AlarmOverlay

logger = logging.getLogger(__name__)

# Log w oknie jest podręczny, nie archiwalny - trzymamy ograniczoną liczbę
# linii, żeby długa praca monitora nie zjadała pamięci.
MAX_LOG_LINES = 300

COLUMNS = ["Klient", "Stan", "Ostatni odczyt", "Incydenty", "Czas odczytu", "Uwagi"]

_COLOR_OK = QColor(215, 245, 215)
_COLOR_ALERT = QColor(255, 205, 205)
_COLOR_ERROR = QColor(255, 230, 190)

# Tła komórek są jasne niezależnie od motywu systemu, więc kolor tekstu musi
# być ustawiony jawnie - w trybie ciemnym Windows domyślny biały tekst byłby
# na nich nieczytelny.
_COLOR_TEXT = QColor(25, 25, 25)


class MainWindow(QMainWindow):
    """Okno główne - lista środowisk, ustawienia i log bieżący."""

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._worker: Optional[MonitorWorker] = None

        self._overlay = AlarmOverlay(display_seconds=settings.alarm_display_sec)
        self._alerts = AlertManager(
            display=self._overlay,
            display_seconds=settings.alarm_display_sec,
            repeat_seconds=settings.alarm_repeat_sec,
        )
        self._overlay.acknowledged.connect(self._on_alarm_acknowledged)
        self._overlay.dismissed.connect(self._on_alarm_dismissed)
        self._overlay.show_requested.connect(self._on_show_requested)

        self._sound = AlarmSound()
        ensure_default_sound()

        # Powiadomienia systemowe - alternatywny tryb alarmowania.
        self._toasts = ToastNotifier()
        self._toasts.show_requested.connect(self._on_show_requested)
        self._toasts.acknowledged.connect(self._on_toast_acknowledged)
        self._toasts.main_window_requested.connect(self._bring_to_front)

        # Moment ostatniego powiadomienia - podstawa odliczania przypomnień
        # w trybie powiadomień (w trybie pełnoekranowym robi to AlertManager).
        self._last_toast_at: Optional[float] = None
        self._toast_sound_timer = QTimer(self)
        self._toast_sound_timer.setSingleShot(True)
        self._toast_sound_timer.timeout.connect(self._sound.stop)

        # Odliczanie przypomnień musi działać także wtedy, gdy worker akurat
        # nie zgłasza nowych zdarzeń - stąd niezależny timer.
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setInterval(1000)
        self._reminder_timer.timeout.connect(self._on_reminder_tick)

        self.setWindowTitle("SecureVisio Monitor")

        # Ustawienie ikony bezpośrednio na oknie, niezależnie od
        # QApplication.setWindowIcon() wywoływanego w app.py. Zabezpieczenie
        # na wypadek, gdyby w danej konfiguracji Windows/Qt ikona aplikacji
        # nie przenosiła się automatycznie na pasek tytułu konkretnego okna.
        icon_path = find_icon()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(900, 620)
        self._build_ui()
        self._load_settings_to_ui()

    # --- Budowa interfejsu -------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(self._build_status_group(), stretch=3)
        layout.addWidget(self._build_settings_group())
        layout.addWidget(self._build_log_group(), stretch=2)
        layout.addLayout(self._build_controls())

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("Monitorowane środowiska")
        layout = QVBoxLayout(group)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # Kolumna stanu mieści najdłuższy komunikat ("NOWE ZDARZENIE (n)"),
        # żeby tekst nie łamał się na dwie linie i nie rozpychał wiersza.
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.Stretch)

        layout.addWidget(self.table)

        self.lbl_summary = QLabel("Monitorowanie zatrzymane.")
        layout.addWidget(self.lbl_summary)

        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("Ustawienia")
        layout = QVBoxLayout(group)

        base_row = QHBoxLayout()
        base_row.addWidget(QLabel("Katalog środowisk:"))
        self.txt_base_dir = QLineEdit()
        self.txt_base_dir.setPlaceholderText(
            r"np. C:\Users\...\Desktop\SecureVisio  (nazwa klienta = podkatalog)"
        )
        base_row.addWidget(self.txt_base_dir)
        layout.addLayout(base_row)

        phrases_row = QHBoxLayout()
        phrases_row.addWidget(QLabel("Frazy nowego zdarzenia:"))
        self.txt_phrases = QLineEdit()
        self.txt_phrases.setPlaceholderText("oddzielone średnikiem")
        phrases_row.addWidget(self.txt_phrases)
        layout.addLayout(phrases_row)

        numbers_row = QHBoxLayout()

        numbers_row.addWidget(QLabel("Interwał (s):"))
        self.sb_interval = QSpinBox()
        self.sb_interval.setRange(2, 3600)
        numbers_row.addWidget(self.sb_interval)

        numbers_row.addSpacing(20)
        numbers_row.addWidget(QLabel("Alarm widoczny (s):"))
        self.sb_display = QSpinBox()
        self.sb_display.setRange(1, 300)
        numbers_row.addWidget(self.sb_display)

        numbers_row.addSpacing(20)
        numbers_row.addWidget(QLabel("Przypomnienie po (s):"))
        self.sb_repeat = QSpinBox()
        self.sb_repeat.setRange(5, 3600)
        numbers_row.addWidget(self.sb_repeat)

        numbers_row.addStretch()
        layout.addLayout(numbers_row)

        flags_row = QHBoxLayout()
        self.chk_first_scan = QCheckBox("Alarmuj o zdarzeniach zastanych przy starcie")
        flags_row.addWidget(self.chk_first_scan)

        self.chk_debug = QCheckBox("Tryb diagnostyczny (szczegółowe logi)")
        self.chk_debug.toggled.connect(set_debug_mode)
        flags_row.addWidget(self.chk_debug)

        flags_row.addStretch()
        layout.addLayout(flags_row)

        layout.addLayout(self._build_alarm_mode_row())
        layout.addLayout(self._build_sound_row())

        return group

    def _build_alarm_mode_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Sposób alarmowania:"))

        self.cb_alarm_mode = QComboBox()
        self.cb_alarm_mode.addItem("Pełny ekran (wszystkie monitory)", ALARM_MODE_FULLSCREEN)
        self.cb_alarm_mode.addItem("Powiadomienia Windows (róg ekranu)", ALARM_MODE_TOAST)
        self.cb_alarm_mode.setMinimumWidth(280)
        self.cb_alarm_mode.currentIndexChanged.connect(self._on_alarm_mode_changed)
        row.addWidget(self.cb_alarm_mode)

        self.lbl_alarm_mode_note = QLabel("")
        row.addWidget(self.lbl_alarm_mode_note)

        row.addStretch()

        self.btn_about = QPushButton("O programie")
        self.btn_about.clicked.connect(self._on_about)
        row.addWidget(self.btn_about)

        return row

    def _build_sound_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.chk_sound = QCheckBox("Dźwięk alarmu:")
        row.addWidget(self.chk_sound)

        self.cb_sound = QComboBox()
        self.cb_sound.setMinimumWidth(220)
        row.addWidget(self.cb_sound)

        self.btn_add_sound = QPushButton("Dodaj plik...")
        self.btn_add_sound.clicked.connect(self._on_add_sound)
        row.addWidget(self.btn_add_sound)

        self.btn_test_sound = QPushButton("Odtwórz")
        self.btn_test_sound.setCheckable(True)
        self.btn_test_sound.toggled.connect(self._on_test_sound)
        row.addWidget(self.btn_test_sound)

        row.addSpacing(16)
        row.addWidget(QLabel("Głośność:"))
        self.sl_volume = QSlider(Qt.Horizontal)
        self.sl_volume.setRange(0, 100)
        self.sl_volume.setFixedWidth(120)
        self.sl_volume.valueChanged.connect(self._on_volume_changed)
        row.addWidget(self.sl_volume)

        self.lbl_volume = QLabel("80%")
        self.lbl_volume.setFixedWidth(40)
        row.addWidget(self.lbl_volume)

        row.addStretch()
        return row

    def _refresh_sound_list(self) -> None:
        """Odświeża listę dostępnych dźwięków z katalogu sounds/."""
        current = self.cb_sound.currentData()
        self.cb_sound.clear()

        for path in list_available_sounds():
            self.cb_sound.addItem(path.stem, path.name)

        if current:
            index = self.cb_sound.findData(current)
            if index >= 0:
                self.cb_sound.setCurrentIndex(index)

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Log bieżący")
        layout = QVBoxLayout(group)

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(MAX_LOG_LINES)
        layout.addWidget(self.txt_log)

        return group

    def _build_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.start_monitoring)
        row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_monitoring)
        row.addWidget(self.btn_stop)

        self.btn_check = QPushButton("Sprawdź teraz")
        self.btn_check.setEnabled(False)
        self.btn_check.clicked.connect(self._on_check_now)
        row.addWidget(self.btn_check)

        row.addStretch()

        self.btn_test_alarm = QPushButton("Testuj alarm")
        self.btn_test_alarm.clicked.connect(self._on_test_alarm)
        row.addWidget(self.btn_test_alarm)

        return row

    # --- Ustawienia --------------------------------------------------------

    def _load_settings_to_ui(self) -> None:
        s = self._settings
        self.txt_base_dir.setText(s.base_dir)
        self.txt_phrases.setText("; ".join(s.default_phrases))
        self.sb_interval.setValue(s.interval_sec)
        self.sb_display.setValue(s.alarm_display_sec)
        self.sb_repeat.setValue(s.alarm_repeat_sec)
        self.chk_first_scan.setChecked(s.alert_on_first_scan)

        mode_index = self.cb_alarm_mode.findData(s.alarm_mode)
        if mode_index >= 0:
            self.cb_alarm_mode.setCurrentIndex(mode_index)
        self._update_alarm_mode_note()

        self.chk_sound.setChecked(s.sound_enabled)
        self._refresh_sound_list()
        if s.sound_file:
            index = self.cb_sound.findData(s.sound_file)
            if index >= 0:
                self.cb_sound.setCurrentIndex(index)
        self.sl_volume.setValue(s.sound_volume)
        self._sound.set_volume(s.sound_volume / 100)

        if not self._sound.supports_volume:
            self.sl_volume.setEnabled(False)
            self.lbl_volume.setText("sys.")

    def _apply_ui_to_settings(self) -> bool:
        """Przenosi wartości z formularza do ustawień. Zwraca False przy błędzie."""
        phrases = tuple(
            p.strip() for p in self.txt_phrases.text().split(";") if p.strip()
        )

        if not phrases:
            QMessageBox.warning(
                self,
                "Brak fraz",
                "Podaj przynajmniej jedną frazę oznaczającą nowe zdarzenie.",
            )
            return False

        try:
            self._settings.base_dir = self.txt_base_dir.text().strip()
            self._settings.default_phrases = phrases
            self._settings.interval_sec = self.sb_interval.value()
            self._settings.alarm_display_sec = self.sb_display.value()
            self._settings.alarm_repeat_sec = self.sb_repeat.value()
            self._settings.alert_on_first_scan = self.chk_first_scan.isChecked()
            self._settings.alarm_mode = self.cb_alarm_mode.currentData()
            self._settings.sound_enabled = self.chk_sound.isChecked()
            self._settings.sound_file = self.cb_sound.currentData() or ""
            self._settings.sound_volume = self.sl_volume.value()
        except ConfigError as exc:
            QMessageBox.warning(self, "Nieprawidłowe ustawienia", str(exc))
            return False

        try:
            save_settings(self._settings)
        except ConfigError as exc:
            # Brak zapisu nie blokuje monitorowania - ustawienia zadziałają
            # w tej sesji, tylko nie przetrwają restartu.
            self.log(f"Uwaga: nie udało się zapisać ustawień ({exc}).")

        return True

    # --- Sterowanie monitorowaniem ----------------------------------------

    def start_monitoring(self) -> None:
        if not self._apply_ui_to_settings():
            return

        if not self._settings.base_dir and not self._settings.manual_map():
            QMessageBox.warning(
                self,
                "Brak konfiguracji",
                "Podaj katalog środowisk, żeby aplikacja mogła rozpoznać klientów "
                "po nazwie podkatalogu.",
            )
            return

        self._alerts = AlertManager(
            display=self._overlay,
            display_seconds=self._settings.alarm_display_sec,
            repeat_seconds=self._settings.alarm_repeat_sec,
        )
        self._overlay._display_seconds = self._settings.alarm_display_sec

        self._worker = MonitorWorker(self._settings)
        self._worker.new_alerts.connect(self._on_new_alerts)
        self._worker.clients_lost.connect(self._on_clients_lost)
        self._worker.clients_returned.connect(self._on_clients_returned)
        self._worker.status_updated.connect(self._on_status_updated)
        self._worker.log_message.connect(self.log)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

        self._reminder_timer.start()
        self._set_controls_running(True)

    def stop_monitoring(self) -> None:
        self._reminder_timer.stop()
        self._sound.stop()
        self._toast_sound_timer.stop()
        self._toasts.clear_all()
        self._last_toast_at = None
        self._alerts.force_hide()

        if self._worker is not None:
            self._worker.stop()
            # Czekamy z limitem - gdyby odczyt UIA się zawiesił, GUI nie
            # może zawisnąć razem z nim.
            if not self._worker.wait(5000):
                logger.warning("Worker nie zatrzymał się w wyznaczonym czasie.")
                self.log("Uwaga: wątek monitorujący nie odpowiada.")
            self._worker = None

        self._set_controls_running(False)
        self.lbl_summary.setText("Monitorowanie zatrzymane.")

    def _set_controls_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.btn_check.setEnabled(running)
        # Pola ustawień pozostają widoczne i czytelne podczas monitorowania,
        # tylko w trybie tylko-do-odczytu. Wyłączenie ich (setEnabled(False))
        # wyszarza tekst tak, że w trybie ciemnym staje się nieczytelny.
        for field in (self.txt_base_dir, self.txt_phrases):
            field.setReadOnly(running)
        for widget in (self.sb_interval, self.chk_first_scan, self.cb_alarm_mode):
            widget.setEnabled(not running)

    def _on_worker_finished(self) -> None:
        self._set_controls_running(False)

    def _on_check_now(self) -> None:
        if self._worker is not None:
            self._worker.check_now()
            self.log("Wymuszono sprawdzenie.")

    # --- Dźwięk ------------------------------------------------------------

    def _selected_sound_path(self) -> Optional[Path]:
        name = self.cb_sound.currentData()
        if not name:
            return ensure_default_sound()
        path = SOUNDS_DIR / name
        return path if path.exists() else ensure_default_sound()

    def _on_volume_changed(self, value: int) -> None:
        self.lbl_volume.setText(f"{value}%")
        self._sound.set_volume(value / 100)

    def _on_add_sound(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik dźwiękowy", "", "Pliki WAV (*.wav)"
        )
        if not path_str:
            return

        imported = import_sound(Path(path_str))
        if imported is None:
            QMessageBox.warning(
                self,
                "Nie udało się dodać pliku",
                "Plik nie został skopiowany. Upewnij się, że to poprawny plik .wav.",
            )
            return

        self._refresh_sound_list()
        index = self.cb_sound.findData(imported.name)
        if index >= 0:
            self.cb_sound.setCurrentIndex(index)
        self.log(f"Dodano dźwięk: {imported.name}")

    def _on_test_sound(self, playing: bool) -> None:
        if playing:
            self._sound.play(self._selected_sound_path())
            self.btn_test_sound.setText("Zatrzymaj")
        else:
            self._sound.stop()
            self.btn_test_sound.setText("Odtwórz")

    def _start_alarm_sound(self) -> None:
        if self.chk_sound.isChecked():
            self._sound.play(self._selected_sound_path())

    # --- Przywracanie okna z poziomu alarmu -------------------------------

    def _on_show_requested(self, client: str) -> None:
        """Maksymalizuje okno wskazanego klienta i ustępuje mu miejsca."""
        resolver = ClientResolver(
            base_dir=self._settings.base_dir or None,
            manual_map=self._settings.manual_map(),
        )

        # Uchwyt sprzed chwili mógł się zdezaktualizować (restart SecureVisio),
        # dlatego szukamy okna ponownie w momencie kliknięcia.
        hwnd = find_window_for_client(client, resolver)
        if hwnd is None:
            self.log(f"Nie znaleziono okna dla {client} - mogło zostać zamknięte.")
            return

        single_entry = self._overlay.entry_count <= 1

        if not maximize_and_focus(hwnd):
            self.log(f"Nie udało się przywrócić okna {client}.")
            return

        self.log(f"Przywrócono środowisko {client}.")

        # W trybie powiadomień nie ma ekranu alarmu, któremu trzeba ustąpić
        # miejsca - potwierdzenie i wyciszenie obsługuje _on_toast_acknowledged,
        # wywoływane równolegle przez ten sam przycisk powiadomienia.
        if self._toast_mode():
            return

        if single_entry:
            # Jedno zdarzenie - alarm znika w całości.
            self._sound.stop()
            self._overlay.hide_alarm(emit_signal=False)
            self._on_alarm_acknowledged()
            return

        # Wiele zdarzeń - alarm ustępuje tylko na monitorze, gdzie wylądowało okno.
        rect = get_window_rect(hwnd)
        if rect is not None:
            left, top, right, bottom = rect
            center = ((left + right) // 2, (top + bottom) // 2)
            self._overlay.close_screen_at(center)

        if not self._overlay.is_visible:
            self._sound.stop()

    # --- Reakcje na sygnały workera ---------------------------------------

    def _on_new_alerts(self, alerts: list) -> None:
        for alert in alerts:
            self.log(
                f"NOWE ZDARZENIE — {alert.client} / {alert.location_label} "
                f"(incydent {alert.incident_id})"
            )

        if self._toast_mode():
            self._show_toast_alerts(alerts)
        else:
            self._alerts.on_new_alerts(alerts)
            self._start_alarm_sound()

    def _toast_mode(self) -> bool:
        """Czy aktywny jest tryb powiadomień systemowych."""
        return self.cb_alarm_mode.currentData() == ALARM_MODE_TOAST

    def _show_toast_alerts(self, alerts: list) -> None:
        """Wyświetla osobne powiadomienie dla każdego zdarzenia."""
        shown = 0
        for alert in alerts:
            if self._toasts.show_event(
                alert.client, alert.location_label, alert.incident_id
            ):
                shown += 1

        if shown == 0 and alerts:
            # Powiadomienia zawiodły - lepiej pokazać alarm pełnoekranowy
            # niż nie zaalarmować wcale.
            self.log("Powiadomienia niedostępne — używam alarmu pełnoekranowego.")
            self._alerts.on_new_alerts(alerts)
            self._start_alarm_sound()
            return

        self._last_toast_at = time.monotonic()
        self._start_toast_sound()

    def _start_toast_sound(self) -> None:
        """Odtwarza dźwięk przez czas odpowiadający wyświetlaniu alarmu.

        Powiadomienie systemowe chowa się samo, w czasie kontrolowanym przez
        Windows, dlatego dźwięk zatrzymujemy własnym licznikiem - zachowując
        ten sam rytm co w trybie pełnoekranowym.
        """
        if not self.chk_sound.isChecked():
            return
        self._sound.play(self._selected_sound_path())
        self._toast_sound_timer.start(self.sb_display.value() * 1000)

    def _on_toast_acknowledged(self, client: str, incident_id: str) -> None:
        """Potwierdzenie zdarzenia przez kliknięcie w powiadomienie."""
        self._sound.stop()
        self._toast_sound_timer.stop()

        if self._worker is not None and client:
            self._worker.acknowledge_ids(client, [incident_id] if incident_id else None)

        self.log(f"Potwierdzono zdarzenie — {client}"
                 + (f" (incydent {incident_id})" if incident_id else ""))

    def _bring_to_front(self) -> None:
        """Przywraca główne okno programu na wierzch."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_alarm_mode_changed(self) -> None:
        """Przełączenie trybu zamyka to, co aktualnie widoczne."""
        self._sound.stop()
        self._toast_sound_timer.stop()
        self._alerts.force_hide()
        self._last_toast_at = None
        self._update_alarm_mode_note()

    def _update_alarm_mode_note(self) -> None:
        """Ostrzega, gdy wybrano tryb powiadomień bez dostępnego mechanizmu."""
        if self._toast_mode() and not self._toasts.is_available:
            self.lbl_alarm_mode_note.setText("⚠ niedostępne — użyty zostanie pełny ekran")
            self.lbl_alarm_mode_note.setStyleSheet("color: #B06000;")
        else:
            self.lbl_alarm_mode_note.setText("")

    def _on_about(self) -> None:
        credits = [f"<b>Autor:</b> {APP_AUTHOR}"]
        # Pozycja pojawia się tylko, gdy autor logo został podany -
        # pusta wartość nie zostawia w oknie osieroconej etykiety.
        if APP_LOGO_AUTHOR.strip():
            credits.append(f"<b>Autor logo:</b> {APP_LOGO_AUTHOR}")

        QMessageBox.about(
            self,
            f"O programie — {APP_NAME}",
            f"<b>{APP_NAME}</b><br>"
            f"wersja {APP_VERSION}<br><br>"
            f"{APP_DESCRIPTION}<br><br>"
            + "<br>".join(credits),
        )

    def _on_clients_lost(self, labels: list) -> None:
        """Alarm o zamkniętym środowisku - jednorazowy, bez dźwięku."""
        for label in labels:
            self.log(f"ŚRODOWISKO ZAMKNIĘTE — {label}")
        if self._toast_mode():
            shown = sum(1 for label in labels if self._toasts.show_unavailable(label))
            if shown:
                return
            # Powiadomienia zawiodły - pokazujemy alarm pełnoekranowy.

        entries = [("Okno SecureVisio zamknięte", label) for label in labels]
        self._overlay.show_alarm(
            entries, self._settings.alarm_display_sec, unavailable=True
        )

    def _on_clients_returned(self, labels: list) -> None:
        """Powrót środowiska - tylko wpis w logu, bez alarmu."""
        for label in labels:
            self.log(f"Środowisko {label} wróciło - monitorowanie wznowione.")

    def _on_status_updated(self, statuses: list) -> None:
        self._refresh_table(statuses)

    def _on_reminder_tick(self) -> None:
        if self._worker is None:
            return

        if self._toast_mode():
            self._toast_reminder_tick()
        else:
            self._alerts.on_tick(self._worker.active_alerts())

    def _toast_reminder_tick(self) -> None:
        """Ponawia powiadomienia o nieobsłużonych zdarzeniach.

        Windows sam decyduje, kiedy schować powiadomienie, dlatego odstęp
        przypomnień odliczamy od momentu jego wysłania.
        """
        active = self._worker.active_alerts()

        if not active:
            self._last_toast_at = None
            return

        if self._last_toast_at is None:
            self._last_toast_at = time.monotonic()
            return

        if time.monotonic() - self._last_toast_at >= self.sb_repeat.value():
            self.log(f"Przypomnienie o {len(active)} nieobsłużonych zdarzeniach.")
            self._show_toast_alerts(active)

    def _on_alarm_dismissed(self) -> None:
        self._sound.stop()
        self._alerts.on_dismissed()

    def _on_alarm_acknowledged(self) -> None:
        self._sound.stop()
        acknowledged = self._alerts.on_acknowledged()
        if self._worker is not None and acknowledged:
            self._worker.acknowledge(acknowledged)
            self.log(f"Potwierdzono {len(acknowledged)} zdarzenie(a).")

    # --- Prezentacja stanu -------------------------------------------------

    def _refresh_table(self, statuses: list[ClientStatus]) -> None:
        self.table.setRowCount(len(statuses))

        available = 0
        with_events = 0

        for row, status in enumerate(sorted(statuses, key=lambda s: s.label)):
            if status.is_available:
                available += 1
            if status.active_events:
                with_events += 1

            note = status.error
            if not note and status.is_minimized:
                note = "okno zminimalizowane (monitorowanie działa)"

            values = [
                status.label,
                status.state_text,
                status.last_read_text,
                str(status.incident_count) if status.is_available else "-",
                f"{status.last_read_duration:.2f}s" if status.is_available else "-",
                note,
            ]

            if not status.is_available:
                color = _COLOR_ERROR
            elif status.active_events:
                color = _COLOR_ALERT
            else:
                color = _COLOR_OK

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(color)
                item.setForeground(_COLOR_TEXT)
                if col in (1, 2, 3, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        total = len(statuses)
        summary = f"Monitorowane: {available}/{total}"
        if with_events:
            summary += f"  |  środowiska z nowym zdarzeniem: {with_events}"
        summary += f"  |  ostatnie sprawdzenie: {datetime.now():%H:%M:%S}"
        self.lbl_summary.setText(summary)

    def log(self, message: str) -> None:
        self.txt_log.appendPlainText(f"{datetime.now():%H:%M:%S}  {message}")

    # --- Test alarmu -------------------------------------------------------

    def _on_test_alarm(self) -> None:
        """Pokazuje przykładowy alarm - do sprawdzenia widoczności na monitorach."""
        if self._toast_mode() and self._toasts.show_event(
            "PRZYKŁAD", "Mapa logiczna", "000000"
        ):
            self._start_toast_sound()
            return

        self._overlay.show_alarm(
            [("Mapa logiczna", "PRZYKŁAD")], self.sb_display.value()
        )
        self._start_alarm_sound()

    # --- Zamknięcie --------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - API Qt
        self._apply_ui_to_settings()
        self.stop_monitoring()
        self._sound.stop()
        self._overlay.hide_alarm(emit_signal=False)
        event.accept()