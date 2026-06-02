# Stoianov Digital Project

## Inhalt

- [Überblick](#überblick)
- [Ziel des Repositories](#ziel-des-repositories)
- [Projektstruktur](#projektstruktur)
  - [Grundstruktur](#grundstruktur)
  - [Zentrale Verzeichnisse](#zentrale-verzeichnisse)
  - [Wichtige Log-Unterordner](#wichtige-log-unterordner)
- [Voraussetzungen](#voraussetzungen)
- [Lokale und harte Pfade](#lokale-und-harte-pfade)
- [Prüfwege](#prüfwege)
  - [Prüffall A: Endzustand direkt prüfen](#prüffall-a-endzustand-direkt-prüfen)
  - [Prüffall B: Verarbeitung ohne neues Korpusziehen](#prüffall-b-verarbeitung-ohne-neues-korpusziehen)
  - [Prüffall C: Neuaufbau mit Scraper in Testumgebung](#prüffall-c-neuaufbau-mit-scraper-in-testumgebung)
- [Wichtige Skripte](#wichtige-skripte)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Status des Endpoint-Teils](#status-des-endpoint-teils)
- [Empfohlene Reihenfolge](#empfohlene-reihenfolge)

---

## Überblick

Dieses Repository dokumentiert Aufbau, Bereinigung, Validierung, Indexierung und prototypische Bereitstellung eines Korpus russischsprachiger ZX-Spectrum-Diskmags auf Grundlage von ZXPress.

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

## Ziel des Repositories

Das Repository soll für die Prüfung drei Dinge ermöglichen:

1. den abgegebenen Endzustand direkt nachzuvollziehen  
2. die lokale Verarbeitungskette ohne erneutes Korpusziehen zu testen  
3. auf Wunsch auch einen scraper-basierten Neuaufbau in einer Testumgebung nachzuvollziehen  

Dafür gibt es in diesem README drei getrennte Prüfwege.

---

## Projektstruktur

Der Korpus ist hierarchisch aufgebaut. Ausgangspunkt ist ein Magazin, darunter liegen die einzelnen Ausgaben, darunter wiederum die einzelnen Artikel.  
Zusätzlich existieren JSON-Metadaten auf mehreren Ebenen, damit der Bestand nicht nur als Dateisammlung, sondern auch als strukturierter Forschungskorpus nutzbar ist.

Die Grundidee lautet:

- **Magazin-Ebene** = allgemeine Informationen zu einem Periodikum
- **Issue-Ebene** = Informationen zu einer konkreten Ausgabe
- **Artikel-Ebene** = Volltext und Metadaten eines einzelnen Artikels

---

# Grundstruktur

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

## Ebenen des Korpus

## 1. Magazin-Ebene

Beispiel:

```text
data/zxpress/magazines/Z80/
├── magazine.json
├── listing.json
└── issues/
```

### Zweck

Diese Ebene beschreibt ein gesamtes Magazin oder Periodikum.

### Wichtige Dateien

#### `magazine.json`

Enthält Grundinformationen zum Magazin, zum Beispiel:

- Magazinname
- Magazin-ID
- Quelle bzw. URL
- Erscheinungsform
- Stadt/Land
- grober Erscheinungszeitraum
- Anzahl der Issues
- Sprache

Typische Funktion:
Diese Datei ist die zentrale Metadatenquelle für das Magazin als Ganzes.

#### `listing.json`

Magazinweites Issue-Verzeichnis.  
Hier wird festgehalten, welche Ausgaben zu diesem Magazin gehören.

Typischer Inhalt:

- `issue_label`
- `issue_date_iso`
- `articles_count`

Typische Funktion:
Diese Datei ist eine kompakte Übersicht aller bekannten Ausgaben eines Magazins.

---

## 2. Issue-Ebene

Beispiel:

```text
data/zxpress/magazines/Z80/issues/01_1996-04-14/
├── issue.json
├── listing.json
└── articles/
```

### Benennung des Issue-Ordners

Die Ordner sind in der Regel nach folgendem Muster aufgebaut:

```text
<issue_label>_<issue_date_iso>
```

Beispiel:

```text
01_1996-04-14
```

### Zweck

Diese Ebene beschreibt eine konkrete Ausgabe eines Magazins.

### Wichtige Dateien

#### `issue.json`

Enthält Metadaten zur Ausgabe, zum Beispiel:

- `issue_label`
- `issue_date_iso`
- `issue_date_human`
- `articles_count`

Typische Funktion:
Diese Datei definiert die Ausgabe als bibliographische Einheit.

#### `listing.json`

Liste der Artikel, die in dieser Ausgabe enthalten sind.

Typische Felder:

- `order`
- `article_id`
- `title_link`
- `article_url`
- `print_url`

Typische Funktion:
Diese Datei verbindet die Ausgabe mit ihren Artikeln und hält deren Reihenfolge fest.

#### `articles/`

Unterordner mit allen Artikeln dieser Ausgabe.

---

## 3. Artikel-Ebene

Beispiel:

```text
data/zxpress/magazines/Z80/issues/01_1996-04-14/articles/01_12345_Beispielartikel/
├── meta.json
└── text.txt
```

### Benennung des Artikelordners

Artikelordner enthalten typischerweise:

```text
<Reihenfolge>_<Artikel-ID>_<Kurzslug>
```

Beispiel:

```text
01_12345_Beispielartikel
```

### Zweck

Diese Ebene enthält den eigentlichen nutzbaren Forschungsinhalt: Metadaten und Volltext eines Artikels.

### Wichtige Dateien

#### `meta.json`

Metadaten eines einzelnen Artikels, zum Beispiel:

- `article_id`
- `order`
- `title_link`
- `title_h1`
- `article_url`
- `print_url`
- `issue_label`
- `issue_date_iso`
- `magazine_id`
- `magazine_name`

Typische Funktion:
Diese Datei beschreibt den Artikel bibliographisch und technisch.

#### `text.txt`

Der gespeicherte Volltext des Artikels.

Typische Funktion:
Dies ist die wichtigste Textquelle für:

- Volltextsuche
- Indexierung
- KWIC-Ausgabe
- spätere Forschungsauswertung

---

## Warum diese Struktur sinnvoll ist

Die Struktur ist für Digital-Humanities-Arbeit praktisch, weil sie mehrere Dinge zugleich ermöglicht:

### 1. Nachvollziehbarkeit

Man kann jeden Artikel bis zu seiner Ausgabe und seinem Magazin zurückverfolgen.

### 2. Technische Weiterverarbeitung

Die Struktur lässt sich relativ leicht für folgende Schritte nutzen:

- Validierung
- Audit
- Katalogbau
- Indexierung
- lokale Suche
- prototypische Endpoint-Bereitstellung

### 3. Trennung von Metadaten und Volltext

Die Metadaten liegen als JSON vor, der eigentliche Text separat als `text.txt`.  
Dadurch bleiben beide Ebenen klar unterscheidbar.

### 4. Flexible Rekonstruktion

Auch wenn einzelne Teile fehlen oder unvollständig sind, kann häufig anhand der übrigen Struktur rekonstruiert werden:

- zu welchem Magazin ein Artikel gehört
- zu welcher Ausgabe er gehört
- welche Metadaten vorhanden oder fehlend sind

---

## Beziehung der Dateien zueinander

Die Ebenen hängen logisch zusammen:

- `magazine.json` beschreibt das Magazin
- `listing.json` auf Magazin-Ebene beschreibt die vorhandenen Issues
- `issue.json` beschreibt eine konkrete Ausgabe
- `listing.json` auf Issue-Ebene beschreibt die Artikel dieser Ausgabe
- `meta.json` beschreibt den einzelnen Artikel
- `text.txt` enthält seinen Volltext

Kurz gesagt:

```text
Magazin → Issue → Artikel → Volltext
```

---

## Beispiel eines vollständigen Pfads

```text
data/zxpress/magazines/Z80/issues/01_1996-04-14/articles/01_12345_Beispielartikel/text.txt
```

Dieser Pfad bedeutet:

- `Z80` = Magazin
- `01_1996-04-14` = konkrete Ausgabe
- `01_12345_Beispielartikel` = konkreter Artikel
- `text.txt` = Volltext dieses Artikels

Der zugehörige Metadatenpfad wäre:

```text
data/zxpress/magazines/Z80/issues/01_1996-04-14/articles/01_12345_Beispielartikel/meta.json
```

---

### Zentrale Verzeichnisse

**`data/`**  
Bereits befüllter Hauptkorpus. Dies ist der wichtigste Datenbestand der Abgabe.

**`data_small/`**  
Kleinerer Teilbestand für kurze Kontrollen oder schnellere Tests.

**`_catalog/`**  
CSV-Kataloge des Korpus:

- `magazines.csv`
- `issues.csv`
- `articles.csv`

Diese Dateien werden mit `scripts/light/build_catalog.py` erzeugt. 
Sie dienen als flache tabellarische Sicht auf den Korpus und können vom Indexer verwendet werden.

**`index_dir/`**  
Lucene-Index für die lokale Volltextsuche.

**`logs/`**  
Ausgabeordner für Prüf- und Diagnoseergebnisse.

**`logs/validation/`**  
Einzelne Validierungsprotokolle pro Magazin

Diese Dateien entstehen durch `validate_corpus.py`, meist indirekt Health-/Audit-Kontext.

**`logs/health/`**  
Struktur- und Audit-Logs des Korpus.

Wichtige Dateien:

- `issues_missing.log`  
  Issues mit fehlender `issue.json`, `listing.json` oder fehlendem `articles/`

- `articles_missing.log`  
  Artikelordner mit fehlender `meta.json` oder `text.txt`

- `placeholders_0000-01-01.log`  
  Issues mit Platzhalterdatum `0000-01-01`

- `magazines_empty.log`  
  Magazine ohne Issues oder mit fehlendem `issues/`

- `audit_summary.csv`  
  Gesamttabelle des Audit-Laufs

- `audit_problematic_magazines.csv`  
  Nur problematische Magazine

- `audit_problematic_magazines.log`  
  Lesbare Zusammenfassung problematischer Fälle

- `audit_stdout.log`  
  Konsolenausgabe des Audit-Laufs

- `summary.txt`  
  Hauptzusammenfassung des Health-Checks

**`logs/textsearch/`**  
Logs für die Suchschicht.

Wichtige Datei:

- 


**`scripts/light/`**  
Korpusbezogene Hauptskripte:

- `run_light_pipeline.py`
- `scrape_issue_listing_light.py`
- `patch_metadata_light.py`
- `fetch_articles_light.py`
- `validate_corpus.py`
- `health_zxpress.sh`
- `audit_corpus.py`
- `build_catalog.py`
- `repair_psychoz_12.py`

**`scripts/TextSearch/`**  
Suchschicht:

- `Indexer.py`
- `Searcher.py`

**`scripts/TextSearch/_tools/`**  
Prüfwerkzeuge für den Index:

- `feldabdeckung.py`
- `indexueberpruefen.py`
- `full_healthcheck.py`

`full_healthcheck.txt`: Zusammenfassung des TextSearch-Healthchecks

**`scripts/FCS/`**  
Erster FCS-/SRU-Prototyp.

**`scripts/FCS_Server/`**  
Zweiter Endpoint-Versuch. Dokumentiert, aber nicht der primäre Prüfpfad.

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

Einige Skripte sind bereits per CLI-Parameter steuerbar und damit relativ portabel. Andere enthalten harte lokale Pfade und müssen auf einem anderen Rechner angepasst werden.

### Sicher vorhandene harte Pfade

`scripts/FCS/fcs_endpoint.py`

```python
INDEX_DIR = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"
CONFIG_PATH = "/Users/stoia1/Desktop/Website/DigitProject/config/zxpress.yaml"
```

Diese Stellen müssen auf einem anderen Rechner angepasst werden, wenn der Endpoint gestartet werden soll.

`scripts/light/repair_psychoz_12.py`

```python
MAG = "data/zxpress/magazines/Psychoz"
```

Spezialskript für einen Einzelfall, nicht Teil des allgemeinen Workflows.

`scripts/TextSearch/_tools/textsuche klein.py`

```python
dir = FSDirectory.open(Paths.get("/Users/stoia1/Desktop/Website/DigitProject/index_dir"))
```

Kein zentraler Prüfpfad.

### Portablere Hauptskripte

Die folgenden Hauptskripte arbeiten über Parameter und sind für die Prüfung besser geeignet:

- `scripts/light/health_zxpress.sh`
- `scripts/light/build_catalog.py`
- `scripts/TextSearch/Indexer.py`
- `scripts/TextSearch/Searcher.py`
- `scripts/TextSearch/_tools/full_healthcheck.py`

---

## Prüfwege

### Prüffall A: Endzustand direkt prüfen

Dies ist der sicherste und einfachste Prüfweg.  
Es wird nichts neu aufgebaut, sondern der abgegebene Projektstand direkt betrachtet und getestet.

#### Wichtige Bestände

Korpus:

- `data/`
- `data_small/`

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

#### Lokale Suche testen

```bash
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "спектрум" --limit 3
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "covox OR ковокс" --limit 3
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "игра" --year-from 1995 --year-to 1997 --limit 3
```

#### TextSearch-Healthcheck

```bash
python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir"
```

Wenn dieser Schritt erfolgreich ist, ist der vorhandene Lucene-Index lesbar und der Searcher lokal nutzbar.

#### Endpoint lokal starten

Vorher harte Pfade in `scripts/FCS/fcs_endpoint.py` prüfen.

```bash
python scripts/FCS/fcs_endpoint.py
```

Danach lokal testen:

```bash
curl -i "http://127.0.0.1:8088/health"
curl -i "http://127.0.0.1:8088/sru?operation=explain&version=2.0"
curl -i "http://127.0.0.1:8088/sru?x-fcs-endpoint-description=true"
curl -i "http://127.0.0.1:8088/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

#### ngrok verwenden

Voraussetzung: Der Endpoint läuft lokal.

1. Account bei ngrok anlegen  
2. ngrok installieren  
3. Auth-Token setzen, falls nötig  

Tunnel starten:

```bash
ngrok http 8088
```

Danach zeigt ngrok eine öffentliche URL an, z. B.:

```text
https://<deine-adresse>.ngrok-free.dev
```

#### Endpoint über ngrok testen

```bash
curl -i "https://<deine-adresse>.ngrok-free.dev/health"
curl -i "https://<deine-adresse>.ngrok-free.dev/sru?operation=explain&version=2.0"
curl -i "https://<deine-adresse>.ngrok-free.dev/sru?x-fcs-endpoint-description=true"
curl -i "https://<deine-adresse>.ngrok-free.dev/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"
```

#### Validator reproduzieren

Online-Validator:

```text
https://fcs-validator.data.saw-leipzig.de/
```

Dort eintragen:

- Endpoint BaseURL: `https://<deine-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум`

Dann `Evaluate` starten.

**Hinweis:**  
Der Validatorfehler ist reproduzierbar und gehört zum dokumentierten Projektstand. Der Endpoint funktioniert lokal und über ngrok, wurde aber nicht vollständig validator-konform abgeschlossen.

---

### Prüffall B: Verarbeitung ohne neues Korpusziehen

Dieser Prüfweg nutzt den vorhandenen Korpus, ohne ihn neu zu scrapen.

#### Vorher löschen

Nur generierte Artefakte löschen, nicht den Korpus:

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

**Hinweis:**  
`health_zxpress.sh` nutzt vorhandene Validierungslogs in `logs/validation`, wenn diese existieren.  
Neue Validierungslogs müssen separat über `validate_corpus.py` oder die Pipeline erzeugt werden.

#### Schritt 2: Katalog bauen

```bash
python scripts/light/build_catalog.py --root "data/zxpress" --out "_catalog"
```

Ergebnis:

- `_catalog/magazines.csv`
- `_catalog/issues.csv`
- `_catalog/articles.csv`

Der Katalog dient als tabellarische Repräsentation des Korpus und kann vom Indexer verwendet werden.

#### Schritt 3: Index neu bauen

Legacy-Modus:

```bash
python scripts/TextSearch/Indexer.py \
  --data-root "data/zxpress/magazines" \
  --index-dir "index_dir"
```

Katalogmodus:

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

Dieser Schritt enthält bereits:

- `feldabdeckung.py`
- `indexueberpruefen.py`

#### Schritt 5: Searcher testen

```bash
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "спектрум" --limit 3
```

#### Schritt 6: Endpoint lokal testen

Vorher harte Pfade in `scripts/FCS/fcs_endpoint.py` prüfen.

```bash
python scripts/FCS/fcs_endpoint.py
```

Danach lokale `curl`-Tests wie in Prüffall A.

#### Schritt 7: ngrok + Validator

Wie in Prüffall A beschrieben.

---

### Prüffall C: Neuaufbau mit Scraper in Testumgebung

Dies ist der aufwendigste und riskanteste Prüfweg.  
Er sollte nicht direkt auf `data/` ausgeführt werden.

Empfohlene Teststruktur:

- `data_test/`
- `_catalog_test/`
- `index_dir_test/`

#### Vorher löschen

```bash
rm -rf data_test
rm -rf _catalog_test
rm -rf index_dir_test
rm -rf logs/health
rm -rf logs/validation
rm -rf logs/textsearch
```

#### Pipeline-Modi

##### Single-Run

Ein einzelnes Magazin:

```bash
python scripts/light/run_light_pipeline.py \
  --mode single \
  --mag-url "https://zxpress.ru/issue.php?id=1" \
  --out-root "data_test/zxpress/magazines/Z80" \
  --validate
```

##### All-Run

Kompletter Katalog von `ezines.php`:

```bash
python scripts/light/run_light_pipeline.py \
  --mode all \
  --config "config/zxpress.yaml" \
  --validate
```

**Wichtiger Hinweis zum All-Run:**

- `--mode all` verarbeitet den ZXPress-Katalog vollständig
- der Lauf kann deutlich länger dauern
- ein kompletter Lauf kann über eine Stunde benötigen
- Dauer und Erfolg hängen auch von Netzverbindung und Quellverfügbarkeit ab

#### Was die Pipeline intern macht

Die Pipeline ruft nacheinander auf:

1. `scrape_issue_listing_light.py`
2. `patch_metadata_light.py`
3. `fetch_articles_light.py`
4. optional `validate_corpus.py`

Damit passiert eine erste Bereinigung bereits im Pipeline-Lauf.  
Trotzdem sollte danach immer noch ein `health_zxpress.sh`-Lauf folgen.

#### Nach dem Scraperlauf

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

---

## Wichtige Skripte

`scripts/light/validate_corpus.py`  
Validiert ein einzelnes Magazin.

Beispiel:

```bash
python scripts/light/validate_corpus.py --mag-root "data/zxpress/magazines/Psychoz"
```

`scripts/light/health_zxpress.sh`  
Gesamtprüfung des Korpusbestands:

- Struktur
- fehlende Dateien
- Platzhalterdaten
- leere Magazine
- Audit

`scripts/light/audit_corpus.py`  
Audit-Zusammenfassung über Magazine. Wird im Normalfall über `health_zxpress.sh` mit aufgerufen.

`scripts/light/build_catalog.py`  
Erzeugt die drei CSV-Kataloge.

`scripts/TextSearch/Indexer.py`  
Baut den Lucene-Index.

`scripts/TextSearch/Searcher.py`  
Lokale Volltextsuche über den Lucene-Index.

`scripts/TextSearch/_tools/full_healthcheck.py`  
Gesamttest der Suchschicht. Wenn dieser Schritt erfolgreich ist, ist die lokale Suchschicht nutzbar.

`scripts/FCS/fcs_endpoint.py`  
Erster FCS-/SRU-Prototyp. Lokal funktionsfähig, aber validator-seitig nicht vollständig abgeschlossen.

---

## Bekannte Einschränkungen

- Der Scraper ist von ZXPress als externer Quelle abhängig.
- Ein kompletter Rebuild kann scheitern, wenn sich die Quellseite verändert oder nicht erreichbar ist.
- Einige Skripte enthalten harte Pfade.
- Der FCS-Endpoint ist nur prototypisch abgeschlossen.
- Der Validatorfehler ist Teil des dokumentierten Projektstands.
- `requirements.txt`, `pyproject.toml` und `setup.py` waren im Projektverlauf noch nicht vollständig ausgereift.

---

## Status des Endpoint-Teils

**Gesichert belegt sind:**

- lokaler Start des Endpoints
- erfolgreiche lokale `curl`-Tests
- erfolgreiche ngrok-Freigabe
- reproduzierbare Validator-Tests
- mehrere Anpassungsversuche an `fcs_xml.py` und `fcs_endpoint.py`

**Nicht erreicht wurde:**

- eine vollständig validator-konforme Endfassung

Für die Abgabe bedeutet das:

- lokal funktionsfähiger Prototyp: **ja**
- vollständig abgeschlossene CLARIN-FCS-Standardintegration: **nein**

---

## Empfohlene Reihenfolge

Am sinnvollsten ist diese Reihenfolge:

- **Prüffall A** – schnellster und sicherster Einstieg
- **Prüffall B** – technisch nachvollziehbarer Neuaufbau ohne Netzrisiko
- **Prüffall C** – vollständiger Neuaufbau mit externem Risiko
