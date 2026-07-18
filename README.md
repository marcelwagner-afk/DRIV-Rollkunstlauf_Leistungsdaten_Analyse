# DRIV Rollkunstlauf – Leistungsdaten-Analyse

Statistische Auswertung historischer Wettkampfdaten der DRIV-Kaderathleten
(2023–2026) auf Basis offizieller RollArt-Ergebnisprotokolle.
**Version 3.4 · Methodik v1.2**

> Dieses Dashboard dient ausschließlich der transparenten statistischen
> Auswertung historischer Wettkampfdaten. Enthaltene Prognosen sind rein
> rechnerische Ableitungen aus historischen Referenzwerten – keine Garantie,
> keine sportfachliche Bewertung, keine Empfehlung für Kader-, Förder- oder
> Nominierungsentscheidungen.

## Zugriff: passwortgeschützte Login-Seite

Das Dashboard ist über eine **Login-Seite** erreichbar:
**https://marcelwagner-afk.github.io/DRIV-Rollkunstlauf_Leistungsdaten_Analyse/**
Der Dashboard-Inhalt liegt dort AES-256-verschlüsselt und wird erst nach
erfolgreicher Anmeldung im Browser entschlüsselt.

- **Zugang anfordern / Passwort vergessen:** formlose E-Mail an
  Marcel Wagner (Sportkommission) – er legt Benutzername + Passwort an und
  teilt sie persönlich mit.
- **Benutzerverwaltung (nur Sportkommission):** direkt **online** – als
  Verwalter anmelden → „Benutzerverwaltung“ → Personen anlegen/ändern/entziehen
  → „Speichern & veröffentlichen“. Die Seite verschlüsselt sich dabei im
  Browser komplett neu. Alternativ lokal: `zugang/benutzer.txt` pflegen
  (liegt **nicht** im Repository) und mit `python3 protect.py` neu erzeugen.
- **Technik:** `protect.py` verschlüsselt das Dashboard je Benutzer
  (PBKDF2-SHA256 mit 310 000 Iterationen, AES-256-GCM); Benutzernamen stehen
  nur als Hash in der veröffentlichten Seite. Eine erzwungene Passwort-Änderung
  beim ersten Login ist ohne Server nicht möglich – daher starke, persönliche
  Passwörter vergeben und bei Bedarf rotieren.

## Neue Ergebnisse ablegen

Offizielle RollArt-PDFs über die GitHub-Weboberfläche nach
[`data/NEUE_ERGEBNISSE/`](data/NEUE_ERGEBNISSE/) hochladen
(„Add file → Upload files", je Wettbewerb ein Unterordner) – oder in den
freigegebenen Google-Drive-Ordner „Statistik_Ergebnisse" legen und im Reiter
**Actions** den Workflow „Drive-Abgleich" starten.
Die Übernahme ins Dashboard ist in `data/NEUE_ERGEBNISSE/ANLEITUNG.md`
beschrieben – oder die PDFs direkt im Dashboard unter „Daten & Import"
per Drag & Drop einlesen.

## Selbst bauen und prüfen

```bash
python3 build.py        # erzeugt Analyse_Tool_DRIV_Rollkunstlauf.html
python3 check_data.py   # Datenprüfung (muss „ALLE PRÜFUNGEN BESTANDEN" melden)
node tests.mjs          # UI-Tests (benötigt Playwright, siehe README_PAKET.md)
```

Der GitHub-Actions-Workflow ([`.github/workflows/build.yml`](.github/workflows/build.yml))
baut und prüft automatisch bei jedem Push, committet das aktualisierte
Dashboard zurück und legt es zusätzlich als Artefakt „dashboard" am
Workflow-Lauf ab.

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
Neu in v3.4: „Rückstand auf Platz 1–3" – rechnerischer Abstand des besten
Saison-TES/PCS zu den Referenzwerten je startberechtigtem Wettbewerb.
Details im Dashboard-Tab „Methodik".

## Datenschutz-Hinweis

Der Datenbestand enthält Namen und Ergebnisse aus öffentlich veröffentlichten
offiziellen Ergebnislisten – darunter auch minderjährige Athletinnen und
Athleten. Das Repository wird deshalb **privat** betrieben; Zugriff nur für
berechtigte Personen (Sportkommission, Trainer) über persönliche
GitHub-Konten.
