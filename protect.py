#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
protect.py – erzeugt die passwortgeschützte Login-Seite des Dashboards.

Eingaben:
  Analyse_Tool_DRIV_Rollkunstlauf.html   (fertig gebautes Dashboard)
  zugang/benutzer.txt                    (eine Zeile je Benutzer: benutzername;passwort
                                          Leerzeilen und #-Kommentare erlaubt)
Ausgabe:
  login/index.html   – eigenständige Login-Seite; das komplette Dashboard liegt
                       darin AES-256-GCM-verschlüsselt. Ohne gültigen Benutzer +
                       Passwort ist der Inhalt kryptografisch nicht lesbar.

Technik: je Benutzer wird der Inhaltsschlüssel mit einem aus benutzername:passwort
abgeleiteten Schlüssel (PBKDF2-SHA256, 310.000 Iterationen) eingepackt.
Benutzernamen stehen nur als SHA-256-Hash in der Seite.

Aufruf:  python3 protect.py        (im Repository-Hauptordner)
"""
import base64, hashlib, json, os, secrets, sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    sys.exit("Fehlende Bibliothek: bitte einmalig  pip install cryptography  ausführen.")

ITER = 310_000
SRC  = 'Analyse_Tool_DRIV_Rollkunstlauf.html'
USR  = 'zugang/benutzer.txt'
OUT  = 'login/index.html'

b64 = lambda b: base64.b64encode(b).decode()

if not os.path.exists(SRC): sys.exit(f"{SRC} fehlt – zuerst  python3 build.py  ausführen.")
if not os.path.exists(USR): sys.exit(f"{USR} fehlt – Benutzerliste anlegen (benutzername;passwort je Zeile).")

html = open(SRC, 'rb').read()

users, seen = [], set()
for ln, line in enumerate(open(USR, encoding='utf-8'), 1):
    line = line.strip()
    if not line or line.startswith('#'): continue
    if ';' not in line: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Format ist  benutzername;passwort")
    u, pw = (x.strip() for x in line.split(';', 1))
    u = u.lower()
    if not u or not pw: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Benutzername oder Passwort leer.")
    if len(pw) < 10: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Passwort für „{u}“ zu kurz (mindestens 10 Zeichen).")
    if u in seen: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Benutzername „{u}“ doppelt.")
    seen.add(u)
    users.append((u, pw))
if not users: sys.exit("zugang/benutzer.txt enthält keine Benutzer.")

K  = secrets.token_bytes(32)          # Inhaltsschlüssel
iv = secrets.token_bytes(12)
ct = AESGCM(K).encrypt(iv, html, None)

recs = []
for u, pw in users:
    salt = secrets.token_bytes(16)
    kek  = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(f"{u}:{pw}".encode())
    wiv  = secrets.token_bytes(12)
    recs.append({'h': hashlib.sha256(u.encode()).hexdigest(),
                 's': b64(salt), 'i': b64(wiv),
                 'w': b64(AESGCM(kek).encrypt(wiv, K, None))})

data = json.dumps({'iter': ITER, 'iv': b64(iv), 'ct': b64(ct), 'users': recs},
                  separators=(',', ':'))

page = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>DRIV Rollkunstlauf – Leistungsdaten-Analyse · Anmeldung</title>
<style>
:root{--ink:#1a2233;--sub:#5b6474;--line:#d9dee8;--acc:#1d4ed8;--bg:#f3f5f9;--err:#b3261e}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 30px rgba(20,30,60,.08);
      max-width:430px;width:100%;padding:34px 34px 26px}
h1{font-size:19px;margin:0 0 4px}
.sub{color:var(--sub);font-size:13.5px;margin:0 0 22px;line-height:1.5}
label{display:block;font-size:12.5px;font-weight:600;color:var(--sub);margin:14px 0 5px;text-transform:uppercase;letter-spacing:.04em}
input{width:100%;padding:11px 12px;font-size:15px;border:1px solid var(--line);border-radius:8px;background:#fbfcfe}
input:focus{outline:2px solid var(--acc);border-color:var(--acc)}
button{width:100%;margin-top:22px;padding:12px;font-size:15px;font-weight:700;color:#fff;background:var(--acc);
       border:0;border-radius:8px;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}
.err{display:none;color:var(--err);font-size:13.5px;margin-top:14px;font-weight:600}
.note{color:var(--sub);font-size:12px;margin-top:22px;line-height:1.5;border-top:1px solid var(--line);padding-top:14px}
</style>
</head>
<body>
<div class="card">
  <h1>DRIV Rollkunstlauf – Leistungsdaten-Analyse</h1>
  <p class="sub">Zugang nur für berechtigte Personen der Sportkommission und Trainer.
     Der Inhalt dieser Seite ist verschlüsselt und wird erst nach erfolgreicher Anmeldung entschlüsselt.</p>
  <form id="f">
    <label for="u">Benutzername</label>
    <input id="u" autocomplete="username" autocapitalize="none" autofocus required>
    <label for="p">Passwort</label>
    <input id="p" type="password" autocomplete="current-password" required>
    <button id="b" type="submit">Anmelden</button>
    <p class="err" id="e">Anmeldung fehlgeschlagen – Benutzername oder Passwort falsch.</p>
  </form>
  <p class="note">Zugang anfordern oder Passwort vergessen? Formlose E-Mail an
     <b>marcel.wagner&#64;w-dfs.de</b> (Sportkommission). Statistische Auswertung
     historischer Wettkampfdaten aus offiziellen RollArt-Protokollen – keine
     Nominierungsempfehlung.</p>
</div>
<script>
const DATA=__DATA__;
const B=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function sha256hex(s){const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('');}
document.getElementById('f').addEventListener('submit',async ev=>{
  ev.preventDefault();
  const btn=document.getElementById('b'),err=document.getElementById('e');
  err.style.display='none';btn.disabled=true;btn.textContent='Entschlüssele …';
  try{
    const u=document.getElementById('u').value.trim().toLowerCase();
    const pw=document.getElementById('p').value;
    const uh=await sha256hex(u);
    const r=DATA.users.find(x=>x.h===uh);
    if(!r)throw new Error('unbekannt');
    const km=await crypto.subtle.importKey('raw',new TextEncoder().encode(u+':'+pw),'PBKDF2',false,['deriveKey']);
    const kek=await crypto.subtle.deriveKey({name:'PBKDF2',salt:B(r.s),iterations:DATA.iter,hash:'SHA-256'},
      km,{name:'AES-GCM',length:256},false,['decrypt']);
    const K=await crypto.subtle.decrypt({name:'AES-GCM',iv:B(r.i)},kek,B(r.w));
    const ck=await crypto.subtle.importKey('raw',K,'AES-GCM',false,['decrypt']);
    const buf=await crypto.subtle.decrypt({name:'AES-GCM',iv:B(DATA.iv)},ck,B(DATA.ct));
    const doc=new TextDecoder().decode(buf);
    document.open();document.write(doc);document.close();
  }catch(e){
    err.style.display='block';btn.disabled=false;btn.textContent='Anmelden';
  }
});
</script>
</body>
</html>"""

os.makedirs('login', exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(page.replace('__DATA__', data))
open('login/.nojekyll', 'w').write('')
print(f"OK – {OUT} erzeugt ({os.path.getsize(OUT)/1e6:.2f} MB, {len(users)} Benutzer, AES-256-GCM, PBKDF2 {ITER:,} Iterationen)")
