Stoianov Digital Project
========================

Überblick
---------
Dieses Repository dokumentiert den Aufbau, die Bereinigung, die Validierung, die Indexierung und die prototypische Bereitstellung eines Korpus russischsprachiger ZX-Spectrum-Diskmags auf Grundlage von ZXPress.

Das Projekt hat vier praktische Hauptteile:

1. Korpusaufbau und Korpusspeicherung
2. Bereinigung, Validierung und Audit
3. Lokale Volltextsuche mit Lucene
4. Prototypische FCS-/SRU-Bereitstellung

Wichtig ist: Dieses Repository ist kein vollständig neu entwickeltes Clean-Room-Projekt, sondern ein über längere Zeit gewachsener Projektstand. Daher enthalten einige Verzeichnisse stabile, prüfbare Komponenten, andere eher experimentelle oder unvollständig abgeschlossene Teile.

Der stabilste und am besten prüfbare Kern ist:
- der lokal vorliegende Korpus,
- die Strukturprüfung,
- der Katalogbau,
- die Indexierung,
- die lokale Lucene-Suche.

Der FCS-/SRU-Teil ist als prototypisch zu verstehen. Er wurde lokal und über ngrok getestet, aber nicht vollständig validator-konform abgeschlossen.


Ziel des Repositories
--------------------
Das Repository soll für die Prüfung drei Dinge ermöglichen:

1. den abgegebenen Endzustand direkt nachzuvollziehen,
2. die lokale Verarbeitungskette ohne erneutes Korpusziehen zu testen,
3. auf Wunsch auch den Scraper-basierten Neuaufbau in einer Testumgebung nachzuvollziehen.

Dafür gibt es in diesem README drei getrennte Prüfwege.


Projektstruktur
---------------

Zentrale Verzeichnisse
~~~~~~~~~~~~~~~~~~~~~~

`data/`
Bereits befüllter Hauptkorpus. Dieser Ordner ist der wichtigste Bestand der Abgabe.

`data_small/`
Kleinerer Teilbestand für kürzere Kontrollen oder schnellere Tests.

`_catalog/`
CSV-Kataloge zum Korpus:
- magazines.csv
- issues.csv
- articles.csv

Diese Dateien werden mit `scripts/light/build_catalog.py` erzeugt. Sie dienen als flache tabellarische Sicht auf den Korpus und können vom Indexer verwendet werden.

`index_dir/`
Lucene-Index für die lokale Volltextsuche.

`logs/`
Ausgabeordner für Prüf- und Diagnoseergebnisse.

Wichtige Unterordner in `logs/`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`logs/validation/`
Einzelne Validierungsprotokolle pro Magazin, z. B.:
- `validate_ACNews_...txt`
- `validate_Anecdotes_...txt`

Diese Dateien entstehen durch `validate_corpus.py`, meist indirekt über Pipeline oder Health-/Audit-Kontext.

`logs/health/`
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
  Gesamttabelle des Audit-Laufs über alle Magazine
- `audit_problematic_magazines.csv`
  Nur Magazine, die für manuelle Sichtung relevant sind
- `audit_problematic_magazines.log`
  Lesbare Textzusammenfassung problematischer Magazine
- `audit_stdout.log`
  Konsolenausgabe des Audit-Laufs
- `summary.txt`
  Hauptzusammenfassung des Health-Checks

`logs/textsearch/`
Logs für die Suchschicht.

Wichtige Datei:
- `full_healthcheck.txt`
  Zusammenfassung des TextSearch-Healthchecks

`scripts/light/`
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

`scripts/TextSearch/`
Suchschicht:
- `Indexer.py`
- `Searcher.py`

`scripts/TextSearch/_tools/`
Prüfwerkzeuge für den Index:
- `feldabdeckung.py`
- `indexüberprüfen.py`
- `full_healthcheck.py`

`scripts/FCS/`
Erster FCS-/SRU-Prototyp.

`scripts/FCS_Server/`
Zweiter Endpoint-Versuch. Dieser wird im Repository dokumentiert, ist aber nicht der primäre erfolgreiche Prüfpfad.


Voraussetzungen
---------------

Python
~~~~~~
Im Projektverlauf wurde mit Python 3.11.13 gearbeitet.

Beispiel aus der Testumgebung:

python3 --version
which python
which python3

Erwartet wurde dabei eine Python-3.11-Umgebung.

Java
~~~~
Für Lucene, Indexer, Searcher und Endpoint wurde Java 21 verwendet.

Beispiel:

java -version

Abhängigkeiten
~~~~~~~~~~~~~~

Für Scraper und Light-Skripte:

pip install -r requirements-scraper.txt

Für Suche, Lucene und Endpoint:

pip install -r requirements.txt


Wichtiger Hinweis zu lokalen und harten Pfaden
---------------------------------------------
Einige Skripte arbeiten bereits mit CLI-Parametern und sind dadurch portabler. Andere enthalten harte lokale Pfade, die auf einem anderen Rechner angepasst werden müssen.

Sicher vorhandene harte Pfade im Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`scripts/FCS/fcs_endpoint.py`

INDEX_DIR = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"
CONFIG_PATH = "/Users/stoia1/Desktop/Website/DigitProject/config/zxpress.yaml"

Diese beiden Stellen müssen auf einem anderen Rechner angepasst werden, falls der Endpoint wirklich gestartet werden soll.

`scripts/light/repair_psychoz_12.py`

MAG = "data/zxpress/magazines/Psychoz"

Dieses Skript ist ein Spezialreparaturskript für einen konkreten Fall und nicht als allgemeiner Workflow-Schritt gedacht.

`scripts/TextSearch/_tools/textsuche klein.py`

dir = FSDirectory.open(Paths.get("/Users/stoia1/Desktop/Website/DigitProject/index_dir"))

Dieses Skript ist kein zentraler Prüfpfad und nutzt einen harten Pfad.

Portablere Hauptskripte
~~~~~~~~~~~~~~~~~~~~~~~
Die folgenden Hauptskripte sind bereits über Parameter steuerbar und daher für die Prüfung besser geeignet:
- `scripts/light/health_zxpress.sh`
- `scripts/light/build_catalog.py`
- `scripts/TextSearch/Indexer.py`
- `scripts/TextSearch/Searcher.py`
- `scripts/TextSearch/_tools/full_healthcheck.py`


Drei Prüfarten
--------------

1. Prüffall A: Endzustand nur ansehen und direkt benutzen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dieser Prüfweg ist der sicherste und für einen Dozenten am einfachsten.

Hier wird nichts neu aufgebaut, sondern nur der abgegebene Projektstand betrachtet und punktuell benutzt.

Was man sich anschauen sollte
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

Lokale Suche direkt testen
^^^^^^^^^^^^^^^^^^^^^^^^^^

python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "спектрум" --limit 3
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "covox OR ковокс" --limit 3
python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "игра" --year-from 1995 --year-to 1997 --limit 3

TextSearch-Gesundheit prüfen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir"

Wenn dieser Schritt erfolgreich ist, bedeutet das praktisch: Der vorhandene Lucene-Index ist lesbar und der Searcher kann lokal ausgeführt werden.

Endpoint lokal starten
^^^^^^^^^^^^^^^^^^^^^^
Vorher harte Pfade in `scripts/FCS/fcs_endpoint.py` prüfen.

python scripts/FCS/fcs_endpoint.py

Danach lokal testen:

curl -i "http://127.0.0.1:8088/health"
curl -i "http://127.0.0.1:8088/sru?operation=explain&version=2.0"
curl -i "http://127.0.0.1:8088/sru?x-fcs-endpoint-description=true"
curl -i "http://127.0.0.1:8088/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"

ngrok verwenden
^^^^^^^^^^^^^^^
Der Endpoint muss lokal laufen.

Registrierung:
1. Account bei ngrok anlegen
2. ngrok lokal installieren
3. Auth-Token setzen, falls nötig

Tunnel starten:

ngrok http 8088

Danach zeigt ngrok eine öffentliche URL an, z. B.:

https://<deine-adresse>.ngrok-free.dev

Endpoint über ngrok testen
^^^^^^^^^^^^^^^^^^^^^^^^^^

curl -i "https://<deine-adresse>.ngrok-free.dev/health"
curl -i "https://<deine-adresse>.ngrok-free.dev/sru?operation=explain&version=2.0"
curl -i "https://<deine-adresse>.ngrok-free.dev/sru?x-fcs-endpoint-description=true"
curl -i "https://<deine-adresse>.ngrok-free.dev/sru?operation=searchRetrieve&version=2.0&query=cql.serverChoice=%22%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D1%80%D1%83%D0%BC%22&maximumRecords=3"

Validator reproduzieren
^^^^^^^^^^^^^^^^^^^^^^^
Online-Validator:
https://fcs-validator.data.saw-leipzig.de/

Dort eintragen:
- Endpoint BaseURL: `https://<deine-adresse>.ngrok-free.dev/sru`
- Search Term: `спектрум`

Dann Evaluate starten.

Wichtiger Hinweis:
Der Validatorfehler ist reproduzierbar und gehört zum dokumentierten Projektstand. Der Endpoint funktioniert lokal und über ngrok, wurde aber nicht vollständig validator-konform abgeschlossen.


2. Prüffall B: Alles außer Korpusziehen neu testen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dieser Prüfweg ist für den Fall gedacht, dass man den vorhandenen Korpus nicht neu scrapen, aber die Verarbeitungsschritte selbst neu laufen lassen will.

Hier wird nicht in `data/` neu gezogen, sondern mit dem vorhandenen Korpus gearbeitet.

Vorher zu löschen
^^^^^^^^^^^^^^^^^
Nur generierte Artefakte löschen, nicht den Korpus selbst.

rm -rf _catalog
rm -rf index_dir
rm -rf logs/health
rm -rf logs/validation
rm -rf logs/textsearch

Reihenfolge
^^^^^^^^^^^

Schritt 1: Health-Check mit Audit
+++++++++++++++++++++++++++++++++
Dieser Schritt ist vor dem Katalogbau sinnvoll, weil zuerst geprüft werden sollte, ob der Korpus strukturell tragfähig ist.

bash scripts/light/health_zxpress.sh data/zxpress/magazines logs/health logs/validation

Was dabei passiert:
- Strukturprüfung des Korpus
- Prüfung auf fehlende Issue-Dateien
- Prüfung auf fehlende Artikeldateien
- Erkennung von Platzhalterdaten
- Erkennung leerer Magazine
- Audit-Zusammenfassung über Magazine
- Einbezug der Validator-Logs aus `logs/validation`

Hinweis zu Validation:
`health_zxpress.sh` führt selbst nicht alle Validierungen neu aus, sondern nutzt für das Audit vorhandene Validierungslogs in `logs/validation`, wenn diese existieren.

Wenn man neue Validator-Logs erzeugen will, muss man `validate_corpus.py` gezielt pro Magazin oder über die Pipeline laufen lassen.

Schritt 2: Katalog bauen
++++++++++++++++++++++++
Erst danach den Katalog neu aufbauen.

python scripts/light/build_catalog.py --root "data/zxpress" --out "_catalog"

Ergebnis:
- `_catalog/magazines.csv`
- `_catalog/issues.csv`
- `_catalog/articles.csv`

Wozu dient der Katalog?
Der Katalog ist die tabellarische Repräsentation des Korpus. Er dient vor allem dazu,
- den Korpus flach und übersichtlich zu inspizieren,
- den Indexer im Katalogmodus zu speisen.

Schritt 3: Index neu bauen
++++++++++++++++++++++++++
Legacy-Modus:

python scripts/TextSearch/Indexer.py \
  --data-root "data/zxpress/magazines" \
  --index-dir "index_dir"

oder Katalogmodus:

python scripts/TextSearch/Indexer.py \
  --from-catalog \
  --catalog-articles "_catalog/articles.csv" \
  --data-root "data/zxpress" \
  --index-dir "index_dir"

Schritt 4: TextSearch-Healthcheck
+++++++++++++++++++++++++++++++++

python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir"

Dieser Schritt enthält bereits:
- `feldabdeckung.py`
- `indexüberprüfen.py`

Schritt 5: Searcher testen
++++++++++++++++++++++++++

python scripts/TextSearch/Searcher.py --index-dir "index_dir" --q "спектрум" --limit 3

Schritt 6: Endpoint lokal testen
++++++++++++++++++++++++++++++++
Vorher harte Pfade in `scripts/FCS/fcs_endpoint.py` prüfen.

python scripts/FCS/fcs_endpoint.py

Dann lokale `curl`-Tests wie oben.

Schritt 7: ngrok + Validator
++++++++++++++++++++++++++++
Wie in Prüffall A beschrieben.


3. Prüffall C: Alles inklusive Korpusziehen testen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dieser Prüfweg ist der aufwendigste und riskanteste. Er ist optional und sollte nicht direkt auf `data/` ausgeführt werden.

Dafür eine getrennte Teststruktur benutzen:
- `data_test/`
- `_catalog_test/`
- `index_dir_test/`

Vorher zu löschen
^^^^^^^^^^^^^^^^^

rm -rf data_test
rm -rf _catalog_test
rm -rf index_dir_test
rm -rf logs/health
rm -rf logs/validation
rm -rf logs/textsearch

Pipeline-Modi
^^^^^^^^^^^^^

Single-Run
++++++++++
Ein einzelnes Magazin:

python scripts/light/run_light_pipeline.py \
  --mode single \
  --mag-url "https://zxpress.ru/issue.php?id=1" \
  --out-root "data_test/zxpress/magazines/Z80" \
  --validate

All-Run
+++++++
Kompletter Katalog von `ezines.php`:

python scripts/light/run_light_pipeline.py \
  --mode all \
  --config "config/zxpress.yaml" \
  --validate

Wichtiger Hinweis zum All-Run:
- `--mode all` verarbeitet den Katalog von ZXPress vollständig
- das kann deutlich länger dauern
- ein kompletter Lauf kann über eine Stunde dauern
- der Lauf hängt zusätzlich von Netzverbindung und Quellverfügbarkeit ab

Was die Pipeline macht
++++++++++++++++++++++
Die Pipeline ruft intern nacheinander auf:
1. `scrape_issue_listing_light.py`
2. `patch_metadata_light.py`
3. `fetch_articles_light.py`
4. optional `validate_corpus.py`

Das heißt:
- erste Bereinigung passiert bereits in der Pipeline
- dennoch sollte danach immer noch ein `health_zxpress.sh`-Lauf folgen, um Restprobleme sichtbar zu machen

Nach dem Scraperlauf
++++++++++++++++++++
Schritt 1: Health-Check

bash scripts/light/health_zxpress.sh data_test/zxpress/magazines logs/health logs/validation

Schritt 2: Katalog bauen

python scripts/light/build_catalog.py --root "data_test/zxpress" --out "_catalog_test"

Schritt 3: Index bauen

python scripts/TextSearch/Indexer.py \
  --from-catalog \
  --catalog-articles "_catalog_test/articles.csv" \
  --data-root "data_test/zxpress" \
  --index-dir "index_dir_test"

Schritt 4: TextSearch-Healthcheck

python scripts/TextSearch/_tools/full_healthcheck.py --index-dir "index_dir_test"

Schritt 5: Searcher testen

python scripts/TextSearch/Searcher.py --index-dir "index_dir_test" --q "спектрум" --limit 3

Schritt 6: Endpoint

Falls der Endpoint mit Testdaten geprüft werden soll, müssen in `scripts/FCS/fcs_endpoint.py` die harten Pfade angepasst werden.


Wofür die wichtigsten Skripte da sind
------------------------------------

`scripts/light/validate_corpus.py`
Validiert ein einzelnes Magazin.

Beispiel:
python scripts/light/validate_corpus.py --mag-root "data/zxpress/magazines/Psychoz"

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
Erzeugt aus dem Korpus die drei CSV-Kataloge.

`scripts/TextSearch/Indexer.py`
Baut den Lucene-Index.

`scripts/TextSearch/Searcher.py`
Lokale Volltextsuche über den Lucene-Index.

`scripts/TextSearch/_tools/full_healthcheck.py`
Gesamttest für die Suchschicht. Wenn dieser Schritt erfolgreich ist, ist die lokale Suchschicht nutzbar.

`scripts/FCS/fcs_endpoint.py`
Erster FCS-/SRU-Prototyp. Lokal funktionsfähig, aber validator-seitig nicht vollständig abgeschlossen.


Bekannte Einschränkungen
------------------------
- Der Scraper ist von ZXPress als externer Quelle abhängig.
- Ein kompletter Rebuild kann scheitern, wenn sich die Quellseite verändert oder nicht erreichbar ist.
- Einige Skripte enthalten harte Pfade.
- Der FCS-Endpoint ist nur prototypisch abgeschlossen.
- Der Validatorfehler ist Teil des realen Projektstands.
- `requirements.txt`, `pyproject.toml` und `setup.py` waren im Projektverlauf selbst noch eine Baustelle und sind nicht als vollständig ausgereifte Paketierungsbasis zu lesen.


Status des Endpoint-Teils
-------------------------
Gesichert belegt ist:
- lokaler Start des Endpoints,
- erfolgreiche lokale `curl`-Tests,
- erfolgreiche ngrok-Freigabe,
- reproduzierbare Validator-Tests,
- mehrere Anpassungsversuche an `fcs_xml.py` und `fcs_endpoint.py`.

Nicht erreicht wurde:
- eine vollständig validator-konforme Endfassung.

Für die Abgabe bedeutet das:
- lokal funktionsfähiger Prototyp: ja
- vollständig abgeschlossene CLARIN-FCS-Standardintegration: nein


Empfohlener Prüfweg
--------------------------------------
Am sinnvollsten ist diese Reihenfolge:
- Schnell und sicher: Prüffall A
- Technisch nachvollziehbar ohne Netzrisiko: Prüffall B
- Vollständiger Neuaufbau mit externem Risiko: Prüffall C


