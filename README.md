# Stoianov Digital Project

## Inhalt

- [Überblick](#überblick)
- [Projektstruktur](#projektstruktur)
  - [Grundstruktur](#grundstruktur)
  - [Zentrale Verzeichnisse](#zentrale-verzeichnisse)
- [Voraussetzungen](#voraussetzungen)
- [Lokale und harte Pfade](#lokale-und-harte-pfade)
- [Prüfwege](#prüfwege)
  - [Prüffall A: Endzustand direkt prüfen](#prüffall-a-endzustand-direkt-prüfen)
  - [Prüffall B: Verarbeitung ohne neues Korpusziehen](#prüffall-b-verarbeitung-ohne-neues-korpusziehen)
  - [Prüffall C: Neuaufbau mit Scraper in Testumgebung](#prüffall-c-neuaufbau-mit-scraper-in-testumgebung)
- [Zusätzliche Skripte](#zusätzliche-skripte)

---

## Überblick

Dieses Repository dokumentiert Aufbau, Bereinigung, Validierung, Indexierung und prototypische Bereitstellung eines Korpus russischsprachiger ZX-Spectrum Diskmags auf Grundlage von Webseite zxpress: https://zxpress.ru

Die vier praktischen Hauptbereiche sind:

1. Korpusaufbau und Korpusspeicherung  
2. Bereinigung, Validierung und Audit  
3. Lokale Volltextsuche mit Lucene  
4. Prototypische FCS-/SRU-Bereitstellung  

Das Repository ist ein gewachsener Projektstand. Entsprechend sind einige Komponenten stabil und gut prüfbar, andere experimentell oder unvollständig abgeschlossen.

**Am zuverlässigsten prüfbar sind:**

- der lokal vorliegende Korpus
- die Strukturprüfung
- der Katalogbau
- die Indexierung
- die lokale Lucene-Suche

Der **FCS-/SRU-Teil** ist als **prototypisch** zu verstehen. Er wurde lokal und über ngrok getestet, aber nicht vollständig validator-konform abgeschlossen.

---

### Ziel des Repositories

Das Repository soll für die Prüfung drei Dinge ermöglichen:

1. den abgegebenen Endzustand direkt nachzuvollziehen  
2. die lokale Verarbeitungskette ohne erneutes Korpusziehen zu testen  
3. auf Wunsch auch einen scraper-basierten Neuaufbau in einer Testumgebung nachzuvollziehen  

Dafür gibt es in diesem README drei getrennte Prüfwege.

---

## Projektstruktur

Der Korpus ist hierarchisch aufgebaut: **Magazin -> Ausgaben -> Artikel -> Volltext**.  
Zusätzlich existieren JSON-Metadaten auf mehreren Ebenen, damit der Bestand als strukturierter Forschungskorpus nutzbar ist.

Die Grundidee lautet:

- **Magazin-Ebene** = allgemeine Informationen zu einem Periodikum
- **Issue-Ebene** = Informationen zu einer konkreten Ausgabe
- **Artikel-Ebene** = Volltext und Metadaten eines einzelnen Artikels

---

### Grundstruktur

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

---

#### 1. Magazin-Ebene

Diese Ebene beschreibt ein gesamtes Magazin oder Periodikum.

- **`magazine.json`**: zentrale Metadatenquelle für das Magazin als Ganzes.
- **`listing.json`**: Magazinweites Issue-Verzeichnis.  

#### 2. Issue-Ebene

**Benennung des Issue-Ordners**

Die Ordner sind in der Regel nach folgendem Muster aufgebaut:

```text
<issue_label>_<issue_date_iso>
```

Diese Ebene beschreibt eine konkrete Ausgabe eines Magazins.

- **`issue.json`**: Enthält Metadaten zur Ausgabe
- **`listing.json`**: Liste der Artikel, die in dieser Ausgabe enthalten sind.

#### 3. Artikel-Ebene

**Benennung des Artikelordners**

Artikelordner enthalten typischerweise:

```text
<Reihenfolge>_<Artikel-ID>_<Kurzslug>
```
Beispiel:
```text
01_12345_Beispielartikel
```

Enthält den eigentlichen nutzbaren Forschungsinhalt: Metadaten und Volltext eines Artikels.

- **`meta.json`**: Metadaten eines einzelnen Artikels, bibliographisch und technisch.
- **`text.txt`**: Der gespeicherte Volltext des Artikels.

.txt sind die wichtigsten Textquellen für:

- Volltextsuche
- Indexierung
- KWIC-Ausgabe
- spätere Forschungsauswertung

Die Struktur erlaubt jeden Artikel bis zu seiner Ausgabe und seinem Magazin zurückzuverfolgen. Auch wenn einzelne Teile fehlen oder unvollständig sind, kann häufig anhand der übrigen Struktur rekonstruiert werden:

- zu welchem Magazin ein Artikel gehört
- zu welcher Ausgabe er gehört
- welche Metadaten vorhanden oder fehlend sind

**Beispiel eines vollständigen Pfads:**

```text
data/zxpress/magazines/Z80/issues/01_1996-04-14/articles/01_12345_Beispielartikel/text.txt
```

- `Z80` = Magazin
- `01_1996-04-14` = konkrete Ausgabe
- `01_12345_Beispielartikel` = konkreter Artikel

---

### Zentrale Verzeichnisse

- **`data/`**: Bereits befüllter Hauptkorpus.

- **`data_small/`**: Kleinerer Teilbestand für kurze Kontrollen oder schnellere Tests.

- **`_catalog/`**: CSV-Kataloge des Korpus

  Diese Dateien werden mit `scripts/light/build_catalog.py` erzeugt.
  Sie dienen als flache tabellarische Sicht auf den Korpus und können vom Indexer verwendet werden.

- **`index_dir/`**: Lucene-Index für die lokale Volltextsuche.

- **`logs/`**: Ausgabeordner für Prüf- und Diagnoseergebnisse.

  **`logs/validation/`**: Einzelne Validierungsprotokolle pro Magazin.

  **`logs/health/`**: Struktur- und Audit-Logs des Korpus.

  Wichtige Dateien:

  - `issues_missing.log`: Issues mit fehlender `issue.json`, `listing.json` oder fehlendem `articles/`

  - `articles_missing.log`: Artikelordner mit fehlender `meta.json` oder `text.txt`

  - `placeholders_0000-01-01.log`: Issues mit Platzhalterdatum `0000-01-01`

  - `magazines_empty.log`: Magazine ohne Issues oder mit fehlendem `issues/`

  - `audit_summary.csv`: Gesamttabelle des Audit-Laufs

  - `audit_problematic_magazines.csv und .log`: Nur problematische Magazine, die man manuell überprüfen sollte.

  - `audit_stdout.log`: Konsolenausgabe des Audit-Laufs

  - `summary.txt`: Hauptzusammenfassung des Health-Checks

  **`logs/textsearch/`**: Logs für die Suchschicht.

- **`scripts/light/`**: Korpusbezogene Hauptskripte

- **`scripts/TextSearch/`**: Suchschicht `Indexer.py` + `Searcher.py`

  **`scripts/TextSearch/_tools/`**: Prüfwerkzeuge für den Index

  - `..._tools/full_healthcheck.py`: Erstellt zusammenfassung der Indexierung.

- **`scripts/FCS/`**: Erster FCS-/SRU-Prototyp.

- **`scripts/FCS_Server/`**: Zweiter Endpoint-Versuch. Dokumentiert, aber nicht der primäre Prüfpfad.

---

## Voraussetzungen

### Python

Im Projektverlauf wurde mit **Python 3.11.13** gearbeitet.

Beispiel:

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

---

## Lokale und harte Pfade

Einige Skripte enthalten harte lokale Pfade und müssen auf eigenem Rechner angepasst werden.

### Harte Pfade

`scripts/FCS/fcs_endpoint.py`

```python
INDEX_DIR = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"
CONFIG_PATH = "/Users/stoia1/Desktop/Website/DigitProject/config/zxpress.yaml"
```

`scripts/light/repair_psychoz_12.py`

```python
MAG = "data/zxpress/magazines/Psychoz"
```

Spezialskript für einen Einzelfall, nicht Teil des allgemeinen Workflows.

---

## Prüfwege

### Prüffall A: Endzustand direkt prüfen

Dies ist der einfachste Prüfweg.  
Der abgegebene Projektstand wird direkt betrachtet und getestet, ohne den Korpus neu aufzubauen.

#### Wichtige Bestände zum Untersuchen

Korpus: `data/`, `data_small/`

Katalog:

- `_catalog/magazines.csv`
- `_catalog/issues.csv`
- `_catalog/articles.csv`

Logs:

- `logs/health/summary.txt`
- `logs/health/audit_problematic_magazines.log`
- `logs/textsearch/full_healthcheck.txt`
- einzelne Dateien in `logs/validation/`

Index:

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

Online-Validator:

```text
https://fcs-validator.data.saw-leipzig.de/
```

Dort eintragen:

- Endpoint BaseURL: `https://<ihre-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум` (en:spectrum)

Dann `Evaluate` starten.

Der Validatorfehler ist reproduzierbar und gehört zum dokumentierten Projektstand.

---

### Prüffall B: Verarbeitung ohne neues Korpusziehen

Dieser Prüfweg nutzt den vorhandenen Korpus unter `/data`, ohne ihn neu zu scrapen.

#### Vorher löschen

Nur generierte logs löschen:

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

Der Healthcheck macht sichtbar, welche Teile des Korpus besonders problematisch sind. Anhand der Logs kann der Forscher gezielt reagieren und bei Bedarf zusätzliche Patches oder manuelle Korrekturen für die weitere Bereinigung erstellen.

Dabei werden geprüft:

- Struktur des Korpus
- fehlende Issue-Dateien
- fehlende Artikeldateien
- Platzhalterdaten
- leere Magazine
- Audit-Zusammenfassung

**Hinweis:**  
`health_zxpress.sh` nutzt vorhandene Validierungslogs in `logs/validation`, wenn diese existieren.  
Neue Validierungslogs müssen separat über `validate_corpus.py` oder automatisch über Scrapper Pipeline erzeugt werden.

#### Schritt 2: Katalog bauen

```bash
python scripts/light/build_catalog.py --root "data/zxpress" --out "_catalog"
```

Ergebnis:

- `_catalog/magazines.csv`
- `_catalog/issues.csv`
- `_catalog/articles.csv`

#### Schritt 3: Index neu bauen 

Legacy-Modus:

```bash
python scripts/TextSearch/Indexer.py \
  --data-root "data/zxpress/magazines" \
  --index-dir "index_dir"
```

oder

Katalogmodus (Katalogdaten müssen vorhanden sein):

```bash
python scripts/TextSearch/Indexer.py \
  --from-catalog \
  --catalog-articles "_catalog/articles.csv" \
  --data-root "data/zxpress" \
  --index-dir "index_dir"
```

#### Schritt 4: TextSearch-Healthcheck (Bestand, Felder und Index überprüfen)

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

Wie in Prüffall A beschrieben.

```bash
ngrok http 8088
```

```bash
curl -i "https://<ihre-adresse>.ngrok-free.dev/health"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=explain&version=2.0"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?x-fcs-endpoint-description=true"
curl -i "https://<ihre-adresse>.ngrok-free.dev/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

Online-Validator: https://fcs-validator.data.saw-leipzig.de/

- Endpoint BaseURL: `https://<ihre-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум` (en:spectrum)
- `Evaluate` starten.


---

### Prüffall C: Neuaufbau mit Scraper in Testumgebung

Dies ist der aufwendigste Prüfweg. Er sollte nicht direkt auf `data/` ausgeführt werden.

Empfohlene Teststruktur:

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

#### WebScrapper Pipeline-Modi

##### Single-Run

Ein einzelnes Magazin:

auf https://zxpress.ru nach Link des Magazins mit ID suchen, als Output unter `magazines/` Magazinnamen eingeben (ohne Sonderzeichen)

```bash
python scripts/light/run_light_pipeline.py \
  --mode single \
  --mag-url "https://zxpress.ru/issue.php?id=1" \
  --out-root "data_test/zxpress/magazines/Z80" \
  --validate
```

##### All-Run

Kompletter zxpress Katalog von `ezines.php`:

```bash
python scripts/light/run_light_pipeline.py \
  --mode all \
  --config "config/zxpress.yaml" \
  --root "data_test/zxpress/magazines" \
  --validate
```

**Wichtiger Hinweis zum All-Run:**

- `--mode all` verarbeitet den Webkatalog vollständig
- ein kompletter Lauf kann über eine Stunde benötigen
- Dauer und Erfolg hängen auch von Netzverbindung und Quellverfügbarkeit ab

#### Was die Pipeline intern macht

Die Pipeline ruft mehrere Skripte unter `/light`nacheinander auf. Damit passiert eine erste Bereinigung bereits im Pipeline-Lauf.  
Trotzdem sollte danach immer noch ein `health_zxpress.sh`-Lauf folgen.

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

Online-Validator: https://fcs-validator.data.saw-leipzig.de/

- Endpoint BaseURL: `https://<ihre-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум` (en:spectrum)
- `Evaluate` starten.

---

## Zusätzliche Skripte

**`scripts/light/validate_corpus.py`**. Validiert ein einzelnes Magazin.

Beispiel:

```bash
python scripts/light/validate_corpus.py --mag-root "data/zxpress/magazines/Psychoz"
```
