#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
protect.py – erzeugt die passwortgeschützte Login-Seite des Dashboards
             (inkl. Online-Benutzerverwaltung für Verwalter).

Eingaben:
  Analyse_Tool_DRIV_Rollkunstlauf.html   (fertig gebautes Dashboard)
  zugang/benutzer.txt                    (eine Zeile je Benutzer:
                                          benutzername;passwort
                                          benutzername;passwort;admin   ← Verwalter)
Ausgabe:
  login/index.html – eigenständige Login-Seite; das komplette Dashboard liegt
                     darin AES-256-GCM-verschlüsselt.

Verwalter (admin) können sich nach dem Login in die Benutzerverwaltung
schalten: Personen anlegen/ändern/entfernen, die Seite wird komplett im
Browser neu verschlüsselt und wahlweise per GitHub-API direkt veröffentlicht
oder als Datei heruntergeladen.

Technik: Inhaltsschlüssel K (AES-256-GCM) je Benutzer mit PBKDF2-SHA256
(310.000 Iterationen, benutzername:passwort) eingepackt; Verwalter erhalten
zusätzlich den Verwaltungsschlüssel KA, mit dem die Benutzerliste
verschlüsselt ist. Benutzernamen stehen nur als SHA-256-Hash in der Seite.

Aufruf:  python3 protect.py        (im Repository-Hauptordner)
"""
import base64, hashlib, json, os, secrets, sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    sys.exit("Fehlende Bibliothek: bitte einmalig  pip install cryptography  ausführen.")

ITER  = 310_000
SRC   = 'Analyse_Tool_DRIV_Rollkunstlauf.html'
USR   = 'zugang/benutzer.txt'
OUT   = 'login/index.html'
OWNER = 'marcelwagner-afk'
REPO  = 'DRIV-Rollkunstlauf_Leistungsdaten_Analyse'

b64 = lambda b: base64.b64encode(b).decode()

if not os.path.exists(SRC): sys.exit(f"{SRC} fehlt – zuerst  python3 build.py  ausführen.")
if not os.path.exists(USR): sys.exit(f"{USR} fehlt – Benutzerliste anlegen (benutzername;passwort[;admin] je Zeile).")

html = open(SRC, 'rb').read()

userlist, seen = [], set()
for ln, line in enumerate(open(USR, encoding='utf-8'), 1):
    line = line.strip()
    if not line or line.startswith('#'): continue
    parts = [x.strip() for x in line.split(';')]
    if len(parts) < 2: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Format ist  benutzername;passwort[;admin]")
    u, pw = parts[0].lower(), parts[1]
    adm = len(parts) > 2 and parts[2].lower() == 'admin'
    if not u or not pw: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Benutzername oder Passwort leer.")
    if len(pw) < 10: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Passwort für „{u}“ zu kurz (mindestens 10 Zeichen).")
    if u in seen: sys.exit(f"zugang/benutzer.txt Zeile {ln}: Benutzername „{u}“ doppelt.")
    seen.add(u)
    userlist.append({'u': u, 'pw': pw, 'admin': adm})
if not userlist: sys.exit("zugang/benutzer.txt enthält keine Benutzer.")
if not any(x['admin'] for x in userlist):
    sys.exit("Kein Verwalter definiert – mindestens eine Zeile braucht  ;admin  am Ende (z. B. marcel).")

K  = secrets.token_bytes(32)   # Inhaltsschlüssel
KA = secrets.token_bytes(32)   # Verwaltungsschlüssel (nur Verwalter)
iv = secrets.token_bytes(12)
ct = AESGCM(K).encrypt(iv, html, None)

recs = []
for x in userlist:
    salt = secrets.token_bytes(16)
    kek  = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(f"{x['u']}:{x['pw']}".encode())
    wiv  = secrets.token_bytes(12)
    rec  = {'h': hashlib.sha256(x['u'].encode()).hexdigest(),
            's': b64(salt), 'i': b64(wiv),
            'w': b64(AESGCM(kek).encrypt(wiv, K, None))}
    if x['admin']:
        wiv2 = secrets.token_bytes(12)
        rec.update({'a': 1, 'i2': b64(wiv2), 'w2': b64(AESGCM(kek).encrypt(wiv2, KA, None))})
    recs.append(rec)

miv  = secrets.token_bytes(12)
mgmt = AESGCM(KA).encrypt(miv, json.dumps(userlist, ensure_ascii=False).encode(), None)

TPL = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>DRIV Rollkunstlauf – Leistungsdaten-Analyse · Anmeldung</title>
<style>
:root{--ink:#1a2233;--sub:#5b6474;--line:#d9dee8;--acc:#1d4ed8;--bg:#f3f5f9;--err:#b3261e;--ok:#166534}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);
     min-height:100vh;display:flex;align-items:flex-start;justify-content:center;padding:40px 18px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 30px rgba(20,30,60,.08);
      max-width:460px;width:100%;padding:32px 32px 24px}
.card.wide{max-width:760px}
h1{font-size:19px;margin:0 0 4px}
h2{font-size:16px;margin:20px 0 8px}
.sub{color:var(--sub);font-size:13.5px;margin:0 0 20px;line-height:1.5}
label{display:block;font-size:12.5px;font-weight:600;color:var(--sub);margin:14px 0 5px;text-transform:uppercase;letter-spacing:.04em}
input,select{padding:10px 11px;font-size:14.5px;border:1px solid var(--line);border-radius:8px;background:#fbfcfe;width:100%}
input:focus{outline:2px solid var(--acc);border-color:var(--acc)}
button{padding:11px 16px;font-size:14.5px;font-weight:700;color:#fff;background:var(--acc);border:0;border-radius:8px;cursor:pointer}
button.sec{background:#fff;color:var(--acc);border:1.5px solid var(--acc)}
button.mini{padding:6px 10px;font-size:12.5px;font-weight:600}
button.warn{background:#fff;color:var(--err);border:1.5px solid var(--err)}
button:disabled{opacity:.55;cursor:wait}
.err{display:none;color:var(--err);font-size:13.5px;margin-top:14px;font-weight:600}
.ok{color:var(--ok);font-size:13.5px;margin-top:14px;font-weight:600}
.note{color:var(--sub);font-size:12px;margin-top:20px;line-height:1.55;border-top:1px solid var(--line);padding-top:13px}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13.5px}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--sub);text-align:left;padding:6px 6px}
td{padding:5px 6px;vertical-align:middle}
td input{padding:7px 9px;font-size:13.5px}
.rowbtns{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.full{width:100%}
.tblwrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0}
.tblwrap table{min-width:560px}
</style>
</head>
<body>
<div class="card" id="card">
  <h1>DRIV Rollkunstlauf – Leistungsdaten-Analyse</h1>
  <p class="sub">Zugang nur für berechtigte Personen der Sportkommission und Trainer.
     Der Inhalt dieser Seite ist verschlüsselt und wird erst nach erfolgreicher Anmeldung entschlüsselt.</p>
  <form id="f">
    <label for="u">Benutzername</label>
    <input id="u" autocomplete="username" autocapitalize="none" autofocus required>
    <label for="p">Passwort</label>
    <input id="p" type="password" autocomplete="current-password" required>
    <button id="b" type="submit" class="full" style="margin-top:22px">Anmelden</button>
    <p class="err" id="e">Anmeldung fehlgeschlagen – Benutzername oder Passwort falsch.</p>
  </form>
  <p class="note">Zugang anfordern oder Passwort vergessen? Formlose E-Mail an
     <b>marcel.wagner&#64;w-dfs.de</b> (Sportkommission). Statistische Auswertung
     historischer Wettkampfdaten aus offiziellen RollArt-Protokollen – keine
     Nominierungsempfehlung.</p>
</div>
<script>
'use strict';
const DATA=__DATA__;
const OWNER='__OWNER__',REPO='__REPO__',BRANCH='main';
const ENC=new TextEncoder(),DEC=new TextDecoder();
const B=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
function b64(u8){let s='';for(let i=0;i<u8.length;i+=32768)s+=String.fromCharCode.apply(null,u8.subarray(i,i+32768));return btoa(s);}
async function sha256hex(s){const d=await crypto.subtle.digest('SHA-256',ENC.encode(s));
  return Array.from(new Uint8Array(d)).map(x=>x.toString(16).padStart(2,'0')).join('');}
async function keyFrom(u,pw,salt){
  const km=await crypto.subtle.importKey('raw',ENC.encode(u+':'+pw),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt:salt,iterations:DATA.iter,hash:'SHA-256'},
    km,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
}
const rawKey=(K,use)=>crypto.subtle.importKey('raw',K,'AES-GCM',false,use);
let DASH=null,LIST=null,IS_ADMIN=false;

document.getElementById('f').addEventListener('submit',async ev=>{
  ev.preventDefault();
  const btn=document.getElementById('b'),err=document.getElementById('e');
  err.style.display='none';btn.disabled=true;btn.textContent='Entschlüssele …';
  try{
    const u=document.getElementById('u').value.trim().toLowerCase();
    const pw=document.getElementById('p').value;
    const uh=await sha256hex(u);
    const r=DATA.users.find(x=>x.h===uh);
    if(!r)throw new Error('x');
    const kek=await keyFrom(u,pw,B(r.s));
    const K=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:B(r.i)},kek,B(r.w)));
    const ck=await rawKey(K,['decrypt']);
    DASH=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:B(DATA.iv)},ck,B(DATA.ct)));
    if(r.a&&r.w2){
      const KA=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:B(r.i2)},kek,B(r.w2)));
      const ak=await rawKey(KA,['decrypt']);
      LIST=JSON.parse(DEC.decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:B(DATA.mi)},ak,B(DATA.mg))));
      IS_ADMIN=true;showChooser();
    } else openDash();
  }catch(x){err.style.display='block';btn.disabled=false;btn.textContent='Anmelden';}
});
function openDash(){const doc=DEC.decode(DASH);document.open();document.write(doc);document.close();}

/* ---------- Verwalter-Ansichten ---------- */
function el(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt!=null)n.textContent=txt;return n;}
function showChooser(){
  const c=document.getElementById('card');c.classList.remove('wide');c.replaceChildren();
  c.append(el('h1',null,'Angemeldet als Verwalter'));
  c.append(el('p','sub','Dashboard öffnen – oder Benutzerzugänge online verwalten.'));
  const b1=el('button','full','Dashboard öffnen');b1.addEventListener('click',openDash);
  const b2=el('button','sec full','Benutzerverwaltung');b2.style.marginTop='10px';b2.addEventListener('click',()=>showAdmin());
  c.append(b1,b2);
}
function pwRandom(){
  const A='abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const r=crypto.getRandomValues(new Uint32Array(12));
  return 'DRIV-'+Array.from(r).map(x=>A[x%A.length]).join('');
}
function showAdmin(msg){
  const c=document.getElementById('card');c.classList.add('wide');c.replaceChildren();
  c.append(el('h1',null,'Benutzerverwaltung'));
  c.append(el('p','sub','Eine Zeile je Person. Passwort ändern = Feld überschreiben · Zugang entziehen = Zeile entfernen · '+
    'mindestens 10 Zeichen je Passwort · mindestens ein Verwalter. Änderungen gelten erst nach „Speichern & veröffentlichen“.'));
  const tb=el('table');const th=el('tr');
  ['Benutzername','Passwort','Verwalter','',''].forEach(x=>th.append(el('th',null,x)));tb.append(th);
  LIST.forEach((x,idx)=>{
    const tr=el('tr');
    const t1=el('td');const iu=el('input');iu.value=x.u;iu.addEventListener('input',()=>x.u=iu.value.trim().toLowerCase());t1.append(iu);
    const t2=el('td');const ip=el('input');ip.value=x.pw;ip.addEventListener('input',()=>x.pw=ip.value);t2.append(ip);
    const t3=el('td');const ck=el('input');ck.type='checkbox';ck.checked=!!x.admin;ck.style.width='auto';
      ck.addEventListener('change',()=>x.admin=ck.checked);t3.append(ck);
    const t4=el('td');const bg=el('button','mini sec','Zufallspasswort');
      bg.type='button';bg.addEventListener('click',()=>{x.pw=pwRandom();ip.value=x.pw;});t4.append(bg);
    const t5=el('td');const bd=el('button','mini warn','Entfernen');
      bd.type='button';bd.addEventListener('click',()=>{LIST.splice(idx,1);showAdmin();});t5.append(bd);
    tr.append(t1,t2,t3,t4,t5);tb.append(tr);
  });
  const tw=el('div','tblwrap');tw.append(tb);c.append(tw);
  const add=el('button','mini sec','+ Person hinzufügen');
  add.addEventListener('click',()=>{LIST.push({u:'',pw:pwRandom(),admin:false});showAdmin();});
  c.append(add);
  const row=el('div','rowbtns');
  const save=el('button',null,'Speichern & veröffentlichen');
  save.addEventListener('click',()=>doSave(save));
  const back=el('button','sec','Zurück');back.addEventListener('click',showChooser);
  row.append(save,back);c.append(row);
  const st=el('p','err');st.id='ast';c.append(st);
  if(msg&&typeof msg==='string'){const ok=el('p','ok',msg);c.append(ok);}
  c.append(el('p','note','Veröffentlichen erzeugt die Seite mit frischer Verschlüsselung komplett neu. '+
    'Tipp: Nach Änderungen zusätzlich „benutzer.txt herunterladen“ und die Datei lokal im Ordner zugang/ ersetzen, '+
    'damit künftige Neu-Verschlüsselungen am Rechner dieselbe Liste verwenden.'));
}
function adminErr(t){const n=document.getElementById('ast');n.textContent=t;n.style.display='block';}
function checkList(){
  const names=new Set();
  for(const x of LIST){
    if(!/^[a-z0-9._-]{2,}$/.test(x.u))return 'Benutzername „'+x.u+'“ ungültig (Kleinbuchstaben/Ziffern/._-, min. 2 Zeichen).';
    if(x.pw.length<10)return 'Passwort für „'+x.u+'“ zu kurz (mindestens 10 Zeichen).';
    if(x.pw.includes(';'))return 'Passwort für „'+x.u+'“ darf kein Semikolon enthalten.';
    if(names.has(x.u))return 'Benutzername „'+x.u+'“ doppelt.';
    names.add(x.u);
  }
  if(!LIST.length)return 'Die Liste ist leer.';
  if(!LIST.some(x=>x.admin))return 'Mindestens eine Person muss Verwalter sein.';
  return null;
}
async function regenerate(){
  const K=crypto.getRandomValues(new Uint8Array(32));
  const KA=crypto.getRandomValues(new Uint8Array(32));
  const iv=crypto.getRandomValues(new Uint8Array(12));
  const ct=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:iv},await rawKey(K,['encrypt']),DASH));
  const users=[];
  for(const x of LIST){
    const salt=crypto.getRandomValues(new Uint8Array(16));
    const kek=await keyFrom(x.u,x.pw,salt);
    const wiv=crypto.getRandomValues(new Uint8Array(12));
    const rec={h:await sha256hex(x.u),s:b64(salt),i:b64(wiv),
      w:b64(new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:wiv},kek,K)))};
    if(x.admin){
      const wiv2=crypto.getRandomValues(new Uint8Array(12));
      rec.a=1;rec.i2=b64(wiv2);
      rec.w2=b64(new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:wiv2},kek,KA)));
    }
    users.push(rec);
  }
  const miv=crypto.getRandomValues(new Uint8Array(12));
  const mg=b64(new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:miv},
    await rawKey(KA,['encrypt']),ENC.encode(JSON.stringify(LIST)))));
  const data={iter:DATA.iter,iv:b64(iv),ct:b64(ct),users:users,mi:b64(miv),mg:mg,tpl:DATA.tpl};
  return DEC.decode(B(DATA.tpl)).split('__DA'+'TA__').join(JSON.stringify(data));
}
async function doSave(btn){
  const bad=checkList(); if(bad){adminErr(bad);return;}
  btn.disabled=true;btn.textContent='Verschlüssele …';
  let page;
  try{page=await regenerate();}
  catch(x){adminErr('Fehler beim Verschlüsseln: '+x);btn.disabled=false;btn.textContent='Speichern & veröffentlichen';return;}
  showPublish(page);
}
function showPublish(page){
  const c=document.getElementById('card');c.classList.add('wide');c.replaceChildren();
  c.append(el('h1',null,'Neue Login-Seite ist fertig verschlüsselt'));
  c.append(el('p','sub','Jetzt veröffentlichen – direkt online (empfohlen) oder per Datei.'));
  c.append(el('h2',null,'A) Direkt auf GitHub veröffentlichen'));
  const lw=el('div');lw.append(el('label',null,'GitHub-Zugriffsschlüssel (Fine-grained Token, nur Contents/Read-write für dieses Repository)'));
  const it=el('input');it.type='password';it.placeholder='github_pat_…';
  try{const t=localStorage.getItem('driv_pat');if(t)it.value=t;}catch(x){}
  lw.append(it);c.append(lw);
  const rw=el('div');rw.style.margin='8px 0';
  const ckm=el('input');ckm.type='checkbox';ckm.style.width='auto';ckm.id='ckm';
  try{ckm.checked=!!localStorage.getItem('driv_pat');}catch(x){}
  const lb=el('label');lb.htmlFor='ckm';lb.style.display='inline';lb.style.textTransform='none';
  lb.style.marginLeft='6px';lb.textContent='Schlüssel auf diesem Gerät merken';
  rw.append(ckm,lb);c.append(rw);
  const bp=el('button',null,'Jetzt veröffentlichen');
  bp.addEventListener('click',async()=>{
    const tok=it.value.trim();
    if(!tok){st.textContent='Bitte Zugriffsschlüssel eingeben (Anleitung siehe unten).';st.style.display='block';return;}
    bp.disabled=true;bp.textContent='Veröffentliche …';st.style.display='none';
    try{
      try{if(ckm.checked)localStorage.setItem('driv_pat',tok);else localStorage.removeItem('driv_pat');}catch(x){}
      await publish(page,tok);
      showAdmin('Veröffentlicht ✓ – die Login-Seite ist in 1–2 Minuten mit der neuen Benutzerliste live.');
      return;
    }catch(x){st.textContent='Veröffentlichen fehlgeschlagen: '+x.message+' – alternativ Weg B nutzen.';st.style.display='block';}
    bp.disabled=false;bp.textContent='Jetzt veröffentlichen';
  });
  c.append(bp);
  c.append(el('h2',null,'B) Oder: Datei herunterladen und selbst hochladen'));
  const rb=el('div','rowbtns');
  const bd=el('button','sec','index.html herunterladen');
  bd.addEventListener('click',()=>download('index.html',page));
  const bt=el('button','sec','benutzer.txt herunterladen');
  bt.addEventListener('click',()=>{
    const txt='# Benutzerliste – Stand aus der Online-Verwaltung\\n'+
      LIST.map(x=>x.u+';'+x.pw+(x.admin?';admin':'')).join('\\n')+'\\n';
    download('benutzer.txt',txt);
  });
  rb.append(bd,bt);c.append(rb);
  c.append(el('p','sub','Hochladen: GitHub-Repository öffnen → „Add file → Upload files“ → die heruntergeladene index.html hineinziehen → „Commit changes“.'));
  const back=el('button','sec','Zurück zur Verwaltung');back.addEventListener('click',()=>showAdmin());
  c.append(back);
  const st=el('p','err');c.append(st);
  c.append(el('p','note','Zugriffsschlüssel einmalig erstellen: github.com → Profilbild → Settings → Developer settings → '+
    'Personal access tokens → Fine-grained tokens → Generate new token → Repository access: nur „'+REPO+'“ → '+
    'Permissions: Contents = Read and write. Der Schlüssel bleibt ausschließlich in Deinem Browser.'));
}
function download(name,text){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
  a.download=name;document.body.append(a);a.click();a.remove();
}
async function publish(page,tok){
  const hd={'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
  const base='https://api.github.com/repos/'+OWNER+'/'+REPO+'/contents/';
  let sha=null;
  const ls=await fetch(base+'?ref='+BRANCH,{headers:hd});
  if(ls.status===401||ls.status===403)throw new Error('Zugriffsschlüssel ungültig oder ohne Berechtigung ('+ls.status+')');
  if(ls.ok){const j=await ls.json();const f=(Array.isArray(j)?j:[]).find(x=>x.name==='index.html');if(f)sha=f.sha;}
  const body={message:'Benutzerverwaltung: Login-Seite aktualisiert',branch:BRANCH,
              content:b64(ENC.encode(page))};
  if(sha)body.sha=sha;
  const r=await fetch(base+'index.html',{method:'PUT',headers:hd,body:JSON.stringify(body)});
  if(!r.ok){let m='HTTP '+r.status;try{m+=' – '+(await r.json()).message;}catch(x){}throw new Error(m);}
}
</script>
</body>
</html>"""

TPL = TPL.replace('__OWNER__', OWNER).replace('__REPO__', REPO)
tpl_b64 = b64(TPL.encode())
data = json.dumps({'iter': ITER, 'iv': b64(iv), 'ct': b64(ct), 'users': recs,
                   'mi': b64(miv), 'mg': b64(mgmt), 'tpl': tpl_b64},
                  separators=(',', ':'))

page = TPL.replace('__DATA__', data)

os.makedirs('login', exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(page)
open('login/.nojekyll', 'w').write('')
n_adm = sum(1 for x in userlist if x['admin'])
print(f"OK – {OUT} erzeugt ({os.path.getsize(OUT)/1e6:.2f} MB, {len(userlist)} Benutzer, davon {n_adm} Verwalter, AES-256-GCM, PBKDF2 {ITER:,})")
