# In 5 Minuten auf GitHub

## 0. Entpacken

1. `DRIV_GitHub_Repo_Kern.zip` entpacken → Ordner `driv-analyse-repo`.
2. Alle `DRIV_Repo_Daten_TeilXX.zip` **in denselben übergeordneten Ordner** entpacken –
   sie füllen automatisch `driv-analyse-repo/data/…` mit den Roh-PDFs auf
   (Doppelklick nacheinander genügt; bei Nachfrage „Zusammenführen/Ersetzen" bestätigen).
3. Kontrolle: der Ordner `driv-analyse-repo/data/` enthält danach Unterordner
   wie `awc/`, `rlw/`, `coe25/` … mit PDF-Dateien.

## 1. Repository auf GitHub anlegen

github.com → **New repository** →
Name z. B. `driv-leistungsdaten-analyse` →
**Private** wählen (empfohlen – der Datenbestand enthält Namen, auch von
Minderjährigen; Zugriff später gezielt an Kommission/Trainer vergeben) →
**KEINE** Haken bei README/.gitignore/Lizenz → **Create repository**.

## 2. Hochladen (im entpackten Ordner ausführen)

```bash
git init -b main
git add -A
git commit -m "DRIV Leistungsdaten-Analyse v3.3 – Dashboard, Pipeline, Roh-Protokolle 2023–2026"
git remote add origin https://github.com/DEIN-BENUTZERNAME/driv-leistungsdaten-analyse.git
git push -u origin main
```

(Git ist auf macOS vorinstalliert bzw. unter git-scm.com erhältlich.
Falls Git nach Name/E-Mail fragt: `git config user.name "Marcel Wagner"` und
`git config user.email "marcel.wagner@w-dfs.de"` einmalig ausführen.)

Beim Push fragt Git nach Anmeldung (Browser-Fenster bzw. Personal Access Token).
Der Upload umfasst ~410 MB (Roh-PDFs) und dauert je nach Leitung einige Minuten.

## 3. Fertig – das passiert automatisch

- GitHub Actions baut bei jedem Push das Dashboard neu und führt die
  Datenprüfung aus (Reiter **Actions**; das fertige HTML hängt dort als
  Artefakt „dashboard").
- Neue Ergebnisse kann jede berechtigte Person direkt im Browser ablegen:
  Ordner `data/NEUE_ERGEBNISSE/` → **Add file → Upload files**
  (Anleitung liegt im Ordner).

## Tipps

- **Mitwirkende einladen:** Settings → Collaborators.
- **Dashboard direkt im Browser bereitstellen** (nur wenn das Repository
  öffentlich sein soll): Settings → Pages → Branch `main` → Ordner `/ (root)`;
  danach ist `…/Analyse_Tool_DRIV_Rollkunstlauf.html` als Link erreichbar.
  Bei privatem Repo stattdessen die HTML-Datei aus dem Repo herunterladen.
- **Neuer Datenstand:** nach Übernahme neuer PDFs (siehe
  `data/NEUE_ERGEBNISSE/ANLEITUNG.md`) einfach committen und pushen –
  Actions prüft automatisch, ob alle Kontrollen grün bleiben.
