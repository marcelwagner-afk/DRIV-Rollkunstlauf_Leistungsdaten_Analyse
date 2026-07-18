# Neue Ergebnis-PDFs hier ablegen

In diesen Ordner können neue offizielle RollArt-Ergebnis-PDFs gelegt werden
(direkt über die GitHub-Weboberfläche: „Add file → Upload files").

Bitte je Wettbewerb einen Unterordner anlegen, z. B.:

```
data/NEUE_ERGEBNISSE/coe_stade_2026/
    2026_CoE_Results_Free.pdf
    2026_CoE_Results_Solo.pdf
    ...
```

**Übernahme in das Dashboard** (durch die Pflegeperson):

1. Ordner nach `data/<kurzname>/` verschieben (z. B. `data/coe26/`).
2. In `parse_all.py` einen Eintrag in der Liste `JOBS` ergänzen, z. B.:
   `({'typ':'CoE','jahr':2026,'name':'Cup of Europe Stade 2026'},sorted(glob.glob('data/coe26/*.pdf')),'nation')`
   (`'nation'` = internationale Protokolle mit Nationen-Spalte, `'club'` = deutsche mit Vereins-Spalte)
3. `python3 parse_all.py && python3 postpass.py && python3 build.py`
   – `postpass.py` muss „142 OK / 0 fehlen" melden.

Alternativ ohne Pipeline: PDFs einfach im Dashboard unter
**„Daten & Import"** per Drag & Drop einlesen (wirkt nur lokal im Browser).
