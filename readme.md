# SecureVisio Monitor

> Program pilnuje wszystkich Twoich środowisk SecureVisio i głośno informuje o nowym zdarzeniu.

Instrukcja nie wymaga wiedzy programistycznej.

## Spis treści

- [Czym jest ten program](#czym-jest-ten-program)
- [Co trzeba przygotować](#co-trzeba-przygotować)
- [Przygotowanie komputera (tylko wersja źródłowa)](#przygotowanie-komputera-tylko-wersja-źródłowa)
- [Pierwsze uruchomienie i konfiguracja](#pierwsze-uruchomienie-i-konfiguracja)
- [Codzienna obsługa](#codzienna-obsługa)
- [Sposób alarmowania: pełny ekran czy powiadomienia Windows](#sposób-alarmowania-pełny-ekran-czy-powiadomienia-windows)
- [Kolory alarmów](#kolory-alarmów)
- [Ustawienia](#ustawienia)
- [Gdy coś nie działa](#gdy-coś-nie-działa)
- [Gdzie szukać informacji](#gdzie-szukać-informacji)
- [Aktualizacja programu](#aktualizacja-programu)
- [Wygodniejsze uruchamianie](#wygodniejsze-uruchamianie)
- [Szybka ściąga](#szybka-ściąga)

## Czym jest ten program

Kiedy pracujesz z kilkoma środowiskami SecureVisio jednocześnie, łatwo przeoczyć moment, w którym w jednym z nich pojawia się nowe zdarzenie. Trzeba pamiętać, żeby regularnie zaglądać do każdego okna po kolei.

**SecureVisio Monitor robi to za Ciebie.** Co kilkanaście sekund sprawdza wszystkie środowiska naraz, a gdy pojawi się nowe zdarzenie — alarmuje w sposób, który sam wybierzesz: dużym czerwonym ekranem na wszystkich monitorach albo powiadomieniem systemowym Windows w rogu ekranu, w obu przypadkach z sygnałem dźwiękowym.

### Co program potrafi

- ✅ Pilnuje jednocześnie wielu środowisk SecureVisio — dowolnej liczby
- ✅ Działa również wtedy, gdy okna SecureVisio są zminimalizowane lub zasłonięte innymi programami
- ✅ Nie przeszkadza w pracy — nie przełącza okien i nie zabiera Ci klawiatury
- ✅ Informuje, którego klienta dotyczy zdarzenie
- ✅ Pozwala jednym kliknięciem otworzyć na pełnym ekranie środowisko, w którym coś się wydarzyło
- ✅ Budzi sygnałem dźwiękowym — przydatne podczas dyżuru nocnego
- ✅ Wykrywa też, gdy SecureVisio straci połączenie z serwerem albo gdy jakieś środowisko zostanie zamknięte
- ✅ Pozwala wybrać, czy alarm ma być pełnoekranowy, czy w formie powiadomienia Windows
- ✅ Pozwala dowolnie ustawić kolor tła każdego rodzaju alarmu

### Czego program nie robi

- ❌ Nie zmienia niczego w systemie SecureVisio — wyłącznie odczytuje
- ❌ Nie obsługuje incydentów za Ciebie
- ❌ Nie wysyła powiadomień na telefon ani e-mailem
- ❌ Nie zapisuje historii zdarzeń

> [!IMPORTANT]
> **Najważniejsza zasada działania:** program alarmuje w momencie pojawienia się nowego zdarzenia, a nie przez cały czas, gdy ono istnieje. Oznacza to, że dostaniesz jeden alarm na jedno zdarzenie. Jeżeli zdarzenie nie zostanie obsłużone, program przypomni o nim po minucie — chyba że wcześniej potwierdzisz, że je widzisz. Gdy pojawi się kolejne, nowe zdarzenie, alarm zabrzmi ponownie.

## Co trzeba przygotować

Zanim zaczniesz, upewnij się, że masz wszystko z poniższej listy.

| Element | Uwagi |
|---|---|
| Komputer z systemem Windows | Program działa tylko na Windows |
| Zainstalowane środowiska SecureVisio | Te same, których używasz na co dzień |
| Pliki programu SecureVisio Monitor | Katalog otrzymany od osoby przekazującej program |
| Około 15 minut na pierwsze uruchomienie | Kolejne uruchomienia zajmują kilka sekund |

Nie potrzebujesz uprawnień administratora. Nie potrzebujesz dostępu do internetu — program działa wyłącznie na Twoim komputerze.

### Dwie wersje programu

Program może być przekazany w jednej z dwóch postaci. Sprawdź, którą masz — od tego zależy, czy wykonujesz sekcję [Przygotowanie komputera](#przygotowanie-komputera-tylko-wersja-źródłowa).

| Co widzisz w katalogu | Która to wersja | Co zrobić |
|---|---|---|
| Plik `SecureVisioMonitor.exe` | Wersja gotowa | Pomiń przygotowanie komputera, przejdź do pierwszego uruchomienia |
| Pliki `app.py`, `requirements.txt` i inne | Wersja źródłowa | Wykonaj przygotowanie komputera |

## Przygotowanie komputera (tylko wersja źródłowa)

> [!NOTE]
> Tę sekcję wykonujesz tylko raz i tylko wtedy, gdy w katalogu programu nie ma pliku `SecureVisioMonitor.exe`. Jeżeli ten plik jest — przejdź od razu do pierwszego uruchomienia.

### Krok 1 — zainstaluj Pythona

Python to program, który jest potrzebny do uruchomienia monitora. Instaluje się go raz.

1. Otwórz przeglądarkę i wejdź na stronę [python.org/downloads](https://www.python.org/downloads/)
2. Kliknij duży żółty przycisk pobierania
3. Uruchom pobrany plik
4. **WAŻNE:** na pierwszym ekranie instalatora zaznacz pole **„Add python.exe to PATH"** na dole okna. Bez tego program się nie uruchomi
5. Kliknij **„Install Now"** i poczekaj na zakończenie

**Sprawdź, czy się udało:**

1. Naciśnij klawisze `Windows + R`
2. Wpisz `powershell` i naciśnij Enter
3. W czarnym oknie wpisz poniższą komendę i naciśnij Enter:

   ```powershell
   python --version
   ```

✔️ Powinieneś zobaczyć napis podobny do: `Python 3.14.6`

> Jeżeli zamiast tego pojawia się komunikat, że nie rozpoznano polecenia — najprawdopodobniej nie zaznaczyłeś pola „Add python.exe to PATH". Uruchom instalator ponownie, wybierz opcję zmiany instalacji (Modify) i zaznacz je.

### Krok 2 — zainstaluj potrzebne dodatki

Program korzysta z kilku dodatkowych komponentów. Pobierzesz je jedną komendą.

1. Otwórz katalog z plikami programu w Eksploratorze Windows
2. Kliknij prawym przyciskiem myszy na pustym miejscu w tym katalogu, trzymając wciśnięty klawisz Shift
3. Wybierz **„Otwórz okno programu PowerShell tutaj"** lub **„Otwórz w Terminalu"**
4. Wklej poniższą komendę i naciśnij Enter:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Poczekaj — instalacja trwa kilka minut i wypisuje dużo tekstu. To normalne

✔️ Na końcu powinien pojawić się napis zaczynający się od: `Successfully installed`

## Pierwsze uruchomienie i konfiguracja

### Krok 1 — przygotuj SecureVisio

Zanim uruchomisz monitor, przygotuj środowiska, które ma pilnować.

1. Uruchom wszystkie środowiska SecureVisio, które chcesz monitorować
2. W każdym z nich kliknij pozycję **„Incydenty"** w menu po lewej stronie

> [!IMPORTANT]
> To bardzo ważne. Program odczytuje dane z listy incydentów. Jeżeli okno SecureVisio pokazuje mapę sieci albo szczegóły pojedynczego incydentu, monitor nie będzie w stanie nic odczytać z tego środowiska.
>
> Po ustawieniu widoku możesz spokojnie zminimalizować okna SecureVisio — program czyta je również wtedy, gdy są zminimalizowane. Widok musi być ustawiony w momencie uruchamiania monitorowania.

### Krok 2 — zaakceptuj warunki korzystania

Przy pierwszym uruchomieniu (i po każdej aktualizacji programu) pojawi się okno z treścią pliku `LICENCJA.txt`.

1. Przeczytaj warunki
2. Kliknij **„Akceptuję"**, żeby przejść dalej

> [!WARNING]
> Kliknięcie **„Nie akceptuję"** albo zamknięcie tego okna krzyżykiem kończy program natychmiast — okno główne w ogóle się nie pokaże. Żeby uruchomić program ponownie, wystarczy odpalić go jeszcze raz i tym razem zaakceptować warunki.

✔️ Po zaakceptowaniu okno znika i otwiera się główne okno programu. Przy kolejnych uruchomieniach (tej samej wersji programu) ten ekran już się nie pojawi.

### Krok 3 — uruchom program

Zależnie od posiadanej wersji:

| Wersja | Jak uruchomić |
|---|---|
| Gotowa | Kliknij dwukrotnie plik `SecureVisioMonitor.exe` |
| Źródłowa | Kliknij dwukrotnie plik `Uruchom.bat` |

✔️ Powinno otworzyć się okno o nazwie „SecureVisio Monitor" z pustą tabelą u góry.

> Wersja gotowa (.exe) uruchamia się przez kilka sekund — to normalne, plik rozpakowuje się przed startem. Nie klikaj wielokrotnie.

### Krok 4 — wskaż, gdzie są środowiska

Program musi wiedzieć, gdzie na dysku znajdują się Twoje środowiska SecureVisio, żeby rozpoznać, które okno należy do którego klienta.

1. Otwórz Eksplorator Windows i znajdź katalog, w którym trzymasz środowiska SecureVisio
2. Wejdź o jeden poziom wyżej — tak, żeby widzieć katalogi z nazwami klientów obok siebie
3. Kliknij w pasek adresu Eksploratora i skopiuj ścieżkę (`Ctrl+C`)
4. Wklej ją w oknie programu w pole **„Katalog środowisk"**

Przykład: jeżeli Twoje środowiska wyglądają tak:

```
C:\SecureVisio\Klient A\..
C:\SecureVisio\Klient B\..
C:\SecureVisio\Klient C\..
```

to w pole wpisujesz:

```
C:\SecureVisio
```

> Nazwy klientów, które zobaczysz później na alarmie, biorą się z nazw tych katalogów. W przykładzie powyżej będą to: Klient A, Klient B, Klient C.

### Krok 5 — uruchom monitorowanie

Kliknij przycisk **„Start"** na dole okna.

✔️ W tabeli powinny pojawić się wiersze — po jednym na każde środowisko — z zielonym tłem i napisem OK.

Sprawdź, czy wszystko się zgadza:

| Kolumna | Co powinna pokazywać |
|---|---|
| Klient | Nazwę środowiska, na przykład Klient A |
| Stan | OK na zielonym tle |
| Ostatni odczyt | Aktualną godzinę |
| Incydenty | Liczbę incydentów widoczną na liście w SecureVisio |
| Czas odczytu | Ułamek sekundy, zwykle 0,3–0,7 s |
| Uwagi | Pusto (albo informację o zminimalizowanym oknie) |

> Jeżeli któreś środowisko ma stan NIEDOSTĘPNY na pomarańczowym tle — najczęściej oznacza to, że nie jest ustawione na widoku listy incydentów. Wróć do kroku 1, ustaw widok i kliknij „Sprawdź teraz".

### Krok 6 — sprawdź alarm

Zanim zdasz się na program, przekonaj się, że alarm działa i jest dla Ciebie widoczny.

1. Kliknij przycisk **„Testuj alarm"** w prawym dolnym rogu
2. Zależnie od wybranego [sposobu alarmowania](#sposób-alarmowania-pełny-ekran-czy-powiadomienia-windows) pojawi się czerwony ekran na wszystkich monitorach albo powiadomienie Windows w rogu ekranu
3. Zamknij alarm — kliknij w tło (tryb pełnoekranowy) albo w powiadomienie (tryb Windows)

✔️ Alarm pojawił się i dał się zamknąć.

Sprawdź też dźwięk — kliknij przycisk **„Odtwórz"** obok listy dźwięków. Kliknij ponownie, żeby przerwać.

> Ustaw głośność tak, żeby alarm był słyszalny również wtedy, gdy odejdziesz od biurka. Jeżeli planujesz dyżur nocny, sprawdź to przy nocnych ustawieniach głośności komputera.

## Codzienna obsługa

### Rozpoczęcie pracy

1. Uruchom środowiska SecureVisio i ustaw w każdym widok „Incydenty"
2. Uruchom SecureVisio Monitor
3. Kliknij **„Start"**
4. Sprawdź, czy wszystkie środowiska mają stan OK

> [!WARNING]
> Uruchomienie programu nie rozpoczyna monitorowania automatycznie. Trzeba kliknąć „Start". Jeżeli tego nie zrobisz, program będzie otwarty, ale nic nie będzie pilnował.

### Co widzisz, gdy pojawi się zdarzenie

W trybie pełnoekranowym: na wszystkich monitorach wyświetli się czerwony ekran z napisem **NOWE ZDARZENIE**, a pod nim lista — miejsce zdarzenia i nazwa klienta. W trybie powiadomień Windows: w rogu ekranu pojawi się osobne powiadomienie dla każdego zdarzenia. W obu trybach jednocześnie zabrzmi sygnał dźwiękowy.

Masz kilka możliwości:

| Co robisz | Co się dzieje |
|---|---|
| Klikasz w tło ekranu / treść powiadomienia | Alarm znika, dźwięk milknie. Program uznaje, że widziałeś zdarzenie i nie będzie o nim przypominał. Okna SecureVisio pozostają nietknięte |
| Klikasz przycisk „Pokaż" przy danej pozycji | To środowisko SecureVisio otwiera się na pełnym ekranie, żebyś od razu widział incydent |
| Nie robisz nic | Alarm znika (po 10 sekundach w trybie pełnoekranowym albo zgodnie z ustawieniami Windows w trybie powiadomień), ale wróci po minucie, dopóki zdarzenie nie zostanie obsłużone |

> Gdy alarm dotyczy kilku środowisk naraz w trybie pełnoekranowym, kliknięcie „Pokaż" przy jednym z nich otwiera to środowisko, a alarm pozostaje widoczny na pozostałych monitorach — możesz zająć się nimi po kolei. W trybie powiadomień Windows każde zdarzenie ma osobne powiadomienie, więc obsługujesz je niezależnie.

### Dwa pozostałe rodzaje alarmu

Poza czerwonym alarmem o nowym zdarzeniu program sygnalizuje jeszcze dwie sytuacje:

| Alarm | Kiedy się pojawia | Jak się zachowuje |
|---|---|---|
| 🟠 Środowisko zamknięte | Okno SecureVisio zniknęło (zamknięte albo przestało odpowiadać) | Pojawia się raz, bez dźwięku, bez przycisku „Pokaż" — nie ma czego pokazać |
| 🟣 Zerwane połączenie | SecureVisio zgłosiło błąd połączenia z serwerem | Pojawia się raz, bez dźwięku, z przyciskiem „Pokaż" — żebyś mógł od razu przejść do okna i kliknąć „Ponów próbę" |

> [!NOTE]
> Gdy środowisko zgłasza zerwane połączenie, dane, które program wcześniej odczytał z niego, mogą być nieaktualne. Monitorowanie nowych zdarzeń dla tego środowiska jest wtedy wstrzymane, dopóki połączenie nie wróci — program da Ci znać w logu, gdy tak się stanie.

### Zakończenie pracy

Kliknij **„Stop"**, żeby wstrzymać monitorowanie, albo zamknij okno programu krzyżykiem — ustawienia zapiszą się automatycznie, a program zakończy działanie całkowicie (nie zostaje w tle).

> Zamknięcie programu kasuje pamięć o potwierdzonych zdarzeniach. Po ponownym uruchomieniu nieobsłużone zdarzenia mogą wywołać alarm jeszcze raz. Jeżeli Ci to przeszkadza, odznacz pole „Alarmuj o zdarzeniach zastanych przy starcie".

### Przyciski w oknie programu

| Przycisk | Do czego służy |
|---|---|
| Start | Rozpoczyna monitorowanie |
| Stop | Wstrzymuje monitorowanie |
| Sprawdź teraz | Sprawdza wszystkie środowiska natychmiast, bez czekania |
| Testuj alarm | Pokazuje przykładowy alarm — do sprawdzenia widoczności |
| Dodaj plik... | Dodaje własny dźwięk alarmu |
| Odtwórz | Odtwarza wybrany dźwięk, żebyś mógł go posłuchać |
| O programie | Pokazuje informacje o autorze i wersji programu |

## Sposób alarmowania: pełny ekran czy powiadomienia Windows

W ustawieniach, w polu **„Sposób alarmowania"**, wybierasz jeden z dwóch trybów — nie mogą działać oba naraz.

| Tryb | Jak wygląda | Kiedy wybrać |
|---|---|---|
| Pełny ekran (wszystkie monitory) | Duży, kolorowy ekran zajmujący całą powierzchnię każdego monitora | Gdy chcesz, żeby alarmu nie dało się przeoczyć — dobre na dyżur nocny |
| Powiadomienia Windows (róg ekranu) | Standardowe powiadomienie systemowe, jak inne aplikacje Windows | Gdy pracujesz na wielu rzeczach naraz i wolisz mniej inwazyjny sygnał |

> [!TIP]
> Przełączenie trybu w trakcie monitorowania jest zablokowane — zatrzymaj monitorowanie („Stop"), zmień tryb, uruchom ponownie („Start").

> [!WARNING]
> Jeżeli wybierzesz powiadomienia Windows, a z jakiegoś powodu nie da się ich wyświetlić (np. ograniczenia systemowe), program automatycznie pokaże zamiast tego alarm pełnoekranowy — żebyś na pewno dostał sygnał. Informacja o tym pojawi się w logu.

## Kolory alarmów

W ustawieniach, w wierszu **„Kolory alarmów"**, możesz zmienić kolor tła dla każdego z trzech rodzajów alarmu osobno: nowego zdarzenia, zamkniętego środowiska i zerwanego połączenia.

1. Kliknij przycisk odpowiadający rodzajowi alarmu, który chcesz zmienić — przycisk pokazuje aktualnie ustawiony kolor
2. Wybierz nowy kolor w oknie, które się otworzy, i potwierdź
3. Zmiana obowiązuje od razu, przy najbliższym alarmie tego rodzaju

Kolor tekstu na alarmie dobiera się sam do wybranego tła — nie musisz się martwić, że jasny kolor tła zrobi napis nieczytelnym.

Żeby wrócić do kolorów domyślnych (czerwony / pomarańczowy / fioletowy), kliknij **„Domyślne"**.

> [!NOTE]
> Wybór koloru dotyczy wyłącznie trybu pełnoekranowego. Wygląd powiadomień Windows kontroluje system operacyjny — gdy masz wybrany tryb powiadomień, przyciski wyboru koloru są wyszarzone.

## Ustawienia

Wszystkie ustawienia znajdują się w środkowej części okna i zapisują się automatycznie.

| Ustawienie | Co oznacza | Kiedy zmieniać |
|---|---|---|
| Katalog środowisk | Miejsce na dysku, gdzie trzymasz środowiska SecureVisio | Gdy przeniesiesz środowiska w inne miejsce |
| Frazy nowego zdarzenia | Napisy w kolumnie Status, na które program ma reagować | Gdy Twoje SecureVisio używa innego napisu (patrz niżej) |
| Interwał | Co ile sekund program sprawdza środowiska | Rzadko — domyślne 10 s jest bezpieczne |
| Alarm widoczny | Ile sekund wyświetla się ekran alarmu (tryb pełnoekranowy) | Gdy 10 sekund to dla Ciebie za krótko lub za długo |
| Przypomnienie po | Po ilu sekundach alarm wraca, jeśli go nie potwierdzisz | Gdy chcesz częstsze lub rzadsze przypomnienia |
| Alarmuj o zdarzeniach zastanych | Czy alarmować o zdarzeniach istniejących już przy starcie | Odznacz, jeśli restart programu ma nie powtarzać alarmów |
| Tryb diagnostyczny | Zapisuje szczegółowe informacje do pliku | Tylko gdy szukasz przyczyny problemu |
| Sposób alarmowania | Pełny ekran albo powiadomienia Windows | Patrz [sekcja wyżej](#sposób-alarmowania-pełny-ekran-czy-powiadomienia-windows) |
| Kolory alarmów | Kolor tła każdego rodzaju alarmu | Patrz [sekcja wyżej](#kolory-alarmów) |
| Dźwięk alarmu | Włącza sygnał dźwiękowy i pozwala wybrać plik | Odznacz, gdy pracujesz w ciszy |
| Głośność | Głośność sygnału względem głośności systemu | Ustaw raz, na początku |

### Ważne: sprawdź frazy przy pierwszym zdarzeniu

> [!CAUTION]
> Program szuka w kolumnie Status napisów „Nowe Zdarzenie" oraz „New Event". Nie zostało potwierdzone, że Twoja wersja SecureVisio używa dokładnie takich napisów. Przy pierwszym prawdziwym incydencie porównaj napis w kolumnie Status z tym, co masz wpisane w polu „Frazy nowego zdarzenia". Jeżeli się różnią — dopisz właściwy napis, oddzielając go średnikiem.

Przykład, gdy Twoje SecureVisio pokazuje status „Nowy":

```
Nowe Zdarzenie; New Event; Nowy
```

Po zmianie kliknij **„Stop"**, a następnie **„Start"**, żeby ustawienie zaczęło obowiązywać.

### Dodanie własnego dźwięku

1. Przygotuj plik dźwiękowy w formacie WAV (inne formaty nie są obsługiwane)
2. Kliknij **„Dodaj plik..."** i wskaż go
3. Plik zostanie skopiowany do programu i pojawi się na liście
4. Wybierz go z listy i kliknij **„Odtwórz"**, żeby sprawdzić

> Plik jest kopiowany do programu, więc możesz spokojnie usunąć oryginał — alarm będzie działał dalej.

## Gdy coś nie działa

<details>
<summary><strong>Środowisko ma stan NIEDOSTĘPNY</strong></summary>

**Co widzisz:** Wiersz w tabeli jest pomarańczowy, w kolumnie Uwagi widnieje komunikat o błędzie.

**Dlaczego:** Najczęściej to okno SecureVisio nie jest ustawione na widoku listy incydentów. Program nie ma wtedy skąd odczytać danych.

**Co zrobić:**
1. Przejdź do tego okna SecureVisio
2. Kliknij „Incydenty" w menu po lewej stronie
3. Wróć do monitora i kliknij „Sprawdź teraz"

✔️ Wiersz zmienia kolor na zielony, a stan na OK.

</details>

<details>
<summary><strong>Tabela jest pusta po kliknięciu Start</strong></summary>

**Co widzisz:** Po uruchomieniu monitorowania nie pojawia się żaden wiersz, a pod tabelą widnieje „Monitorowane: 0/0".

**Dlaczego:** Program nie rozpoznał żadnego okna SecureVisio. Zwykle oznacza to źle wpisany katalog środowisk.

**Co zrobić:**
1. Sprawdź, czy środowiska SecureVisio są w ogóle uruchomione
2. Sprawdź pole „Katalog środowisk" — musi wskazywać katalog **nadrzędny**, w którym leżą katalogi klientów, a nie katalog jednego klienta
3. Popraw ścieżkę, kliknij „Stop", a potem „Start"

✔️ W tabeli pojawiają się wiersze wszystkich środowisk.

</details>

<details>
<summary><strong>Środowisko zniknęło z tabeli i pojawił się pomarańczowy alarm</strong></summary>

**Co widzisz:** Alarm z napisem ŚRODOWISKO ZAMKNIĘTE i nazwą klienta.

**Dlaczego:** Okno SecureVisio zostało zamknięte lub przestało odpowiadać. Program informuje, że przestał je pilnować.

**Co zrobić:**
1. Zamknij alarm (kliknij w tło albo w powiadomienie)
2. Jeżeli zamknąłeś to środowisko celowo — nic więcej nie musisz robić
3. Jeżeli nie — uruchom SecureVisio ponownie, ustaw widok „Incydenty". Program sam je wykryje i wznowi monitorowanie

✔️ W polu „Log bieżący" pojawia się wpis, że środowisko wróciło.

</details>

<details>
<summary><strong>Pojawił się fioletowy alarm ZERWANE POŁĄCZENIE</strong></summary>

**Co widzisz:** Alarm z napisem ZERWANE POŁĄCZENIE i nazwą klienta, z przyciskiem „Pokaż".

**Dlaczego:** SecureVisio zgłosiło błąd połączenia z serwerem — zwykle widać wtedy w samym SecureVisio okno z komunikatem i przyciskiem „Ponów próbę".

**Co zrobić:**
1. Kliknij „Pokaż", żeby przejść od razu do tego środowiska
2. W oknie SecureVisio kliknij „Ponów próbę" (albo postępuj zgodnie z tym, co pokazuje SecureVisio)
3. Program sam wykryje przywrócenie połączenia i wznowi monitorowanie tego środowiska

✔️ W polu „Log bieżący" pojawia się wpis, że połączenie zostało przywrócone.

</details>

<details>
<summary><strong>Nie słyszę dźwięku alarmu</strong></summary>

**Co widzisz:** Alarm się pojawia, ale bez dźwięku.

**Dlaczego:** Dźwięk może być wyłączony w programie, wyciszony w systemie albo ustawiony na zbyt niski poziom.

**Co zrobić:**
1. Sprawdź, czy pole „Dźwięk alarmu" jest zaznaczone
2. Kliknij „Odtwórz" — jeżeli nic nie słychać, problem jest w dźwięku, nie w alarmie
3. Sprawdź głośność systemu Windows (ikona głośnika przy zegarze) i mikser głośności
4. Przesuń suwak głośności w programie w prawo

✔️ Po kliknięciu „Odtwórz" słychać sygnał alarmowy.

</details>

<details>
<summary><strong>Suwak głośności jest szary i nie działa</strong></summary>

**Co widzisz:** Obok suwaka widnieje napis „sys." zamiast wartości procentowej.

**Dlaczego:** Brakuje komponentu odpowiedzialnego za regulację głośności. Dźwięk działa, ale sterujesz nim głośnością systemu.

**Co zrobić:**
1. Steruj głośnością przez ikonę głośnika w Windows — to w pełni wystarcza
2. Jeżeli chcesz przywrócić suwak, zgłoś to osobie, która przekazała Ci program

✔️ Dźwięk alarmu jest słyszalny na odpowiednim poziomie.

</details>

<details>
<summary><strong>Przyciski wyboru koloru są wyszarzone</strong></summary>

**Co widzisz:** W wierszu „Kolory alarmów" przyciski nie reagują na kliknięcie, widoczna jest notka „(nie dotyczy powiadomień Windows)".

**Dlaczego:** Masz wybrany tryb powiadomień Windows — ich wyglądem steruje system, nie program.

**Co zrobić:**

Zmień „Sposób alarmowania" na „Pełny ekran", jeżeli chcesz mieć możliwość zmiany kolorów.

✔️ Przyciski kolorów stają się aktywne.

</details>

<details>
<summary><strong>Zdarzenie było, ale alarmu nie było</strong></summary>

**Co widzisz:** W SecureVisio widać nowe zdarzenie, monitor pokazywał OK i nie zaalarmował.

**Dlaczego:** Najprawdopodobniej Twoje SecureVisio używa innego napisu statusu niż ten wpisany w ustawieniach programu.

**Co zrobić:**
1. Otwórz SecureVisio i przepisz dokładnie napis z kolumny Status dla tego zdarzenia
2. Porównaj go z zawartością pola „Frazy nowego zdarzenia" w monitorze
3. Jeżeli się różnią, dopisz właściwy napis po średniku
4. Kliknij „Stop", a potem „Start"

✔️ Przy kolejnym zdarzeniu alarm pojawia się poprawnie.

</details>

<details>
<summary><strong>Program otwiera się na chwilę i od razu znika</strong></summary>

**Co widzisz:** Krótko mignie okno, po czym program się zamyka — bez błędu, bez dalszego działania.

**Dlaczego:** Najczęściej to przypadkowe kliknięcie „Nie akceptuję" albo krzyżyka w oknie warunków korzystania, które pojawia się przy pierwszym uruchomieniu (i po każdej aktualizacji). Bez zaakceptowania warunków program celowo się nie uruchamia.

**Co zrobić:**
1. Uruchom program ponownie
2. W oknie „Warunki korzystania" przeczytaj treść i kliknij **„Akceptuję"**

✔️ Otwiera się główne okno „SecureVisio Monitor".

</details>

<details>
<summary><strong>Program w ogóle się nie uruchamia</strong></summary>

**Co widzisz:** Podwójne kliknięcie nic nie daje albo pojawia się i znika czarne okno.

**Dlaczego:** W wersji źródłowej zwykle oznacza to brak Pythona lub niezainstalowane dodatki.

**Co zrobić:**
1. Sprawdź, czy wykonałeś oba kroki z sekcji [Przygotowanie komputera](#przygotowanie-komputera-tylko-wersja-źródłowa)
2. Otwórz PowerShell w katalogu programu i uruchom go tak, żeby zobaczyć komunikat błędu:

   ```powershell
   python app.py
   ```

3. Zanotuj treść błędu i przekaż ją osobie, która udostępniła Ci program

✔️ Otwiera się okno „SecureVisio Monitor".

</details>

> [!TIP]
> **Najczęstsza przyczyna problemów:** jeżeli coś nie działa, w dziewięciu przypadkach na dziesięć któreś okno SecureVisio nie jest ustawione na widoku listy incydentów. Sprawdź to najpierw.

## Gdzie szukać informacji

### Log w oknie programu

Pole **„Log bieżący"** na dole okna pokazuje, co program robił: kiedy wykrył zdarzenie, kiedy je potwierdziłeś, kiedy środowisko zniknęło, wróciło albo utraciło połączenie. To pierwsze miejsce, do którego warto zajrzeć.

Log czyści się przy zamknięciu programu — jeżeli chcesz coś zachować, zaznacz tekst i skopiuj.

### Plik z błędami

Program zapisuje błędy do pliku:

```
logs\monitor.log
```

Znajdziesz go w katalogu programu. Otwórz go Notatnikiem.

> Pusty plik albo jego brak to dobra wiadomość — oznacza, że nie wystąpił żaden błąd. Program zapisuje tam wyłącznie problemy, a nie normalną pracę.

### Tryb diagnostyczny

Gdy trzeba zbadać problem dokładniej, zaznacz pole **„Tryb diagnostyczny (szczegółowe logi)"**. Program zacznie zapisywać znacznie więcej informacji.

> Po zakończeniu diagnostyki odznacz to pole. W trybie diagnostycznym do pliku trafiają także dane incydentów — ich numery i statusy — a plik szybko się zapełnia.

## Aktualizacja programu

Program nie aktualizuje się sam. Gdy otrzymasz nową wersję:

1. Zamknij program
2. Zrób kopię pliku `settings.json` z katalogu programu — zawiera Twoje ustawienia (w tym wybrane kolory). Wystarczy skopiować go na pulpit
3. Jeżeli masz własne dźwięki, skopiuj też katalog `sounds`
4. Zastąp pliki programu nowymi
5. Uruchom program i sprawdź, czy ustawienia są na miejscu

> Ustawienia zwykle zachowują się same, bo plik `settings.json` nie jest nadpisywany przez nową wersję. Kopia to zabezpieczenie na wszelki wypadek.

## Wygodniejsze uruchamianie

### Skrót na pulpicie

1. Znajdź plik, którym uruchamiasz program (`SecureVisioMonitor.exe` lub `Uruchom.bat`)
2. Kliknij go prawym przyciskiem myszy
3. Wybierz **„Pokaż więcej opcji"**, a następnie **„Wyślij do" → „Pulpit (utwórz skrót)"**

✔️ Na pulpicie pojawia się skrót, którym uruchomisz program jednym dwuklikiem.

### Uruchamianie razem z Windows

1. Naciśnij `Windows + R`
2. Wpisz `shell:startup` i naciśnij Enter
3. Przeciągnij do otwartego katalogu skrót do programu

> Program uruchomi się sam po zalogowaniu, ale nadal trzeba kliknąć „Start", żeby rozpocząć monitorowanie. Automatyczne rozpoczynanie nie jest dostępne.

## Szybka ściąga

### Codzienny start — 4 kroki

1. Uruchom środowiska SecureVisio
2. W każdym kliknij „Incydenty"
3. Uruchom SecureVisio Monitor
4. Kliknij „Start" i sprawdź, czy wszystkie wiersze są zielone

### Gdy zabrzmi alarm

| Chcesz... | Zrób to |
|---|---|
| Zobaczyć incydent od razu | Kliknij „Pokaż" przy odpowiedniej pozycji |
| Tylko zamknąć alarm | Kliknij w tło ekranu / w treść powiadomienia |
| Zająć się tym za chwilę | Nie rób nic — alarm wróci za minutę |

### Kolory w tabeli

| Kolor | Znaczenie | Co robić |
|---|---|---|
| 🟢 Zielony | Wszystko działa | Nic |
| 🔴 Czerwony | Jest nowe zdarzenie | Obsłuż incydent w SecureVisio |
| 🟠 Pomarańczowy | Nie da się odczytać środowiska | Sprawdź widok „Incydenty" w tym oknie |
| 🟣 Fioletowy | Zerwane połączenie z serwerem | Kliknij „Pokaż" i „Ponów próbę" w SecureVisio |

### Rodzaje alarmu

| Alarm | Znaczenie | Pilność |
|---|---|---|
| 🔴 NOWE ZDARZENIE | Pojawił się incydent do obsłużenia | Wymaga reakcji |
| 🟠 ŚRODOWISKO ZAMKNIĘTE | Okno SecureVisio zostało zamknięte | Sprawdź, czy to zamierzone |
| 🟣 ZERWANE POŁĄCZENIE | SecureVisio utracił połączenie z serwerem | Kliknij „Pokaż" i ponów próbę w SecureVisio |

> Domyślne kolory alarmów można zmienić w ustawieniach — patrz [Kolory alarmów](#kolory-alarmów). Powyższe kolory to ustawienia fabryczne.

### O czym warto pamiętać

- Uruchomienie programu to **nie to samo** co kliknięcie „Start"
- Okna SecureVisio mogą być zminimalizowane — program i tak je czyta
- Widok „Incydenty" musi być ustawiony w każdym monitorowanym oknie
- Przy pierwszym prawdziwym zdarzeniu sprawdź, czy napis w kolumnie Status zgadza się z ustawieniami
- Wybór koloru alarmu dotyczy tylko trybu pełnoekranowego, nie powiadomień Windows
- Program nie zastępuje obsługi incydentów — tylko informuje, że coś się pojawiło