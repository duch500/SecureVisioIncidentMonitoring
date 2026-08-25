"""Odczyt listy incydentów z okna SecureVisio przez UI Automation.

Moduł jest celowo niezależny od reszty aplikacji: nie wie nic o klientach,
alarmach ani GUI. Przyjmuje uchwyt okna (HWND), zwraca listę incydentów.

Metoda odczytu opiera się na wzorcach UIA GridPattern/TablePattern kontrolki
DataGrid. Zweryfikowano empirycznie, że działa niezależnie od tego, czy okno
jest aktywne, zasłonięte czy zminimalizowane - i bez aktywowania okna.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    import uiautomation as auto
except ImportError as exc:  # pragma: no cover - zależność środowiskowa
    raise ImportError(
        "Brak biblioteki 'uiautomation'. Zainstaluj: pip install uiautomation"
    ) from exc

logger = logging.getLogger(__name__)

# Typy kontrolek UIA, które mogą reprezentować siatkę incydentów.
GRID_CONTROL_TYPES = ("DataGridControl", "TableControl")

# Maksymalna głębokość przeszukiwania drzewa UIA w poszukiwaniu siatki.
MAX_TREE_DEPTH = 25

# Maksymalna głębokość schodzenia w dzieci komórki przy wyciąganiu tekstu.
MAX_CELL_DEPTH = 4

# Nazwy nagłówków kolumn, po których rozpoznajemy kluczowe pola.
# Kolumny identyfikujemy po nazwie, nie po pozycji - kolejność kolumn
# w SecureVisio może się zmienić (np. przeciągnięciem przez użytkownika).
COLUMN_ID = "Id"
COLUMN_STATUS = "Status"
COLUMN_NETWORK_MAP = "Mapa sieci"


class GridReadError(Exception):
    """Nie udało się odczytać siatki incydentów z okna."""


@dataclass(frozen=True)
class Incident:
    """Pojedynczy wiersz listy incydentów.

    Attributes:
        incident_id: Zawartość kolumny "Id" - unikalny identyfikator incydentu.
            Stanowi klucz maszyny stanów.
        status: Zawartość kolumny "Status" (np. "On Hold", "Nowe Zdarzenie").
        network_map: Zawartość kolumny "Mapa sieci" (np. "Mapa logiczna").
        row_index: Pozycja wiersza w siatce, zgodna z kolejnością wizualną.
        raw: Pełny wiersz w postaci mapy nazwa_kolumny -> wartość. Wypełniany
            tylko przy odczycie z full=True (tryb diagnostyczny); w normalnym
            monitorowaniu pozostaje pusty ze względu na koszt odczytu.
    """

    incident_id: str
    status: str
    network_map: str
    row_index: int
    raw: dict[str, str] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class GridSnapshot:
    """Wynik pojedynczego odczytu siatki.

    Attributes:
        incidents: Odczytane wiersze, w kolejności wizualnej.
        headers: Nazwy kolumn w kolejności występowania.
        row_count: Liczba wierszy zgłoszona przez GridPattern.
        column_count: Liczba kolumn zgłoszona przez GridPattern.
    """

    incidents: list[Incident]
    headers: list[str]
    row_count: int
    column_count: int


def _extract_text(element, depth: int = 0) -> str:
    """Wyciąga tekst z elementu UIA, próbując kolejnych strategii.

    Komórki WPF DataGrid często nie mają tekstu we własnym Name - tekst siedzi
    w zagnieżdżonym TextBlock. Dlatego po wyczerpaniu standardowych właściwości
    schodzimy rekurencyjnie w dzieci.
    """
    if element is None:
        return ""

    try:
        name = element.Name
        if name:
            return str(name)
    except Exception:  # noqa: BLE001 - UIA rzuca różnorodne błędy COM
        pass

    for pattern_getter in ("GetValuePattern", "GetLegacyIAccessiblePattern"):
        try:
            pattern = getattr(element, pattern_getter)()
            value = pattern.Value if pattern else None
            if value:
                return str(value)
        except Exception:  # noqa: BLE001
            pass

    if depth >= MAX_CELL_DEPTH:
        return ""

    try:
        for child in element.GetChildren():
            text = _extract_text(child, depth + 1)
            if text:
                return text
    except Exception:  # noqa: BLE001
        pass

    return ""


def _find_grid(root, max_depth: int = MAX_TREE_DEPTH):
    """Znajduje pierwszą kontrolkę siatki wspierającą GridPattern.

    W drzewie SecureVisio występuje kilka kontrolek listowych, z których tylko
    jedna (DataGrid listy incydentów) faktycznie udostępnia GridPattern.
    Pozostałe odrzucamy, sprawdzając wsparcie dla wzorca, a nie sam typ.
    """
    stack = [(root, 0)]

    while stack:
        element, depth = stack.pop()
        if depth > max_depth:
            continue

        try:
            control_type = element.ControlTypeName
        except Exception:  # noqa: BLE001
            continue

        if control_type in GRID_CONTROL_TYPES:
            try:
                if element.GetGridPattern():
                    return element
            except Exception:  # noqa: BLE001
                pass

        try:
            for child in element.GetChildren():
                stack.append((child, depth + 1))
        except Exception:  # noqa: BLE001
            pass

    return None


def _read_headers(grid, column_count: int) -> list[str]:
    """Odczytuje nazwy kolumn siatki.

    Zwraca listę o długości column_count - brakujące nazwy jako pusty string,
    żeby indeksowanie kolumn pozostało spójne niezależnie od powodzenia odczytu.
    """
    headers: list[str] = []

    try:
        table_pattern = grid.GetTablePattern()
        if table_pattern:
            headers = [_extract_text(h) for h in table_pattern.GetColumnHeaders()]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Nie udało się odczytać nagłówków kolumn: %s", exc)

    if len(headers) < column_count:
        headers.extend([""] * (column_count - len(headers)))

    return headers[:column_count]


def _column_index(headers: list[str], name: str) -> Optional[int]:
    """Zwraca indeks kolumny o podanej nazwie nagłówka (bez uwzględniania wielkości liter)."""
    target = name.strip().casefold()
    for index, header in enumerate(headers):
        if header.strip().casefold() == target:
            return index
    return None


def read_incidents(hwnd: int, full: bool = False) -> GridSnapshot:
    """Odczytuje listę incydentów z okna SecureVisio o podanym HWND.

    Args:
        hwnd: Uchwyt okna SecureVisio.
        full: Gdy True, czyta wszystkie kolumny i wypełnia pole Incident.raw.
            Wolniejsze - przeznaczone wyłącznie do diagnostyki. W normalnym
            monitorowaniu pozostaw False.

    Returns:
        GridSnapshot z odczytanymi wierszami.

    Raises:
        GridReadError: Gdy okno jest niedostępne, nie zawiera siatki incydentów
            albo siatka nie udostępnia wymaganych kolumn. Wywołujący powinien
            potraktować to jako stan "niedostępny", a nie "brak zdarzeń".
    """
    try:
        root = auto.ControlFromHandle(hwnd)
    except Exception as exc:  # noqa: BLE001
        raise GridReadError(f"Nie udało się połączyć z oknem (HWND={hwnd}): {exc}") from exc

    if root is None:
        raise GridReadError(f"Okno o HWND={hwnd} nie istnieje lub zostało zamknięte.")

    grid = _find_grid(root)
    if grid is None:
        raise GridReadError(
            f"Nie znaleziono siatki incydentów w oknie HWND={hwnd}. "
            "Upewnij się, że w SecureVisio otwarty jest widok listy incydentów."
        )

    try:
        grid_pattern = grid.GetGridPattern()
        row_count = int(grid_pattern.RowCount)
        column_count = int(grid_pattern.ColumnCount)
    except Exception as exc:  # noqa: BLE001
        raise GridReadError(f"Brak dostępu do GridPattern (HWND={hwnd}): {exc}") from exc

    headers = _read_headers(grid, column_count)

    idx_id = _column_index(headers, COLUMN_ID)
    idx_status = _column_index(headers, COLUMN_STATUS)
    idx_map = _column_index(headers, COLUMN_NETWORK_MAP)

    if idx_id is None or idx_status is None:
        raise GridReadError(
            f"Siatka nie zawiera wymaganych kolumn '{COLUMN_ID}' i '{COLUMN_STATUS}'. "
            f"Odczytane nagłówki: {headers}"
        )

    # Czytamy tylko kolumny, których faktycznie potrzebujemy. Odczyt każdej
    # komórki to osobne wywołanie COM - przy 20 wierszach i 18 kolumnach daje
    # to 360 wywołań na okno. Ograniczenie do 2-3 kolumn skraca odczyt
    # kilkukrotnie, co przekłada się wprost na dopuszczalny interwał sprawdzania.
    wanted: dict[str, int] = {"id": idx_id, "status": idx_status}
    if idx_map is not None:
        wanted["map"] = idx_map

    if full:
        wanted = {headers[c] or f"col_{c}": c for c in range(column_count)}

    incidents: list[Incident] = []

    for row in range(row_count):
        values: dict[str, str] = {}
        failed_cells = 0

        for key, col in wanted.items():
            try:
                cell = grid_pattern.GetItem(row, col)
                values[key] = _extract_text(cell)
            except Exception:  # noqa: BLE001
                values[key] = ""
                failed_cells += 1

        if failed_cells == len(wanted):
            logger.warning("Wiersz %d: nie udało się odczytać żadnej komórki, pomijam.", row)
            continue

        if full:
            incident_id = values.get(headers[idx_id] or f"col_{idx_id}", "").strip()
            status = values.get(headers[idx_status] or f"col_{idx_status}", "").strip()
            network_map = (
                values.get(headers[idx_map] or f"col_{idx_map}", "").strip()
                if idx_map is not None
                else ""
            )
        else:
            incident_id = values.get("id", "").strip()
            status = values.get("status", "").strip()
            network_map = values.get("map", "").strip()

        if not incident_id:
            logger.debug("Wiersz %d: brak Id incydentu, pomijam.", row)
            continue

        incidents.append(
            Incident(
                incident_id=incident_id,
                status=status,
                network_map=network_map,
                row_index=row,
                raw=values if full else {},
            )
        )

    logger.debug(
        "HWND=%d: odczytano %d/%d wierszy, %d kolumn.",
        hwnd,
        len(incidents),
        row_count,
        column_count,
    )

    return GridSnapshot(
        incidents=incidents,
        headers=headers,
        row_count=row_count,
        column_count=column_count,
    )