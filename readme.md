SecureVisio Monitor - Instrukcja użytkownika 

# **SecureVisio Monitor** 

## Instrukcja użytkownika 

_Program pilnuje wszystkich Twoich środowisk SecureVisio i głośno informuje o nowym zdarzeniu_ 

Instrukcja nie wymaga wiedzy programistycznej 

Strona 1 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **Spis treści** 

|Spis treści.....................................................................................................................................................1<br>1. Czym jest ten program............................................................................................................................1|
|---|
|Co program potraf..................................................................................................................................1|
|Czego program nie robi........................................................................................................................... 1|
|Najważniejsza zasada działania...............................................................................................................1|
|2. Co trzeba przygotować............................................................................................................................1|
|Dwie wersje programu............................................................................................................................ 1|
|3. Przygotowanie komputera (tylko wersja źródłowa)................................................................................1|
|Krok 1 - zainstaluj Pythona...................................................................................................................... 1|
|Krok 2 - zainstaluj potrzebne dodatki......................................................................................................1|
|4. Pierwsze uruchomienie i konfguracja.....................................................................................................1|
|Krok 1 - przygotuj SecureVisio.................................................................................................................1|
|Krok 2 - uruchom program......................................................................................................................1|
|Krok 3 - wskaż, gdzie są środowiska........................................................................................................1|
|Krok 4 - uruchom monitorowanie...........................................................................................................1|
|Krok 5 - sprawdź alarm............................................................................................................................1|
|5. Codzienna obsługa...................................................................................................................................1|
|Rozpoczęcie pracy...................................................................................................................................1|
|Co widzisz, gdy pojawi się zdarzenie.......................................................................................................1|
|Zakończenie pracy................................................................................................................................... 1|
|Przyciski w oknie programu.....................................................................................................................1|
|6. Ustawienia...............................................................................................................................................1|
|Ważne: sprawdź frazy przy pierwszym zdarzeniu...................................................................................1|
|Dodanie własnego dźwięku.....................................................................................................................1|
|7. Gdy coś nie działa.................................................................................................................................... 1|
|Środowisko ma stan NIEDOSTĘPNY.........................................................................................................1|
|Tabela jest pusta po kliknięciu Start........................................................................................................1|
|Środowisko zniknęło z tabeli i pojawił się pomarańczowy ekran............................................................1|
|Nie słyszę dźwięku alarmu.......................................................................................................................1|
|Suwak głośności jest szary i nie działa.....................................................................................................1|
|Zdarzenie było, ale alarmu nie było.........................................................................................................1|
|Program w ogóle się nie uruchamia........................................................................................................ 1|



Strona 2 z 19 

|SecureVisio Monitor - Instrukcja użytkownika|
|---|
|8. Gdzie szukać informacji........................................................................................................................... 1|
|Log w oknie programu.............................................................................................................................1|
|Plik z błędami...........................................................................................................................................1|
|Tryb diagnostyczny..................................................................................................................................1|
|9. Aktualizacja programu.............................................................................................................................1|
|10. Wygodniejsze uruchamianie.................................................................................................................1|
|Skrót na pulpicie......................................................................................................................................1|
|Uruchamianie razem z Windows.............................................................................................................1|
|11. Szybka ściąga......................................................................................................................................... 1|
|Codzienny start - 4 kroki..........................................................................................................................1|
|Gdy zabrzmi alarm...................................................................................................................................1|
|Kolory w tabeli.........................................................................................................................................1|
|Kolory ekranów alarmu...........................................................................................................................1|
|Najczęstsza przyczyna problemów..........................................................................................................1|
|O czym warto pamiętać...........................................................................................................................1|



Strona 3 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **1. Czym jest ten program** 

Kiedy pracujesz z kilkoma środowiskami SecureVisio jednocześnie, łatwo przeoczyć moment, w którym w jednym z nich pojawia się nowe zdarzenie. Trzeba pamiętać, żeby regularnie zaglądać do każdego okna po kolei. 

SecureVisio Monitor robi to za Ciebie. Co kilkanaście sekund sprawdza wszystkie środowiska naraz, a gdy pojawi się nowe zdarzenie - wyświetla na wszystkich monitorach duży czerwony ekran i odtwarza sygnał dźwiękowy. 

### **Co program potrafi** 

- Pilnuje jednocześnie wielu środowisk SecureVisio - dowolnej liczby. 

- Działa również wtedy, gdy okna SecureVisio są zminimalizowane lub zasłonięte innymi programami. 

- Nie przeszkadza w pracy - nie przełącza okien i nie zabiera Ci klawiatury. 

- Informuje, którego klienta dotyczy zdarzenie. 

- Pozwala jednym kliknięciem otworzyć na pełnym ekranie to środowisko, w którym coś się wydarzyło. 

- Alarmuje sygnałem dźwiękowym (opcjonalne). 

### **Czego program nie robi** 

- Nie zmienia niczego w systemie SecureVisio - wyłącznie odczytuje. 

- Nie obsługuje incydentów za Ciebie. 

- Nie wysyła powiadomień na telefon ani e-mailem. 

- Nie zapisuje historii zdarzeń. 

### **Najważniejsza zasada działania** 

Program alarmuje w momencie pojawienia się nowego zdarzenia, a nie przez cały czas, gdy ono istnieje. Oznacza to, że dostaniesz jeden alarm na jedno zdarzenie. Jeżeli zdarzenie nie zostanie obsłużone, program przypomni o nim po minucie - chyba że wcześniej klikniesz w ekran alarmu, potwierdzając, że je widzisz. Gdy pojawi się kolejne, nowe zdarzenie, alarm zabrzmi ponownie. 

Strona 4 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **2. Co trzeba przygotować** 

Zanim zaczniesz, upewnij się, że masz wszystko z poniższej listy. 

|**Element**|**Uwagi**|
|---|---|
|Komputer z systemem Windows|Program działa tylko na Windows|
|Zainstalowane środowiska SecureVisio|Te same, których używasz na co dzień|
|Pliki programu SecureVisio Monitor|Przygotowane zgodnie z instrukcją (Folder na wszystkie środowiska)|
|Około 15 minut na pierwsze<br>uruchomienie|Kolejne uruchomienia zajmują kilka sekund|



Nie potrzebujesz uprawnień administratora. Nie potrzebujesz dostępu do internetu - program działa wyłącznie na Twoim komputerze. 

### **Dwie wersje programu** 

Program może być przekazany w jednej z dwóch postaci. Sprawdź, którą masz - od tego zależy, czy wykonujesz rozdział 3. 

|**Co widzisz w katalogu**|**Która to wersja**|**Co zrobić**|
|---|---|---|
|Plik SecureVisioMonitor.exe|Wersja gotowa|Pomiń rozdział 3, przejdź do rozdziału 4|
|Pliki app.py, requirements.txt i<br>inne|Wersja źródłowa|Wykonaj rozdział 3|



Strona 5 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **3. Przygotowanie komputera (tylko wersja źródłowa)** 

Ten rozdział wykonujesz tylko raz i tylko wtedy, gdy w katalogu programu nie ma pliku SecureVisioMonitor.exe. Jeżeli ten plik jest - przejdź od razu do rozdziału 4. 

### **Krok 1 - zainstaluj Pythona** 

Python to program, który jest potrzebny do uruchomienia monitora. Instaluje się go raz. 

1. Otwórz przeglądarkę i wejdź na stronę python.org/downloads 

2. Kliknij duży żółty przycisk pobierania. 

3. Uruchom pobrany plik. 

4. WAŻNE: na pierwszym ekranie instalatora zaznacz pole „Add python.exe to PATH” na dole okna. Bez tego program się nie uruchomi. 

5. Kliknij „Install Now” i poczekaj na zakończenie. 

#### **Sprawdź, czy się udało** 

1. Naciśnij klawisze Windows + R. 

2. Wpisz powershell i naciśnij Enter. 

3. W czarnym oknie wpisz poniższą komendę i naciśnij Enter: 

<mark>python --version</mark> 

- **✔  Powinieneś zobaczyć napis podobny do: Python 3.14.6** 

Jeżeli zamiast tego pojawia się komunikat, że nie rozpoznano polecenia - najprawdopodobniej nie zaznaczyłeś pola „Add python.exe to PATH”. Uruchom instalator ponownie, wybierz opcję zmiany instalacji (Modify) i zaznacz je. 

### **Krok 2 - zainstaluj potrzebne dodatki** 

Program korzysta z kilku dodatkowych komponentów. Pobierzesz je jedną komendą. 

1. Otwórz katalog z plikami programu w Eksploratorze Windows. 

2. Kliknij prawym przyciskiem myszy na pustym miejscu w tym katalogu, trzymając wciśnięty klawisz Shift. 

3. Wybierz „Otwórz okno programu PowerShell tutaj” lub „Otwórz w Terminalu”. 

4. Wklej poniższą komendę i naciśnij Enter: 

<mark>python -m pip install -r requirements.txt</mark> 

5. Poczekaj - instalacja trwa kilka minut i wypisuje dużo tekstu. To normalne. 

- **✔  Na końcu powinien pojawić się napis zaczynający się od: Successfully installed** 

Strona 6 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **4. Pierwsze uruchomienie i konfiguracja** 

### **Krok 1 - przygotuj SecureVisio** 

Zanim uruchomisz monitor, przygotuj środowiska, które ma pilnować. 

1. Uruchom wszystkie środowiska SecureVisio, które chcesz monitorować. 

2. W każdym z nich kliknij pozycję „Incydenty” w menu po lewej stronie. 

To bardzo ważne. Program odczytuje dane z listy incydentów. Jeżeli okno SecureVisio pokazuje mapę sieci albo szczegóły pojedynczego incydentu, monitor nie będzie w stanie nic odczytać z tego środowiska. 

Po ustawieniu widoku możesz spokojnie zminimalizować okna SecureVisio - program czyta je również wtedy, gdy są zminimalizowane. Widok musi być ustawiony w momencie uruchamiania monitorowania. 

### **Krok 2 - uruchom program** 

Zależnie od posiadanej wersji: 

|**Wersja**|**Jak uruchomić**|
|---|---|
|Gotowa|Kliknij dwukrotnie plik SecureVisioMonitor.exe|
|Źródłowa|Kliknij dwukrotnie plik Uruchom.bat|



- **✔  Powinno otworzyć się okno o nazwie „SecureVisio Monitor” z pustą tabelą u góry.** 

Wersja gotowa (.exe) uruchamia się przez kilka sekund - to normalne, plik rozpakowuje się przed startem. Nie klikaj wielokrotnie. 

### **Krok 3 - wskaż, gdzie są środowiska** 

Program musi wiedzieć, gdzie na dysku znajdują się Twoje środowiska SecureVisio, żeby rozpoznać, które okno należy do którego klienta. 

1. Otwórz Eksplorator Windows i znajdź katalog, w którym trzymasz środowiska SecureVisio. 

2. Wejdź o jeden poziom wyżej - tak, żeby widzieć katalogi z nazwami klientów obok siebie. 

3. Kliknij w pasek adresu Eksploratora i skopiuj ścieżkę (Ctrl+C). 

4. Wklej ją w oknie programu w pole „Katalog środowisk”. 

Przykład: jeżeli Twoje środowiska wyglądają tak: 

<mark>C:\SecureVisio\\...</mark> C:\SecureVisio\\... 

C:\SecureVisio\\... 

Strona 7 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

#### to w pole wpisujesz: 

##### <mark>C:\SecureVisio</mark> 

Nazwy klientów, które zobaczysz później na alarmie, biorą się z nazw tych katalogów. W przykładzie powyżej będą to: , , . 

### **Krok 4 - uruchom monitorowanie** 

Kliknij przycisk „Start” na dole okna. 

- **✔  W tabeli powinny pojawić się wiersze - po jednym na każde środowisko - z zielonym tłem i napisem OK.** 

#### Sprawdź, czy wszystko się zgadza: 

|**Kolumna**|**Co powinna pokazywać**|
|---|---|
|Klient|Nazwę środowiska, na przykład |
|Stan|OK na zielonym tle|
|Ostatni odczyt|Aktualną godzinę|
|Incydenty|Liczbę incydentów widoczną na liście w SecureVisio|
|Czas odczytu|Ułamek sekundy, zwykle 0,3-0,7 s|
|Uwagi|Pusto (albo informację o zminimalizowanym oknie)|



Jeżeli któreś środowisko ma stan NIEDOSTĘPNY na pomarańczowym tle - najczęściej oznacza to, że nie jest ustawione na widoku listy incydentów. Wróć do kroku 1, ustaw widok i kliknij „Sprawdź teraz”. 

### **Krok 5 - sprawdź alarm** 

Zanim zdasz się na program, przekonaj się, że alarm działa i jest dla Ciebie widoczny. 

1. Kliknij przycisk „Testuj alarm” w prawym dolnym rogu. 

2. Na wszystkich monitorach powinien pojawić się czerwony ekran z napisem NOWE ZDARZENIE. 

3. Kliknij w dowolne miejsce, żeby go zamknąć. 

- **✔  Alarm pojawił się na każdym monitorze i zniknął po kliknięciu.** 

Sprawdź też dźwięk - kliknij przycisk „Odtwórz” obok listy dźwięków. Kliknij ponownie, żeby przerwać. 

Ustaw głośność tak, żeby alarm był słyszalny również wtedy, gdy odejdziesz od biurka. Jeżeli planujesz dyżur nocny, sprawdź to przy nocnych ustawieniach głośności komputera. 

Strona 8 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **5. Codzienna obsługa** 

### **Rozpoczęcie pracy** 

1. Uruchom środowiska SecureVisio i ustaw w każdym widok „Incydenty”. 

2. Uruchom SecureVisio Monitor. 

3. Kliknij „Start”. 

4. Sprawdź, czy wszystkie środowiska mają stan OK. 

Uruchomienie programu nie rozpoczyna monitorowania automatycznie. Trzeba kliknąć „Start”. Jeżeli tego nie zrobisz, program będzie otwarty, ale nic nie będzie pilnował. 

### **Co widzisz, gdy pojawi się zdarzenie** 

Na wszystkich monitorach wyświetli się czerwony ekran z napisem NOWE ZDARZENIE, a pod nim lista - miejsce zdarzenia i nazwa klienta. Jednocześnie zabrzmi sygnał dźwiękowy. 

Masz dwie możliwości: 

|**Co robisz**|**Co się dzieje**|
|---|---|
|Klikasz w tło ekranu (poza<br>przyciskami)|Alarm znika, dźwięk milknie. Program uznaje, że widziałeś zdarzenie i nie<br>będzie o nim przypominał. Okna SecureVisio pozostają nietknięte.|
|Klikasz przycisk „Pokaż” przy danej<br>pozycji|To środowisko SecureVisio otwiera się na pełnym ekranie, żebyś od razu<br>widział incydent.|
|Nie robisz nic|Alarm znika po 10 sekundach, ale wróci po minucie, dopóki zdarzenie nie<br>zostanie obsłużone.|



Gdy alarm dotyczy kilku środowisk naraz, kliknięcie „Pokaż” przy jednym z nich otwiera to środowisko, a alarm pozostaje widoczny na pozostałych monitorach - możesz zająć się nimi po kolei. 

### **Zakończenie pracy** 

Kliknij „Stop”, żeby wstrzymać monitorowanie, albo zamknij okno programu krzyżykiem - ustawienia zapiszą się automatycznie. 

Zamknięcie programu kasuje pamięć o potwierdzonych zdarzeniach. Po ponownym uruchomieniu nieobsłużone zdarzenia mogą wywołać alarm jeszcze raz. Jeżeli Ci to przeszkadza, odznacz pole „Alarmuj o zdarzeniach zastanych przy starcie”. 

### **Przyciski w oknie programu** 

Strona 9 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

|**Przycisk**|**Do czego służy**|
|---|---|
|Start|Rozpoczyna monitorowanie|
|Stop|Wstrzymuje monitorowanie|
|Sprawdź teraz|Sprawdza wszystkie środowiska natychmiast, bez czekania|
|Testuj alarm|Pokazuje przykładowy alarm - do sprawdzenia widoczności|
|Dodaj plik...|Dodaje własny dźwięk alarmu|
|Odtwórz|Odtwarza wybrany dźwięk, żebyś mógł go posłuchać|



Strona 10 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **6. Ustawienia** 

Wszystkie ustawienia znajdują się w środkowej części okna i zapisują się automatycznie. 

|**Ustawienie**|**Co oznacza**|**Kiedy zmieniać**|
|---|---|---|
|Katalog środowisk|Miejsce na dysku, gdzie trzymasz<br>środowiska SecureVisio|Gdy przeniesiesz środowiska w inne<br>miejsce|
|Frazy nowego zdarzenia|Napisy w kolumnie Status, na które<br>program ma reagować|Gdy Twoje SecureVisio używa innego<br>napisu (patrz niżej)|
|Interwał|Co ile sekund program sprawdza<br>środowiska|Rzadko - domyślne 30 s jest<br>bezpieczne|
|Alarm widoczny|Ile sekund wyświetla się czerwony ekran|Gdy 10 sekund to dla Ciebie za krótko<br>lub za długo|
|Przypomnienie po|Po ilu sekundach alarm wraca, jeśli go nie<br>potwierdzisz|Gdy chcesz częstsze lub rzadsze<br>przypomnienia|
|Alarmuj o zdarzeniach<br>zastanych|Czy alarmować o zdarzeniach istniejących<br>już przy starcie|Odznacz, jeśli restart programu ma nie<br>powtarzać alarmów|
|Tryb diagnostyczny|Zapisuje szczegółowe informacje do pliku|Tylko gdy szukasz przyczyny problemu|
|Dźwięk alarmu|Włącza sygnał dźwiękowy i pozwala<br>wybrać plik|Odznacz, gdy pracujesz w ciszy|
|Głośność|Głośność sygnału względem głośności<br>systemu|Ustaw raz, na początku|



### **Ważne: sprawdź frazy przy pierwszym zdarzeniu** 

Program szuka w kolumnie Status napisów „Nowe Zdarzenie” oraz „New Event”. Nie zostało potwierdzone, że Twoja wersja SecureVisio używa dokładnie takich napisów. Przy pierwszym prawdziwym incydencie porównaj napis w kolumnie Status z tym, co masz wpisane w polu „Frazy nowego zdarzenia”. Jeżeli się różnią - dopisz właściwy napis, oddzielając go średnikiem. 

Przykład, gdy Twoje SecureVisio pokazuje status „Nowy”: 

<mark>Nowe Zdarzenie; New Event; Nowy</mark> 

Po zmianie kliknij „Stop”, a następnie „Start”, żeby ustawienie zaczęło obowiązywać. 

### **Dodanie własnego dźwięku** 

1. Przygotuj plik dźwiękowy w formacie WAV (inne formaty nie są obsługiwane). 

2. Kliknij „Dodaj plik...” i wskaż go. 

3. Plik zostanie skopiowany do programu i pojawi się na liście. 

4. Wybierz go z listy i kliknij „Odtwórz”, żeby sprawdzić. 

Strona 11 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

<mark>Plik jest kopiowany do programu, więc możesz spokojnie usunąć oryginał - alarm będzie działał dalej.</mark> 

Strona 12 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **7. Gdy coś nie działa** 

### **Środowisko ma stan NIEDOSTĘPNY** 

_Co widzisz: Wiersz w tabeli jest pomarańczowy, w kolumnie Uwagi widnieje komunikat o błędzie._ 

Dlaczego: Najczęściej to okno SecureVisio nie jest ustawione na widoku listy incydentów. Program nie ma wtedy skąd odczytać danych. 

#### **Co zrobić** 

1. Przejdź do tego okna SecureVisio. 

2. Kliknij „Incydenty” w menu po lewej stronie. 

3. Wróć do monitora i kliknij „Sprawdź teraz”. 

- **✔  Wiersz zmienia kolor na zielony, a stan na OK.** 

### **Tabela jest pusta po kliknięciu Start** 

_Co widzisz: Po uruchomieniu monitorowania nie pojawia się żaden wiersz, a pod tabelą widnieje „Monitorowane: 0/0”._ 

Dlaczego: Program nie rozpoznał żadnego okna SecureVisio. Zwykle oznacza to źle wpisany katalog środowisk. 

#### **Co zrobić** 

1. Sprawdź, czy środowiska SecureVisio są w ogóle uruchomione. 

2. Sprawdź pole „Katalog środowisk” - musi wskazywać katalog NADRZĘDNY, w którym leżą katalogi klientów, a nie katalog jednego klienta. 

3. Popraw ścieżkę, kliknij „Stop”, a potem „Start”. 

- **✔  W tabeli pojawiają się wiersze wszystkich środowisk.** 

### **Środowisko zniknęło z tabeli i pojawił się pomarańczowy ekran** 

_Co widzisz: Ekran z napisem ŚRODOWISKO ZAMKNIĘTE i nazwą klienta._ 

Dlaczego: Okno SecureVisio zostało zamknięte lub przestało odpowiadać. Program informuje, że przestał je pilnować. 

#### **Co zrobić** 

1. Kliknij w ekran, żeby go zamknąć. 

2. Jeżeli zamknąłeś to środowisko celowo - nic więcej nie musisz robić. 

3. Jeżeli nie - uruchom SecureVisio ponownie, ustaw widok „Incydenty”. Program sam je wykryje i wznowi monitorowanie. 

- **✔  W polu „Log bieżący” pojawia się wpis, że środowisko wróciło.** 

Strona 13 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

### **Nie słyszę dźwięku alarmu** 

_Co widzisz: Czerwony ekran się pojawia, ale bez dźwięku._ 

Dlaczego: Dźwięk może być wyłączony w programie, wyciszony w systemie albo ustawiony na zbyt niski poziom. 

#### **Co zrobić** 

1. Sprawdź, czy pole „Dźwięk alarmu” jest zaznaczone. 

2. Kliknij „Odtwórz” - jeżeli nic nie słychać, problem jest w dźwięku, nie w alarmie. 

3. Sprawdź głośność systemu Windows (ikona głośnika przy zegarze) i mikser głośności. 

4. Przesuń suwak głośności w programie w prawo. 

- **✔  Po kliknięciu „Odtwórz” słychać sygnał alarmowy.** 

### **Suwak głośności jest szary i nie działa** 

_Co widzisz: Obok suwaka widnieje napis „sys.” zamiast wartości procentowej._ 

Dlaczego: Brakuje komponentu odpowiedzialnego za regulację głośności. Dźwięk działa, ale sterujesz nim głośnością systemu. 

#### **Co zrobić** 

1. Steruj głośnością przez ikonę głośnika w Windows - to w pełni wystarcza. 

2. Jeżeli chcesz przywrócić suwak, zgłoś to osobie, która przekazała Ci program. 

- **✔  Dźwięk alarmu jest słyszalny na odpowiednim poziomie.** 

### **Zdarzenie było, ale alarmu nie było** 

_Co widzisz: W SecureVisio widać nowe zdarzenie, monitor pokazywał OK i nie zaalarmował._ 

Dlaczego: Najprawdopodobniej Twoje SecureVisio używa innego napisu statusu niż ten wpisany w ustawieniach programu. 

#### **Co zrobić** 

1. Otwórz SecureVisio i przepisz dokładnie napis z kolumny Status dla tego zdarzenia. 

2. Porównaj go z zawartością pola „Frazy nowego zdarzenia” w monitorze. 

3. Jeżeli się różnią, dopisz właściwy napis po średniku. 

4. Kliknij „Stop”, a potem „Start”. 

- **✔  Przy kolejnym zdarzeniu alarm pojawia się poprawnie.** 

### **Program w ogóle się nie uruchamia** 

_Co widzisz: Podwójne kliknięcie nic nie daje albo pojawia się i znika czarne okno._ 

Dlaczego: W wersji źródłowej zwykle oznacza to brak Pythona lub niezainstalowane dodatki. 

Strona 14 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

#### **Co zrobić** 

1. Sprawdź, czy wykonałeś oba kroki z rozdziału 3. 

2. Otwórz PowerShell w katalogu programu i uruchom go tak, żeby zobaczyć komunikat błędu: 

<mark>python app.py</mark> 

3. Zanotuj treść błędu i przekaż ją osobie, która udostępniła Ci program. 

- **✔  Otwiera się okno „SecureVisio Monitor”.** 

Strona 15 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **8. Gdzie szukać informacji** 

### **Log w oknie programu** 

Pole „Log bieżący” na dole okna pokazuje, co program robił: kiedy wykrył zdarzenie, kiedy je potwierdziłeś, kiedy środowisko zniknęło lub wróciło. To pierwsze miejsce, do którego warto zajrzeć. 

Log czyści się przy zamknięciu programu - jeżeli chcesz coś zachować, zaznacz tekst i skopiuj. 

### **Plik z błędami** 

Program zapisuje błędy do pliku: 

<mark>logs\monitor.log</mark> 

Znajdziesz go w katalogu programu. Otwórz go Notatnikiem. 

Pusty plik albo jego brak to dobra wiadomość - oznacza, że nie wystąpił żaden błąd. Program zapisuje tam wyłącznie problemy, a nie normalną pracę. 

### **Tryb diagnostyczny** 

Gdy trzeba zbadać problem dokładniej, zaznacz pole „Tryb diagnostyczny (szczegółowe logi)”. Program zacznie zapisywać znacznie więcej informacji. 

Po zakończeniu diagnostyki odznacz to pole. W trybie diagnostycznym do pliku trafiają także dane incydentów - ich numery i statusy - a plik szybko się zapełnia. 

## **9. Aktualizacja programu** 

Program nie aktualizuje się sam. Gdy otrzymasz nową wersję: 

1. Zamknij program. 

2. Zrób kopię pliku settings.json z katalogu programu - zawiera Twoje ustawienia. Wystarczy skopiować go na pulpit. 

3. Jeżeli masz własne dźwięki, skopiuj też katalog sounds. 

4. Zastąp pliki programu nowymi. 

5. Uruchom program i sprawdź, czy ustawienia są na miejscu. 

Ustawienia zwykle zachowują się same, bo plik settings.json nie jest nadpisywany przez nową wersję. Kopia to zabezpieczenie na wszelki wypadek. 

## **10. Wygodniejsze uruchamianie** 

### **Skrót na pulpicie** 

Strona 16 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

1. Znajdź plik, którym uruchamiasz program (SecureVisioMonitor.exe lub Uruchom.bat). 

2. Kliknij go prawym przyciskiem myszy. 

3. Wybierz „Pokaż więcej opcji”, a następnie „Wyślij do” → „Pulpit (utwórz skrót)”. 

- **✔  Na pulpicie pojawia się skrót, którym uruchomisz program jednym dwuklikiem.** 

### **Uruchamianie razem z Windows** 

1. Naciśnij Windows + R. 

2. Wpisz shell:startup i naciśnij Enter. 

3. Przeciągnij do otwartego katalogu skrót do programu. 

Program uruchomi się sam po zalogowaniu, ale nadal trzeba kliknąć „Start”, żeby rozpocząć monitorowanie. Automatyczne rozpoczynanie nie jest dostępne. 

Strona 17 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

## **11. Szybka ściąga** 

### **Codzienny start - 4 kroki** 

1. Uruchom środowiska SecureVisio. 

2. W każdym kliknij „Incydenty”. 

3. Uruchom SecureVisio Monitor. 

4. Kliknij „Start” i sprawdź, czy wszystkie wiersze są zielone. 

### **Gdy zabrzmi alarm** 

|**Chcesz...**|**Zrób to**||
|---|---|---|
|Zobaczyć incydent|od razu<br>Kliknij „Pokaż” przy o|dpowiedniej pozycji|
|Tylko zamknąć ala|rm<br>Kliknij w tło ekranu, p|oza przyciskami|
|Zająć się tym za ch|wilę<br>Nie rób nic - alarm wr|óci za minutę|
|**Kolory w ta**<br>**Kolor**|**beli**<br>**Znaczenie**|**Co robić**|
|Zielony|Wszystko działa|Nic|
|Czerwony|Jest nowe zdarzenie|Obsłuż incydent w SecureVisio|
|Pomarańczowy|Nie da się odczytać środowiska|Sprawdź widok „Incydenty” w tym oknie|



### **Kolory w tabeli** 

### **Kolory ekranów alarmu** 

|**Ekran**|**Znaczenie**|**Pilność**|
|---|---|---|
|Czerwony - NOWE ZDARZENIE|Pojawił się incydent do obsłużenia|Wymaga reakcji|
|Pomarańczowy - ŚRODOWISKO<br>ZAMKNIĘTE|Okno SecureVisio zostało zamknięte|Sprawdź, czy to<br>zamierzone|



### **Najczęstsza przyczyna problemów** 

**Jeżeli coś nie działa, w dziewięciu przypadkach na dziesięć któreś okno SecureVisio nie jest ustawione na widoku listy incydentów. Sprawdź to najpierw.** 

### **O czym warto pamiętać** 

Strona 18 z 19 

SecureVisio Monitor - Instrukcja użytkownika 

- Uruchomienie programu to nie to samo co kliknięcie „Start”. 

- Okna SecureVisio mogą być zminimalizowane - program i tak je czyta. 

- Widok „Incydenty” musi być ustawiony w każdym monitorowanym oknie. 

- Przy pierwszym prawdziwym zdarzeniu sprawdź, czy napis w kolumnie Status zgadza się z ustawieniami. 

- Program nie zastępuje obsługi incydentów - tylko informuje, że coś się pojawiło. 

Strona 19 z 19 

