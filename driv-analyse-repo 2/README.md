# DRIV Rollkunstlauf – Leistungsdaten-Analyse

Statistische Auswertung historischer Wettkampfdaten der DRIV-Kaderathleten
(2023–2026) auf Basis offizieller RollArt-Ergebnisprotokolle.
**Version 3.3 · Methodik v1.1**

> Dieses Dashboard dient ausschließlich der transparenten statistischen
> Auswertung historischer Wettkampfdaten. Enthaltene Prognosen sind rein
> rechnerische Ableitungen aus historischen Referenzwerten – keine Garantie,
> keine sportfachliche Bewertung, keine Empfehlung für Kader-, Förder- oder
> Nominierungsentscheidungen.

## Dashboard nutzen

`Analyse_Tool_DRIV_Rollkunstlauf.html` herunterladen und im Browser öffnen –
keine Installation, kein Server, läuft vollständig offline
(46 Wettbewerbe, 8 381 Einzelergebnisse, Stand 18.07.2026).

## Neue Ergebnisse ablegen

Offizielle RollArt-PDFs über die GitHub-Weboberfläche nach
[`data/NEUE_ERGEBNISSE/`](data/NEUE_ERGEBNISSE/) hochladen
(„Add file → Upload files", je Wettbewerb ein Unterordner).
Die Übernahme ins Dashboard ist dort in der ANLEITUNG.md beschrieben –
oder die PDFs direkt im Dashboard unter „Daten & Import" per Drag & Drop einlesen.

## Selbst bauen und prüfen

```bash
python3 build.py        # erzeugt Analyse_Tool_DRIV_Rollkunstlauf.html
python3 check_data.py   # Datenprüfung (muss „ALLE PRÜFUNGEN BESTANDEN" melden)
node tests.mjs          # UI-Tests (benötigt Playwright, siehe README_PAKET.md)
```

Der GitHub-Actions-Workflow ([`.github/workflows/build.yml`](.github/workflows/build.yml))
baut und prüft automatisch bei jedem Push; das fertige HTML hängt als
Artefakt „dashboard" am Workflow-Lauf.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `Analyse_Tool_DRIV_Rollkunstlauf.html` | fertiges Dashboard (eine Datei, offline) |
| `tool_template.html` | Quell-Template (HTML/CSS/JS mit Platzhaltern) |
| `parse_intl.py`, `parse_all.py`, `postpass.py` | Daten-Pipeline (PDF → Datenbestand) |
| `build.py`, `check_data.py`, `tests.mjs` | Bauen, Datenprüfung, UI-Tests |
| `data/seed_v2.json`, `data/kader.json` | aufbereiteter Datenbestand + Kaderliste |
| `data/…/*.pdf` | Roh-Ergebnisprotokolle 2023–2026 (Quelle der Wahrheit) |
| `README_PAKET.md` | ausführliche Wartungs-Dokumentation |

## Methodik in Kürze

TES = technische Elemente − Abzüge (nie der PDF-Endwert; Kontrolle
TES + PCS = Gesamt). PCS = Summe beider Programme, RollArt-Faktoren bereits
enthalten. Referenzwerte = Ø der letzten 3 ausgetragenen Jahre je Platzierung,
erste 80 % des Feldes (methodische Festlegung dieses Projekts).
Details im Dashboard-Tab „Methodik".

## Datenschutz-Hinweis

Der Datenbestand enthält Namen und Ergebnisse aus öffentlich veröffentlichten
offiziellen Ergebnislisten – darunter auch minderjährige Athletinnen und
Athleten. **Empfehlung: Repository privat betreiben** und nur berechtigten
Personen (Sportkommission, Trainer) Zugriff geben.
