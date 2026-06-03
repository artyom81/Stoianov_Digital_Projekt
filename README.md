<h1 align="center">Freies Digitales Projekt</h1>
<br>
<p align="center">
  <strong>Artem Stoianov</strong><br>
  Julius-Maximilians-Universität Würzburg · Philosophische Fakultät · Digital Humanities<br>
  Sommersemester 2026 · Stand: Juni 2026
</p>
<br>
<p align="center">
  <strong>Aufbau, Erschließung und prototypische Suchbereitstellung eines Korpus russischsprachiger Diskmags auf Grundlage von ZXpress</strong>
</p>
<br>
<p align="center">
  <a href="#inhalt">Inhalt</a> •
  <a href="#überblick">Überblick</a> •
  <a href="#projektstruktur">Projektstruktur</a> •
  <a href="#prüfwege">Prüfwege</a> •
  <a href="#zusätzliche-skripte">Zusätzliche Skripte</a>
</p>

<p align="center">
  <img alt="Status Korpus" src="https://img.shields.io/badge/Korpus-vorhanden-2ea44f">
  <img alt="Status Lucene" src="https://img.shields.io/badge/Lucene-lokal%20testbar-2ea44f">
  <img alt="Status Endpoint" src="https://img.shields.io/badge/FCS%2FSRU-prototypisch-f0ad4e">
  <img alt="Status Validator" src="https://img.shields.io/badge/Validator-nicht%20vollständig%20konform-d9534f">
</p>

---

## Inhalt

- [Überblick](#überblick)
- [Projektstruktur](#projektstruktur)
  - [Grundstruktur des Korpus](#grundstruktur-des-korpus)
  - [Zentrale Verzeichnisse](#zentrale-verzeichnisse)
- [Voraussetzungen](#voraussetzungen)
- [Lokale und harte Pfade](#lokale-und-harte-pfade)
- [Prüfwege](#prüfwege)
  - [Prüffall A: Endzustand direkt prüfen](#prüffall-a-endzustand-direkt-prüfen)
  - [Prüffall B: Verarbeitung ohne neues Korpusziehen](#prüffall-b-verarbeitung-ohne-neues-korpusziehen)
  - [Prüffall C: Neuaufbau mit Scraper in Testumgebung](#prüffall-c-neuaufbau-mit-scraper-in-testumgebung)
- [Zusätzliche Skripte](#zusätzliche-skripte)
- [Tipps für Webquelle und weitere Forschung](#tipps-für-webquelle-und-weitere-forschung)

---

## Überblick

Dieses Repository dokumentiert technische Schritte der Bereitstellung eines Korpus russischsprachiger Diskmags auf Grundlage der Website <a href="https://zxpress.ru/ezines.php">zxpress.ru</a>

Das ausführliche Projektprotokoll ist hier abgelegt:[Stoianov_Protokoll_Groß.pdf](Stoianov_Protokoll_Groß.pdf)

Die vier praktischen Hauptbereiche sind:

- Korpusaufbau und Korpusspeicherung
- Bereinigung, Validierung und Audit
- Lokale Volltextsuche mit Lucene
- Prototypische FCS-/SRU-Bereitstellung

Das Repository ist ein gewachsener Projektstand. Entsprechend sind einige Komponenten stabil und gut prüfbar, andere experimentell oder unvollständig abgeschlossen.

> **Am schnellsten prüfbar sind:**  
> der lokal vorliegende Korpus, die Strukturprüfung, der Katalogbau, die Indexierung und die lokale Lucene-Suche.

> **Status des FCS-/SRU-Teils:**  
> prototypisch; lokal und über ngrok getestet, aber nicht vollständig validator-konform abgeschlossen.

### Ziel des Repositories

Das Repository soll für die Prüfung drei Dinge ermöglichen:

1. den abgegebenen Endzustand direkt nachzuvollziehen
2. die lokale Verarbeitungskette ohne erneutes Korpusziehen zu testen
3. auf Wunsch auch einen scraper-basierten Neuaufbau in einer Testumgebung nachzuvollziehen

Dafür gibt es in diesem README drei getrennte Prüfwege.

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

## Projektstruktur

Der Korpus ist hierarchisch aufgebaut: **Magazin → Ausgaben → Artikel → Volltext**.  
Zusätzlich existieren JSON-Metadaten auf mehreren Ebenen, damit der Bestand als strukturierter Forschungskorpus nutzbar ist.

Die Grundidee lautet:

- **Magazin-Ebene** = allgemeine Informationen zu einem Periodikum
- **Issue-Ebene** = Informationen zu einer konkreten Ausgabe
- **Artikel-Ebene** = Volltext und Metadaten eines einzelnen Artikels

---

> **Wichtig!**
> Das Korpus bildet Publikationsfolge der **Ausgaben/Issues** von <a href="https://zxpress.ru/ezines.php">zxpress.ru/ezines.php</a> chronologisch von **oben nach unten** ab;
> Auf der Webseite selbst werden diese aber **von unten nach oben** gemacht. D.h. die **ältere bzw. erste** Ausgabe des Magazins wird ganz unten in der Liste stehen!

### Grundstruktur des Korpus

```text
data/
└── zxpress/
    └── magazines/
        ├── <Magazin_A>/
        │   ├── magazine.json
        │   ├── listing.json
        │   └── issues/
        │       ├── <Issue_1>/
        │       │   ├── issue.json
        │       │   ├── listing.json
        │       │   └── articles/
        │       │       ├── <Artikel_1>/
        │       │       │   ├── meta.json
        │       │       │   └── text.txt
        │       │       ├── <Artikel_2>/
        │       │       │   ├── meta.json
        │       │       │   └── text.txt
        │       │       └── ...
        │       ├── <Issue_2>/
        │       └── ...
        ├── <Magazin_B>/
        └── ...
```
<br>
<details>
<summary><strong>Magazin-, Issue- und Artikel-Ebene anzeigen</strong></summary>

#### 1. Magazin-Ebene

Diese Ebene beschreibt ein gesamtes Magazin oder Periodikum.

- **`magazine.json`**: zentrale Metadatenquelle für das Magazin als Ganzes
- **`listing.json`**: magazinweites Issue-Verzeichnis

#### 2. Issue-Ebene

**Benennung des Issue-Ordners**

```text
<issue_label>_<issue_date_iso>
```

Diese Ebene beschreibt eine konkrete Ausgabe eines Magazins.

- **`issue.json`**: Metadaten zur Ausgabe
- **`listing.json`**: Liste der Artikel dieser Ausgabe

#### 3. Artikel-Ebene

**Benennung des Artikelordners**

```text
<Reihenfolge>_<Artikel-ID>_<Kurzslug>
```

Beispiel:

```text
01_12345_Beispielartikel
```

Diese Ebene enthält den eigentlichen Forschungsinhalt:

- **`meta.json`**: Metadaten eines einzelnen Artikels
- **`text.txt`**: gespeicherter Volltext

`text.txt` ist zentral für:

- Volltextsuche
- Indexierung
- KWIC-Ausgabe
- spätere Forschungsauswertung

**Beispiel eines vollständigen Pfads**

```text
data/zxpress/magazines/Z80/issues/01_1996-04-14/articles/01_12345_Beispielartikel/text.txt
```

- `Z80` = Magazin
- `01_1996-04-14` = Ausgabe
- `01_12345_Beispielartikel` = Artikel

</details>

---

### Zentrale Verzeichnisse

| Pfad | Inhalt | Rolle |
|---|---|---|
| `data/` | bereits befüllter Hauptkorpus | zentral |
| `data_small/` | kleinerer Teilbestand für Kurztests | optional |
| `_catalog/` | CSV-Kataloge des Korpus | wichtig für Indexer |
| `index_dir/` | Lucene-Index | zentral für Searcher |
| `logs/` | Prüf- und Diagnoseergebnisse | zentral |
| `scripts/light/` | Korpusaufbau, Bereinigung, Audit | zentral |
| `scripts/TextSearch/` | Indexer und Searcher | zentral |
| `scripts/TextSearch/_tools/` | Prüfwerkzeuge für den Index | zentral |
| `scripts/FCS/` | erster FCS-/SRU-Prototyp | prototypisch |
| `scripts/FCS_Server/` | zweiter Endpoint-Versuch | dokumentiert, nicht primärer Prüfpfad |
<br>
<details>
<summary><strong>Wichtige Log-Dateien anzeigen</strong></summary>

### `logs/validation/`
Einzelne Validierungsprotokolle pro Magazin.

### `logs/health/`
Struktur- und Audit-Logs des Korpus.

Wichtige Dateien:

- `issues_missing.log`: Issues mit fehlender `issue.json`, `listing.json` oder fehlendem `articles/`
- `articles_missing.log`: Artikelordner mit fehlender `meta.json` oder `text.txt`
- `placeholders_0000-01-01.log`: Issues mit Platzhalterdatum `0000-01-01`
- `magazines_empty.log`: Magazine ohne Issues oder mit fehlendem `issues/`
- `audit_summary.csv`: Gesamttabelle des Audit-Laufs
- `audit_problematic_magazines.csv` und `.log`: problematische Magazine zur manuellen Sichtung
- `audit_stdout.log`: Konsolenausgabe des Audit-Laufs
- `summary.txt`: Hauptzusammenfassung des Health-Checks

### `logs/textsearch/`
Logs für die Suchschicht.

- `full_healthcheck.txt`: Zusammenfassung des TextSearch-Healthchecks

</details>

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

## Voraussetzungen

### Python

Im Projektverlauf wurde mit **Python 3.11.13** gearbeitet.

```bash
python3 --version
which python
which python3
```

### Java

Für Lucene, Indexer, Searcher und Endpoint wurde **Java 21** verwendet.

```bash
java -version
```

### Abhängigkeiten

Für Scraper und Light-Skripte:

```bash
pip install -r requirements-scraper.txt
```

Für Suche, Lucene und Endpoint:

```bash
pip install -r requirements.txt
```

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

## Lokale und harte Pfade

Einige Skripte enthalten harte lokale Pfade und müssen auf eigenem Rechner angepasst werden.

### Harte Pfade

| Datei | Stelle | Hinweis |
|---|---|---|
| `scripts/FCS/fcs_endpoint.py` | `INDEX_DIR`, `CONFIG_PATH` | vor Endpoint-Test anpassen |
| `scripts/light/repair_psychoz_12.py` | `MAG` | Spezialskript für Einzelfall |
<br>
`scripts/FCS/fcs_endpoint.py`

```python
INDEX_DIR = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"
CONFIG_PATH = "/Users/stoia1/Desktop/Website/DigitProject/config/zxpress.yaml"
```

`scripts/light/repair_psychoz_12.py`

```python
MAG = "data/zxpress/magazines/Psychoz"
```

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

## Prüfwege

---

### Prüffall A: Endzustand direkt prüfen

> **Ziel:** vorhandenen Projektstand direkt ansehen und benutzen  
> **Geeignet für:** schnelle Prüfung ohne Neuaufbau

#### Wichtige Bestände zum Untersuchen

**1. Korpus ansehen**
- `data/`
- `data_small/`

**2. Katalog ansehen**
- `_catalog/magazines.csv`
- `_catalog/issues.csv`
- `_catalog/articles.csv`

**3. Logs ansehen**
- `logs/health/summary.txt`
- `logs/health/audit_problematic_magazines.log`
- `logs/textsearch/full_healthcheck.txt`
- einzelne Dateien in `logs/validation/`

**4. Index**
- `index_dir/`

#### TextSearch-Healthcheck

```bash
python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir"
```

Wenn dieser Schritt erfolgreich ist, ist der vorhandene Index lesbar und der Searcher lokal nutzbar.

#### Lokale Suche testen

```bash
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "спектрум" --limit 3
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "covox OR ковокс" --limit 3
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "игра" --year-from 1995 --year-to 1997 --limit 3
```

#### Endpoint lokal starten

Vorher harte Pfade in `scripts/FCS/fcs_endpoint.py` prüfen.

```bash
python scripts/FCS/fcs_endpoint.py
```

Dann lokal testen:

```bash
curl -i "http://127.0.0.1:8088/health"
curl -i "http://127.0.0.1:8088/sru?operation=explain&version=2.0"
curl -i "http://127.0.0.1:8088/sru?x-fcs-endpoint-description=true"
curl -i "http://127.0.0.1:8088/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

#### ngrok verwenden

Voraussetzung: Der Endpoint läuft bereits lokal.

1. Account bei ngrok anlegen  
2. ngrok installieren  
3. Auth-Token setzen, falls nötig  

Tunnel starten:

```bash
ngrok http 8088
```

Danach zeigt ngrok eine öffentliche URL an, z. B.:

```text
https://<ihre-adresse>.ngrok-free.dev
```

#### Endpoint über ngrok testen

```bash
curl -i "https://<ihre-adresse>.ngrok-free.dev/health"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=explain&version=2.0"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?x-fcs-endpoint-description=true"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

#### Validator reproduzieren

Validator: <a href="https://fcs-validator.data.saw-leipzig.de/">https://fcs-validator.data.saw-leipzig.de/</a>

Eintragen:

- Endpoint BaseURL: `https://<ihre-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум` (`spectrum`)

Dann `Evaluate` starten.

> **Wichtig:** Der Validatorfehler ist reproduzierbar und gehört zum dokumentierten Projektstand.

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

### Prüffall B: Verarbeitung ohne neues Korpusziehen

> **Ziel:** vorhandenen Korpus neu prüfen und verarbeiten, ohne ihn neu zu scrapen  
> **Geeignet für:** technische Nachvollziehbarkeit ohne Netzrisiko

#### Vorher löschen

Nur generierte Artefakte löschen:

```bash
rm -rf _catalog
rm -rf index_dir
rm -rf logs/health
rm -rf logs/validation
rm -rf logs/textsearch
```

#### Schritt 1: Health-Check mit Audit

```bash
bash scripts/light/health_zxpress.sh data/zxpress/magazines logs/health logs/validation
```

Dabei werden geprüft:

- Struktur des Korpus
- fehlende Issue-Dateien
- fehlende Artikeldateien
- Platzhalterdaten
- leere Magazine
- Audit-Zusammenfassung

> **Hinweis:** `health_zxpress.sh` nutzt vorhandene Validierungslogs in `logs/validation`, wenn diese existieren.  
> Neue Validierungslogs müssen separat über `validate_corpus.py` oder automatisch über die Scraper-Pipeline erzeugt werden.

#### Schritt 2: Katalog bauen

```bash
python scripts/light/build_catalog.py --root "data/zxpress" --out "_catalog"
```

Ergebnis:

- `_catalog/magazines.csv`
- `_catalog/issues.csv`
- `_catalog/articles.csv`

#### Schritt 3: Index neu bauen

**Legacy-Modus**

```bash
python scripts/TextSearch/Indexer.py \
  --data-root "data/zxpress/magazines" \
  --index-dir "index_dir"
```

**Katalogmodus**

```bash
python scripts/TextSearch/Indexer.py \
  --from-catalog \
  --catalog-articles "_catalog/articles.csv" \
  --data-root "data/zxpress" \
  --index-dir "index_dir"
```

#### Schritt 4: TextSearch-Healthcheck

```bash
python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir"
```

#### Schritt 5: Searcher testen

```bash
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "спектрум" --limit 3
```

#### Schritt 6: Endpoint lokal testen

Vorher harte Pfade in `scripts/FCS/fcs_endpoint.py` prüfen.

```bash
python scripts/FCS/fcs_endpoint.py
```

```bash
curl -i "http://127.0.0.1:8088/health"
curl -i "http://127.0.0.1:8088/sru?operation=explain&version=2.0"
curl -i "http://127.0.0.1:8088/sru?x-fcs-endpoint-description=true"
curl -i "http://127.0.0.1:8088/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

#### Schritt 7: ngrok + Validator

```bash
ngrok http 8088
```

```bash
curl -i "https://<ihre-adresse>.ngrok-free.dev/health"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=explain&version=2.0"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?x-fcs-endpoint-description=true"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

Validator: <a href="https://fcs-validator.data.saw-leipzig.de/">https://fcs-validator.data.saw-leipzig.de/</a>

- Endpoint BaseURL: `https://<ihre-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум` (`spectrum`)
- `Evaluate` starten

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

### Prüffall C: Neuaufbau mit Scraper in Testumgebung

> **Ziel:** kompletten Neuaufbau in separater Teststruktur durchführen  
> **Geeignet für:** vollständige Reproduktion mit externer Quelle

#### Empfohlene Teststruktur

- `data_test/`
- `_catalog_test/`
- `index_dir_test/`

#### Vorher löschen

```bash
rm -rf data_test
rm -rf _catalog_test
rm -rf _catalog
rm -rf index_dir_test
rm -rf index_dir
rm -rf logs/health
rm -rf logs/validation
rm -rf logs/textsearch
```

#### WebScraper Pipeline-Modi

##### Single-Run

Ein einzelnes Magazin:

Auf <a href="https://zxpress.ru/ezines.php">zxpress.ru/ezines.php</a> nach Link des Magazins mit ID suchen; als Output unter `magazines/` einen passenden Magazinordnernamen ohne problematische Sonderzeichen verwenden.

```bash
python scripts/light/run_light_pipeline.py \
  --mode single \
  --mag-url "https://zxpress.ru/issue.php?id=1" \
  --out-root "data_test/zxpress/magazines/Z80" \
  --validate
```

##### All-Run

Kompletter ZXPress-Katalog von `ezines.php`:

```bash
python scripts/light/run_light_pipeline.py \
  --mode all \
  --config "config/zxpress.yaml" \
  --root "data_test/zxpress/magazines" \
  --validate
```
<br>
<details>
<summary><strong>Hinweise zum All-Run</strong></summary>

- `--mode all` verarbeitet den Webkatalog vollständig
- ein kompletter Lauf kann über eine Stunde benötigen
- Dauer und Erfolg hängen von Netzverbindung und Quellverfügbarkeit ab

</details>

#### Was die Pipeline intern macht

Die Pipeline ruft mehrere Skripte unter `scripts/light/` nacheinander auf.  
Damit passiert eine erste Bereinigung bereits im Pipeline-Lauf. Danach sollte trotzdem immer noch ein `health_zxpress.sh`-Lauf folgen.

#### Nach dem Lauf

##### Schritt 1: Health-Check

```bash
bash scripts/light/health_zxpress.sh data_test/zxpress/magazines logs/health logs/validation
```

##### Schritt 2: Katalog bauen

```bash
python scripts/light/build_catalog.py --root "data_test/zxpress" --out "_catalog_test"
```

##### Schritt 3: Index bauen

```bash
python scripts/TextSearch/Indexer.py \
  --from-catalog \
  --catalog-articles "_catalog_test/articles.csv" \
  --data-root "data_test/zxpress" \
  --index-dir "index_dir_test"
```

##### Schritt 4: TextSearch-Healthcheck

```bash
python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir_test"
```

##### Schritt 5: Searcher testen

```bash
python scripts/TextSearch/Searcher.py --index-dir "index_dir_test" --q "спектрум" --limit 3
```

##### Schritt 6: Endpoint

Falls der Endpoint mit Testdaten geprüft werden soll, müssen die harten Pfade in `scripts/FCS/fcs_endpoint.py` angepasst werden.

```bash
python scripts/FCS/fcs_endpoint.py
```

```bash
curl -i "http://127.0.0.1:8088/health"
curl -i "http://127.0.0.1:8088/sru?operation=explain&version=2.0"
curl -i "http://127.0.0.1:8088/sru?x-fcs-endpoint-description=true"
curl -i "http://127.0.0.1:8088/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

##### Schritt 7: ngrok + Validator

```bash
ngrok http 8088
```

```bash
curl -i "https://<ihre-adresse>.ngrok-free.dev/health"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=explain&version=2.0"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?x-fcs-endpoint-description=true"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

Validator: <a href="https://fcs-validator.data.saw-leipzig.de/">https://fcs-validator.data.saw-leipzig.de/</a>

- Endpoint BaseURL: `https://<ihre-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум` (`spectrum`)
- `Evaluate` starten

<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>

---

## Zusätzliche Skripte

**`scripts/light/validate_corpus.py`**: validiert ein einzelnes Magazin

**Beispiel**

```bash
python scripts/light/validate_corpus.py --mag-root "data/zxpress/magazines/Psychoz"
```

## Tipps für Webquelle und weitere Forschung

Auf den Magazinebenen kann man Magazinarchive für Start in Emulator herunterladen. Die Option heißt: "Скачать архив газеты для запуска в эмуляторе".

Auf den Artikelebenen können einzelne Artikel ins Druckansicht überführt oder als .txt heruntergeladen werden.

In der rechten Leistenmenü sind häufige Themen der Artikel aufgelistet: "Темы", z.B. Spiele, Software, Demoszene.

Oben rechts gibt es mehrere Weiterleitungen:
  - "Пресса" sind Magazine, die in diesem Projekt bearbeitet wurden;
  - "Книги" sind Bücher, die dem Thema ZX Spectrum gewidmet sind;
  - "Письма" sind Papierbriefe von Teilnehmer der ZX Spectrum Szene;
  - „ZXNet“ archiviert Echo-Konferenzen eines nichtkommerziellen ZX-Spectrum-Netzwerks, also historische thematische Nachrichten- und Diskussionsbestände der Szene.

Im selben Navigationsbereich befinden sich außerdem die Seiten:

„Хронология“ bietet eine zeitliche Übersicht der Zeitungen und Magazine, inklusive Jahresgrafik und detaillierter Ausgabenliste.

„Статистика“ fasst quantitative Informationen zum Archiv zusammen, etwa Artikelzahlen, Screenshots, Umfang des Pressearchivs, besonders gelesene Artikel sowie langlebige Magazine und Zeitungen.


<p align="right"><a href="#inhalt">↑ Zurück zum Inhalt</a></p>
