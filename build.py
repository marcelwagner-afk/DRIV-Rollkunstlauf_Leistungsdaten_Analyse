# build.py – erzeugt Analyse_Tool_DRIV_Rollkunstlauf.html aus Template + Daten
# Aufruf:  python3 build.py
# Ergebnis: eigenständige HTML-Datei (offline lauffähig), Datenstand = heutiges Datum
import json, datetime, os, sys

REQUIRED = ['tool_template.html', 'data/seed_v2.json', 'data/kader.json',
            'data/konstanz.json', 'pdfjs.min.js', 'pdfjs.worker.min.js']
missing = [f for f in REQUIRED if not os.path.exists(f)]
if missing:
    sys.exit('FEHLER – Dateien fehlen: ' + ', '.join(missing))

tpl    = open('tool_template.html', encoding='utf-8').read()
seed   = json.dumps(json.load(open('data/seed_v2.json', encoding='utf-8')),
                    ensure_ascii=False, separators=(',', ':'))
kader  = json.dumps(json.load(open('data/kader.json', encoding='utf-8')),
                    ensure_ascii=False, separators=(',', ':'))
konst  = json.dumps(json.load(open('data/konstanz.json', encoding='utf-8')),
                    ensure_ascii=False, separators=(',', ':'))
pdfjs  = open('pdfjs.min.js', encoding='utf-8').read()
worker = open('pdfjs.worker.min.js', encoding='utf-8').read()
build  = datetime.date.today().strftime('%d.%m.%Y')

out = (tpl.replace('/*__SEED__*/', seed)
          .replace('/*__KADER__*/', kader)
          .replace('/*__DETAILS__*/', konst)
          .replace('/*__PDFJS__*/', pdfjs)
          .replace('/*__PDFWORKER__*/', worker)
          .replace('/*__BUILD__*/', build))

open('Analyse_Tool_DRIV_Rollkunstlauf.html', 'w', encoding='utf-8').write(out)
n_ev = seed.count('"name"')  # grob
print(f'OK – Analyse_Tool_DRIV_Rollkunstlauf.html gebaut '
      f'({round(len(out)/1e6,2)} MB, Datenstand {build})')
