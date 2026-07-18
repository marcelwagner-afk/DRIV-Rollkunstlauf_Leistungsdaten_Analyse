# check_data.py – Datenqualitätsprüfung (nur lesend, verändert nichts)
# Aufruf:  python3 check_data.py
# Prüft: Invarianten, Duplikate, Segmentsummen, Register-Kreuzcheck, Namens-Hygiene
import json, os, re, sys
from collections import Counter

seed = json.load(open('data/seed_v2.json', encoding='utf-8'))
kader = json.load(open('data/kader.json', encoding='utf-8'))
fail = 0

print('=== Bestand ===')
n_rows = sum(len(k['rows']) for e in seed for k in e['kategorien'])
print(f'Events: {len(seed)} | Ergebnisse: {n_rows}')

print('=== Invarianten ===')
inv = dups = 0
for ev in seed:
    for k in ev['kategorien']:
        c = Counter(r['name'] for r in k['rows'])
        dups += sum(1 for x in c.values() if x > 1)
        for r in k['rows']:
            if r.get('tesOk') and r['tes'] is not None and r['total'] and r['pcs'] is not None:
                if abs(r['tes'] + r['pcs'] - r['total']) > 0.03:
                    inv += 1; print('  TES+PCS≠Total:', ev['name'], r['name'])
            if r.get('tesRaw') is not None and abs(r['tesRaw'] - r.get('abzuege', 0) - r['tes']) > 0.03:
                inv += 1; print('  Raw−Abz≠TES:', ev['name'], r['name'])
            if r.get('segs'):
                s = round(sum(x['tes'] for x in r['segs']), 2)
                if r.get('tesRaw') is not None and abs(s - r['tesRaw']) > 0.05:
                    inv += 1; print('  Segmentsumme≠Raw:', ev['name'], r['name'])
print(f'Invarianten-Verstöße: {inv} | Kategorie-Duplikate: {dups}')
fail += inv + dups

print('=== Namens-Hygiene ===')
allnames = {r['name'] for e in seed for k in e['kategorien'] for r in k['rows']}
bad = [n for n in allnames if re.search(r'\d|  |Kieler$|Post$', n)]
print('Auffällige Namen:', bad if bad else 'keine')
fail += len(bad)

print('=== Register-Kreuzcheck (2026 international) ===')
regp = next((p for p in ('data/athleten_register.json',
                         '/home/claude/driv-dashboard/data/athleten_register.json')
             if os.path.exists(p)), None)
if regp:
    REG = json.load(open(regp, encoding='utf-8'))['athleten']
    vmap = {k['name']: set(k['varianten']) | {k['name']} for k in kader}
    EVMAP = {'wc_gap': 'AWC Semi-Final Garmisch 2026', 'wc_fin': 'AWC Finale Cesena 2026',
             'wc_ba': 'AWC Buenos Aires 2026', 'dm_stade': 'Deutsche Meisterschaften Stade 2026',
             'dp_kuer': 'Int. Deutschland-Pokal Freiburg 2026'}
    ok = 0; miss = []
    for a in REG:
        names = vmap.get(a['name'], {a['name']})
        for ir in a.get('international', []):
            evn = EVMAP.get(ir.get('event_id'))
            if not evn: continue
            pts, pl = ir.get('punkte'), ir.get('platz')
            if pts is None and pl is None: continue
            hit = 0
            for e in seed:
                if e['name'] != evn: continue
                for kk in e['kategorien']:
                    for r in kk['rows']:
                        if r['name'] in names and (
                           (pts is not None and r['total'] is not None and abs(r['total'] - pts) < 0.02)
                           or (pts is None and r['platz'] == pl)):
                            hit = 1
            ok += hit
            if not hit: miss.append((a['name'], evn))
    print(f'Register: {ok} OK, {len(miss)} fehlen', miss[:5])
    fail += len(miss)
else:
    print('athleten_register.json nicht gefunden – Kreuzcheck übersprungen')

print()
print('ERGEBNIS:', 'ALLE PRÜFUNGEN BESTANDEN ✓' if fail == 0 else f'{fail} PROBLEME – bitte prüfen!')
sys.exit(0 if fail == 0 else 1)
