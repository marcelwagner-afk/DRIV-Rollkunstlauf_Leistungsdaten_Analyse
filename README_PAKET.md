# DRIV Rollkunstlauf – Leistungsdaten-Analyse · Wartungspaket

**Version 3.3 · Methodik v1.1 · Stand 18.07.2026**

Dieses Paket enthält alles, um das Dashboard `Analyse_Tool_DRIV_Rollkunstlauf.html`
zu pflegen, neu zu bauen und zu prüfen – unabhängig von einer bestimmten Person.

---

## 1. Neue Ergebnisse einpflegen – in 3 Schritten

**Der Normalfall braucht gar kein Werkzeug außer dem Dashboard selbst:**

1. Dashboard im Browser öffnen → Tab **„Daten & Import"**.
2. Wettbewerbstyp wählen (z. B. „Europa Cup") und die offiziellen
   RollArt-Ergebnis-PDFs per Drag & Drop ablegen (mehrere gleichzeitig möglich).
   Der Import-Bericht zeigt je Datei die erkannten Kategorien, Programme und Warnungen.
3. **„Datenbestand sichern (JSON)"** klicken und die Sicherung ablegen –
   sie kann jederzeit wieder eingelesen werden.

> Beispiel Oktober 2026: Europa Cup in Stade → Ergebnis-PDFs von der
> Veranstalter-/DRIV-Seite laden → Typ „Europa Cup" → PDFs hineinziehen → sichern.

**Dauerhafte Übernahme in die ausgelieferte Datei** (damit alle Empfänger die
neuen Daten haben): siehe Abschnitt 3 – die PDFs in `data/` ablegen, einen
Eintrag in `parse_all.py` (Liste `JOBS`) ergänzen und neu bauen.

---

## 2. Paketinhalt

| Datei | Zweck |
|---|---|
| `tool_template.html` | Quell-Template des Dashboards (HTML/CSS/JS, mit Platzhaltern) |
| `parse_intl.py` | Basis-Parser EM/WM 2024/2025 (erzeugt `data/seed_international.json`) |
| `parse_all.py` | Haupt-Parser: liest alle Ergebnis-PDFs, erzeugt `data/seed_v2.json` |
| `postpass.py` | Nachlauf: Konsistenz, Netto-TES, Namens-Kanonisierung, Kader-Zuordnung, Checks |
| `build.py` | Baut die fertige HTML-Datei aus Template + Daten (Datenstand = heute) |
| `check_data.py` | Datenprüfung (nur lesend): Invarianten, Duplikate, Register-Kreuzcheck |
| `tests.mjs` | UI-Regressionstest (Playwright): Tabs, Profile, Prognose-Regeln, Exporte, Druck, Mobil |
| `data/seed_v2.json` | Aufbereiteter Datenbestand (46 Wettbewerbe, 8 392 Ergebnisse) |
| `data/seed_international.json` | Basis-Seed EM/WM 2024/2025 |
| `data/kader.json` | Kaderliste mit Schreibweisen-Varianten |
| `data/athleten_register.json` | Referenz für den 142er-Kreuzcheck |
| `pdfjs.min.js`, `pdfjs.worker.min.js` | Eingebettete PDF-Bibliothek für den Browser-Import |
| `Analyse_Tool_DRIV_Rollkunstlauf.html` | Fertig gebautes Dashboard (Auslieferung) |

**Nicht enthalten (Größe ~405 MB):** die Roh-Ergebnis-PDFs unter `data/…`
(EM/WM/World Cups/Europa Cup/DM/RLW 2023–2026). Quellen: Marcels Ordner
„Upload DRIV/Statistik_Ergebnisse", rollkunstlauf-driv.de (Ergebnisse/Downloads),
Veranstalterseiten (z. B. Google-Drive des Cup of Europe Matosinhos 2025).
Ohne diese PDFs funktioniert alles außer einem kompletten Neu-Parsen
(`parse_all.py`); Bauen, Prüfen und Browser-Import sind uneingeschränkt möglich.

---

## 3. Dashboard neu bauen

Voraussetzungen: **Python 3** (Standardbibliothek genügt).

```bash
python3 build.py        # erzeugt Analyse_Tool_DRIV_Rollkunstlauf.html
python3 check_data.py   # Datenprüfung – muss „ALLE PRÜFUNGEN BESTANDEN“ melden
```

Kompletter Pipeline-Lauf (nur nötig, wenn Roh-PDFs neu geparst werden sollen;
benötigt `pdftotext`/Poppler, für WM-2024-Kür zusätzlich `pdfplumber`):

```bash
python3 parse_intl.py   # 1. Basis-Seed EM/WM
python3 parse_all.py    # 2. alle Events → data/seed_v2.json
python3 postpass.py     # 3. Nachlauf + Checks (muss „142 OK / 0 fehlen“ melden)
python3 build.py        # 4. HTML bauen
```

Neues Event dauerhaft aufnehmen: PDFs z. B. nach `data/coe26/` legen und in
`parse_all.py` einen `JOBS`-Eintrag ergänzen, etwa
`({'typ':'CoE','jahr':2026,'name':'Cup of Europe Stade 2026'},sorted(glob.glob('data/coe26/*.pdf')),'nation')`
– Format `'nation'` für internationale Protokolle (Nationen-Spalte),
`'club'` für deutsche (Vereins-Spalte). Danach Schritte 2–4.

## 4. Tests

```bash
npm i playwright && npx playwright install chromium   # einmalig
node tests.mjs                                        # muss „ALLE TESTS BESTANDEN“ melden
```

## 5. Architektur in einem Absatz

Das Dashboard ist eine einzige HTML-Datei ohne Server. `build.py` injiziert vier
Blöcke ins Template: den Datenbestand (`/*__SEED__*/`), die Kaderliste
(`/*__KADER__*/`), die PDF-Bibliothek (`/*__PDFJS__*/`, `/*__PDFWORKER__*/`)
und das Build-Datum (`/*__BUILD__*/`). Kernregeln (im Template dokumentiert):
TES = technische Elemente − Abzüge, abgesichert über TES + PCS = Gesamt;
PCS = Summe beider Programme (RollArt-Faktoren bereits enthalten);
Referenzwerte = Ø der letzten 3 Jahre je Platzierung, erste 80 % des Feldes
(methodische Festlegung); Prognosen sind rein rechnerische Ableitungen aus
historischen Referenzwerten. Startberechtigungen: WM nur Junioren/Senioren,
EM ab Cadets, Europa Cup/Interland alle Klassen (`ELIG` im Template).
Festlegungen der Sportkommission stehen in den Konstanten `GRUPPE_DIS`
(Gruppen-Anzeige je Disziplin) und in `data/kader.json`.

## 6. Bekannte Punkte / Ausbaustufe 2

Percentile-Ansicht · Inline-Disziplin · Schüler-B-Segmentansicht ·
Feld-Simulation · Europa Cup 2026 (findet erst im Oktober statt).
Historie und Entscheidungen: siehe Projekt-Dokumentation
(`claude/analyse-tool-dokumentation.md` im Claude-Projekt).
