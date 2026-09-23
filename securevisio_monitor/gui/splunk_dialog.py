"""Dialogi GUI do zarządzania środowiskami Splunk.

Dwa poziomy, zgodnie z ustaleniem "chciałbym aby docelowo wpisywanie
środowisk odbywało się poprzez GUI":

- SplunkEnvironmentEditDialog: formularz jednego środowiska (etykieta,
  adres, porty, token, interwał, verify_ssl, enabled). Waliduje przez
  samą konstrukcję SplunkEnvironment (__post_init__ w config.py) - ta sama
  walidacja co przy ręcznej edycji settings.json, więc nie da się tu
  utworzyć niepoprawnego wpisu, który by przeszedł ręczną edycję, ale nie
  przeszedłby przez to okno.
- SplunkEnvironmentsManagerDialog: lista wszystkich środowisk z przyciskami
  Dodaj/Edytuj/Usuń, otwierana z głównego okna. Operuje na własnej,
  roboczej kopii listy - zmiany trafiają do prawdziwej konfiguracji dopiero
  gdy main_window.py odczyta wynik po zamknięciu dialogu.

Token wyświetla się domyślnie ukryty (jak hasło), z przyciskiem
pokaż/ukryj - to samo, świadome podejście co przy dźwiękach i kolorach:
nie chowamy tokenu "na twardo" (decyzja: "na razie w settings")), ale
niepotrzebne trzymanie go czytelnym na ekranie przy zwykłej edycji innego
pola nie ma uzasadnienia.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..config import MIN_SPLUNK_POLL_INTERVAL_SEC, ConfigError, SplunkEnvironment
from ..splunk_client import SplunkClient, SplunkQueryError, decode_token_expiry, fetch_with_retry


# Cooldown testu połączenia - świadomie NA POZIOMIE MODUŁU, nie instancji
# dialogu, bo dialog jest tworzony od nowa przy każdym "Dodaj"/"Edytuj" -
# licznik w samym dialogu resetowałby się przy każdym otwarciu, co nie
# chroniłoby Search Heada przed powtarzanym testowaniem w krótkim odstępie
# (ustalone wprost: cooldown 10 minut). Klucz to (host, port) - to sam
# adres, do którego mierzymy odstęp, nie etykieta (nowe, jeszcze nienazwane
# środowisko też powinno podlegać temu samemu ograniczeniu).
_CONNECTION_TEST_COOLDOWN_SEC = 600
_last_connection_test_at: dict[tuple[str, int], float] = {}


class _ConnectionTestThread(QThread):
    """Wykonuje prawdziwe zapytanie do Splunka w tle, bez blokowania GUI.

    Reużywa SplunkClient/fetch_with_retry - tę samą, przetestowaną ścieżkę,
    którą i tak będzie używał SplunkWorker w produkcji. To nie jest osobna,
    "lżejsza" wersja testu - celowo sprawdza dokładnie to samo (odczyt
    es_notable_events), żeby wynik testu miał realną wartość predykcyjną.
    """

    finished_test = Signal(bool, str)

    def __init__(self, env: SplunkEnvironment) -> None:
        super().__init__()
        self._env = env

    def run(self) -> None:  # noqa: D102 - API QThread
        try:
            incidents = fetch_with_retry(SplunkClient(self._env), max_attempts=2)
        except SplunkQueryError as exc:
            self.finished_test.emit(False, str(exc))
        except Exception as exc:  # noqa: BLE001 - zabezpieczenie przed nieprzewidzianym wyjątkiem w wątku
            self.finished_test.emit(False, f"Nieoczekiwany błąd: {exc}")
        else:
            self.finished_test.emit(
                True, f"Połączenie działa - odczytano {len(incidents)} wierszy z es_notable_events."
            )


class SplunkEnvironmentEditDialog(QDialog):
    """Formularz dodania albo edycji jednego środowiska Splunk.

    Walidacja przebiega przez rzeczywistą konstrukcję SplunkEnvironment -
    ten sam kod, który waliduje wpisy przy ręcznej edycji settings.json, więc
    reguły nigdy nie mogą się rozjechać między dwoma ścieżkami wprowadzania
    danych.
    """

    def __init__(
        self,
        forbidden_labels: set[str],
        initial: Optional[SplunkEnvironment] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Edytuj środowisko Splunk" if initial else "Nowe środowisko Splunk"
        )
        self.setMinimumWidth(420)

        # Własna etykieta (przy edycji) jest wyłączona z zestawu zakazanych -
        # inaczej zapisanie środowiska bez zmiany etykiety zgłaszałoby
        # kolizję samo ze sobą.
        self._forbidden_labels = set(forbidden_labels)
        if initial is not None:
            self._forbidden_labels.discard(initial.label.strip().casefold())
        self._initial = initial
        self._result: Optional[SplunkEnvironment] = None

        form = QFormLayout()

        self.txt_label = QLineEdit(initial.label if initial else "")
        self.txt_label.setPlaceholderText("np. Klient A - Splunk")
        form.addRow("Etykieta:", self.txt_label)

        self.txt_host = QLineEdit(initial.rest_host if initial else "")
        self.txt_host.setPlaceholderText("np. 172.18.41.14")
        form.addRow("Adres Search Heada:", self.txt_host)

        self.sb_rest_port = QSpinBox()
        self.sb_rest_port.setRange(1, 65535)
        self.sb_rest_port.setValue(initial.rest_port if initial else 8089)
        form.addRow("Port REST API:", self.sb_rest_port)

        self.sb_web_port = QSpinBox()
        self.sb_web_port.setRange(1, 65535)
        self.sb_web_port.setValue(initial.web_port if initial else 8000)
        form.addRow("Port Splunk Web (przycisk \"Pokaż\"):", self.sb_web_port)

        token_row = QHBoxLayout()
        self.txt_token = QLineEdit(initial.token if initial else "")
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_token.setPlaceholderText("Authentication Token (Settings → Tokens)")
        token_row.addWidget(self.txt_token)
        self.btn_toggle_token = QPushButton("Pokaż")
        self.btn_toggle_token.setCheckable(True)
        self.btn_toggle_token.setFixedWidth(60)
        self.btn_toggle_token.toggled.connect(self._on_toggle_token)
        token_row.addWidget(self.btn_toggle_token)
        form.addRow("Token:", token_row)

        self.lbl_token_age = QLabel()
        self.lbl_token_age.setWordWrap(True)
        form.addRow("", self.lbl_token_age)
        self.txt_token.textChanged.connect(self._update_token_expiry_label)
        self._update_token_expiry_label()

        self.sb_interval = QSpinBox()
        # Górna granica 10000s (~2h45min) - ustalone wprost: część Search
        # Headów wymaga znacznie dłuższych odstępów niż standardowe 2 min.
        # QSpinBox pozwala też wpisać wartość bezpośrednio z klawiatury, nie
        # tylko strzałkami - istotne przy dużych, precyzyjnych wartościach.
        self.sb_interval.setRange(MIN_SPLUNK_POLL_INTERVAL_SEC, 10000)
        self.sb_interval.setValue(
            initial.poll_interval_sec if initial else MIN_SPLUNK_POLL_INTERVAL_SEC
        )
        form.addRow("Interwał odpytywania (s):", self.sb_interval)

        interval_note = QLabel(
            f"Minimum {MIN_SPLUNK_POLL_INTERVAL_SEC}s. Słabsze środowiska "
            "mogą wymagać znacznie więcej (np. 600s) - ustal to z "
            "administratorem Splunka, nie zgaduj."
        )
        interval_note.setWordWrap(True)
        interval_note.setStyleSheet("color: #777777; font-size: 11px;")
        form.addRow("", interval_note)

        self.chk_verify_ssl = QCheckBox("Weryfikuj certyfikat TLS")
        self.chk_verify_ssl.setChecked(initial.verify_ssl if initial else False)
        form.addRow("", self.chk_verify_ssl)

        self.chk_enabled = QCheckBox("Środowisko aktywne (odpytywane)")
        self.chk_enabled.setChecked(initial.enabled if initial else True)
        form.addRow("", self.chk_enabled)

        test_row = QHBoxLayout()
        self.btn_test_connection = QPushButton("Testuj połączenie")
        self.btn_test_connection.clicked.connect(self._on_test_connection)
        test_row.addWidget(self.btn_test_connection)
        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        test_row.addWidget(self.lbl_test_result, stretch=1)
        form.addRow("", test_row)

        self._test_thread: Optional[_ConnectionTestThread] = None
        self._test_key: Optional[tuple[str, int]] = None

        layout = QVBoxLayout(self)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_token_expiry_label(self) -> None:
        """Pokazuje RZECZYWISTY termin ważności odczytany z samego tokenu (JWT).

        Ustalone wprost: "nie każdy token ma 14 dni ważności" - dlatego nie
        zgadujemy żadnego stałego okresu. Jeśli token jest poprawnym JWT
        z polem "exp", pokazujemy dokładnie to, co on sam o sobie mówi.
        Jeśli nie da się tego odczytać, mówimy to wprost, zamiast pokazywać
        zmyśloną wartość - to jest sedno "jeśli taka informacja jest".

        Odświeża się na żywo w miarę wpisywania/wklejania tokenu (nie tylko
        raz przy otwarciu dialogu), żeby nowo wklejony token był od razu
        widoczny z właściwym terminem, nie z terminem poprzedniego wpisu.
        """
        token = self.txt_token.text().strip()

        if not token:
            self.lbl_token_age.setText("Brak tokenu.")
            self.lbl_token_age.setStyleSheet("color: #777777; font-size: 11px;")
            return

        expiry = decode_token_expiry(token)

        entered_note = ""
        if self._initial is not None and self._initial.token == token and self._initial.token_set_at_iso:
            try:
                set_at = datetime.fromisoformat(self._initial.token_set_at_iso)
                entered_days_ago = (datetime.now() - set_at).days
                entered_note = f" (wpisany {entered_days_ago} dni temu)"
            except ValueError:
                pass

        if expiry is None:
            self.lbl_token_age.setText(
                f"Nie udało się odczytać terminu ważności z tokenu{entered_note}. "
                "Token może nie być formatu JWT, albo nie zawiera informacji "
                "o wygaśnięciu - to nie musi być błąd."
            )
            self.lbl_token_age.setStyleSheet("color: #777777; font-size: 11px;")
            return

        now = datetime.now(expiry.tzinfo)
        remaining = expiry - now
        remaining_days = remaining.days
        expiry_local_text = expiry.astimezone().strftime("%Y-%m-%d %H:%M")

        if remaining.total_seconds() < 0:
            text = f"Token WYGASŁ {expiry_local_text}{entered_note}."
            color = "#B40000"
        elif remaining_days <= 3:
            text = (
                f"Token wygasa {expiry_local_text} - za {remaining_days} dni"
                f"{entered_note}."
            )
            color = "#BE5F00"
        else:
            text = f"Token ważny do {expiry_local_text} (jeszcze {remaining_days} dni){entered_note}."
            color = "#777777"

        self.lbl_token_age.setText(text)
        self.lbl_token_age.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _build_candidate_for_test(self) -> Optional[SplunkEnvironment]:
        """Buduje środowisko z bieżących pól formularza wyłącznie do testu.

        Celowo NIE sprawdza kolizji etykiet (irrelewantne dla samego
        połączenia sieciowego) i pozwala na pustą etykietę (test przed
        nadaniem nazwy nowemu środowisku jest sensownym przypadkiem użycia -
        adres/token/port są tym, co faktycznie determinuje wynik testu).
        """
        try:
            return SplunkEnvironment(
                label=self.txt_label.text().strip() or "(test)",
                rest_host=self.txt_host.text().strip(),
                rest_port=self.sb_rest_port.value(),
                web_port=self.sb_web_port.value(),
                token=self.txt_token.text(),
                verify_ssl=self.chk_verify_ssl.isChecked(),
                poll_interval_sec=self.sb_interval.value(),
                enabled=self.chk_enabled.isChecked(),
            )
        except ConfigError as exc:
            QMessageBox.warning(self, "Nieprawidłowe dane", str(exc))
            return None

    def _on_test_connection(self) -> None:
        """Uruchamia rzeczywisty test połączenia w tle, z cooldownem 10 min.

        Cooldown chroni Search Head przed powtarzanym, ręcznym testowaniem
        w krótkim odstępie (ustalone wprost) - liczony per adres:port, nie
        per etykieta, więc dotyczy też jeszcze nienazwanych, nowych środowisk.
        """
        candidate = self._build_candidate_for_test()
        if candidate is None:
            return

        key = (candidate.rest_host, candidate.rest_port)
        last = _last_connection_test_at.get(key)
        if last is not None:
            remaining = _CONNECTION_TEST_COOLDOWN_SEC - (time.monotonic() - last)
            if remaining > 0:
                minutes_left = int(remaining // 60) + 1
                self.lbl_test_result.setText(
                    f"Poczekaj jeszcze ok. {minutes_left} min przed kolejnym "
                    "testem tego adresu - ograniczenie chroni Search Head "
                    "przed nadmiarem zapytań."
                )
                self.lbl_test_result.setStyleSheet("color: #BE5F00; font-size: 11px;")
                return

        self._test_key = key
        self.btn_test_connection.setEnabled(False)
        self.lbl_test_result.setText("Testowanie...")
        self.lbl_test_result.setStyleSheet("color: #777777; font-size: 11px;")

        self._test_thread = _ConnectionTestThread(candidate)
        self._test_thread.finished_test.connect(self._on_test_finished)
        self._test_thread.start()

    def _on_test_finished(self, success: bool, message: str) -> None:
        # Zapisujemy moment próby NIEZALEŻNIE od wyniku - powtarzane testy
        # nieudanego adresu obciążają Search Head tak samo jak udane.
        if self._test_key is not None:
            _last_connection_test_at[self._test_key] = time.monotonic()

        self.btn_test_connection.setEnabled(True)
        self.lbl_test_result.setText(message)
        self.lbl_test_result.setStyleSheet(
            "color: #2E7D32; font-size: 11px;" if success else "color: #B40000; font-size: 11px;"
        )

    def _wait_for_test_thread(self) -> None:
        """Krótkie, ograniczone oczekiwanie przy zamykaniu okna.

        Ta sama zasada co przy zamykaniu głównego okna programu: nie
        zostawiamy referencji do wciąż działającego QThread na łasce
        odśmiecania Pythona (ryzyko "QThread: Destroyed while thread is
        still running"). Test trwa typowo ~1s, więc 3s to bezpieczny margines
        bez zauważalnego opóźnienia zamykania dialogu w normalnym przypadku.
        """
        if self._test_thread is not None and self._test_thread.isRunning():
            self._test_thread.wait(3000)

    def reject(self) -> None:  # noqa: D102 - API QDialog
        self._wait_for_test_thread()
        super().reject()

    def _on_toggle_token(self, checked: bool) -> None:
        self.txt_token.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.btn_toggle_token.setText("Ukryj" if checked else "Pokaż")

    def _on_accept(self) -> None:
        label = self.txt_label.text().strip()

        if label.casefold() in self._forbidden_labels:
            QMessageBox.warning(
                self,
                "Zduplikowana etykieta",
                f"Etykieta '{label}' jest już użyta przez inne środowisko "
                "(Splunk albo SecureVisio). Etykiety muszą być unikalne.",
            )
            return

        try:
            candidate = SplunkEnvironment(
                label=label,
                rest_host=self.txt_host.text().strip(),
                rest_port=self.sb_rest_port.value(),
                web_port=self.sb_web_port.value(),
                token=self.txt_token.text(),
                verify_ssl=self.chk_verify_ssl.isChecked(),
                poll_interval_sec=self.sb_interval.value(),
                enabled=self.chk_enabled.isChecked(),
            )
        except ConfigError as exc:
            QMessageBox.warning(self, "Nieprawidłowe dane", str(exc))
            return

        if not candidate.token.strip():
            proceed = QMessageBox.question(
                self,
                "Brak tokenu",
                "Nie podano tokenu - to środowisko nie będzie w stanie się "
                "połączyć. Zapisać mimo to?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                # Świadomie NIE ustawiamy self._result tutaj - candidate jest
                # tylko lokalną zmienną. Wcześniejsza wersja przypisywała do
                # self._result przed tym sprawdzeniem, więc odmowa
                # potwierdzenia i tak zostawiała niepotwierdzony obiekt
                # dostępny przez result_environment() po zamknięciu dialogu
                # przyciskiem Cancel - realny błąd znaleziony testem, nie
                # przy ręcznym klikaniu.
                return

        # token_set_at_iso ma odzwierciedlać moment WPISANIA tokenu, nie
        # każdej edycji środowiska - inaczej zmiana samego interwału przy
        # okazji wyzerowałaby znacznik potrzebny do przyszłego ostrzegania
        # o zbliżającym się wygaśnięciu (token ważny 14 dni). Ustawiamy nową
        # wartość tylko, gdy token faktycznie się zmienił względem tego, co
        # było wczytane przy otwarciu dialogu; w przeciwnym razie zachowujemy
        # poprzedni znacznik bez zmian.
        token_changed = self._initial is None or candidate.token != self._initial.token
        if token_changed and candidate.token.strip():
            candidate.token_set_at_iso = datetime.now().isoformat()
        elif self._initial is not None:
            candidate.token_set_at_iso = self._initial.token_set_at_iso

        self._wait_for_test_thread()
        self._result = candidate
        self.accept()

    def result_environment(self) -> Optional[SplunkEnvironment]:
        """Zwraca poprawnie skonstruowane środowisko, jeśli dialog zaakceptowano."""
        return self._result


class SplunkEnvironmentsManagerDialog(QDialog):
    """Lista wszystkich środowisk Splunk z możliwością dodania/edycji/usunięcia.

    Operuje na własnej, roboczej kopii listy - żadna zmiana nie trafia do
    rzeczywistej konfiguracji, dopóki wywołujący (main_window.py) nie
    odczyta environments() po zamknięciu i sam nie zapisze ustawień. Dzięki
    temu zamknięcie tego okna (nawet klawiszem Esc) nigdy nie zostawia
    konfiguracji w połowie zmienionego stanu.
    """

    def __init__(
        self,
        environments: list[SplunkEnvironment],
        other_labels: set[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Środowiska Splunk")
        self.setMinimumSize(560, 360)

        self._environments: list[SplunkEnvironment] = list(environments)
        # Etykiety klientów SecureVisio - środowisko Splunk nie może się
        # nazywać tak samo, bo dzielą jedną, wspólną tabelę i mechanizm
        # alarmowania.
        self._other_labels = {label.casefold() for label in other_labels}

        layout = QVBoxLayout(self)

        info = QLabel(
            "Każde środowisko ma własny adres, token i interwał odpytywania - "
            "różne środowiska mogą wymagać różnej częstotliwości w zależności "
            "od wytrzymałości Search Heada."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555555;")
        layout.addWidget(info)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Etykieta", "Adres", "Interwał (s)", "Aktywne"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemDoubleClicked.connect(lambda _: self._on_edit())
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Dodaj...")
        self.btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self.btn_add)

        self.btn_edit = QPushButton("Edytuj...")
        self.btn_edit.clicked.connect(self._on_edit)
        btn_row.addWidget(self.btn_edit)

        self.btn_remove = QPushButton("Usuń")
        self.btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self.btn_remove)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        close_row = QHBoxLayout()
        close_row.addStretch()
        self.btn_close = QPushButton("Zamknij")
        self.btn_close.clicked.connect(self.accept)
        close_row.addWidget(self.btn_close)
        layout.addLayout(close_row)

        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self._environments))
        for row, env in enumerate(self._environments):
            self.table.setItem(row, 0, QTableWidgetItem(env.label))
            self.table.setItem(
                row, 1, QTableWidgetItem(f"{env.rest_host}:{env.rest_port}")
            )
            self.table.setItem(row, 2, QTableWidgetItem(str(env.poll_interval_sec)))
            state_item = QTableWidgetItem("Tak" if env.enabled else "Nie")
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, state_item)

    def _forbidden_labels_excluding(self, index: Optional[int]) -> set[str]:
        labels = set(self._other_labels)
        for i, env in enumerate(self._environments):
            if i != index:
                labels.add(env.label.strip().casefold())
        return labels

    def _on_add(self) -> None:
        dialog = SplunkEnvironmentEditDialog(
            forbidden_labels=self._forbidden_labels_excluding(None), parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_env = dialog.result_environment()
            if new_env is not None:
                self._environments.append(new_env)
                self._refresh_table()

    def _selected_index(self) -> Optional[int]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return rows[0].row()

    def _on_edit(self) -> None:
        index = self._selected_index()
        if index is None:
            QMessageBox.information(
                self, "Brak wyboru", "Wybierz środowisko do edycji."
            )
            return

        dialog = SplunkEnvironmentEditDialog(
            forbidden_labels=self._forbidden_labels_excluding(index),
            initial=self._environments[index],
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited = dialog.result_environment()
            if edited is not None:
                self._environments[index] = edited
                self._refresh_table()

    def _on_remove(self) -> None:
        index = self._selected_index()
        if index is None:
            QMessageBox.information(
                self, "Brak wyboru", "Wybierz środowisko do usunięcia."
            )
            return

        env = self._environments[index]
        confirm = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            f"Usunąć środowisko '{env.label}'? Tej operacji nie da się cofnąć.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            del self._environments[index]
            self._refresh_table()

    def environments(self) -> list[SplunkEnvironment]:
        """Ostateczna lista środowisk po zamknięciu dialogu."""
        return list(self._environments)