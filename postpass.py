# Nachlauf-Pipeline: Konsistenz, Netto-TES, Namens-Kanonisierung, Kader, Checks
import json, unicodedata, re
from collections import Counter, defaultdict

seed=json.load(open('data/seed_v2.json'))
import os
_REGPATH=next(p for p in ('data/athleten_register.json','/home/claude/driv-dashboard/data/athleten_register.json') if os.path.exists(p))
REG=json.load(open(_REGPATH))['athleten']

# ---------- 1) Konsistenz / Faktor-Dedupe / tesOk ----------
part=nulled=0
for ev in seed:
    for k in ev['kategorien']:
        for r in k['rows']:
            if r['tes'] is None: r['tesOk']=False; continue
            if not r['total']: r['tesOk']=True; continue
            s=r['tes']+(r['pcs'] or 0)
            if -0.01<=s-r['total']<=12: r['tesOk']=True
            elif s<r['total']-0.5: r['tesOk']=False; part+=1
            else:
                done=False
                for f in (2,3,4):
                    if -0.01<=s/f-r['total']<=12:
                        r['tes']=round(r['tes']/f,2); r['pcs']=round((r['pcs'] or 0)/f,2)
                        r['nseg']=max(1,(r['nseg'] or f)//f); r['tesOk']=True; r['segs']=None; done=True; break
                if not done: r['tes']=None; r['pcs']=None; r['tesOk']=False; r['segs']=None; nulled+=1
print('Konsistenz: unvollständig',part,'| verworfen',nulled)

# ---------- 2) Einzeln benannte Paar-Zeilen ----------
p2pair={}
for a in REG:
    if ' / ' in a['name']:
        for p in a['name'].split(' / '): p2pair.setdefault(p,[]).append(a['name'])
rep=0
for ev in seed:
    for k in ev['kategorien']:
        if k['disziplin'] in ('Rolltanz','Paarlauf'):
            for r in k['rows']:
                if ' / ' not in r['name'] and r['name'] in p2pair and len(p2pair[r['name']])==1:
                    r['name']=p2pair[r['name']][0]; rep+=1
print('Paar-Zeilen repariert:',rep)

# ---------- 3) Netto-TES über Identität ----------
conv=0
for ev in seed:
    for k in ev['kategorien']:
        for r in k['rows']:
            if r.get('tesOk') and r['tes'] is not None and r['total'] and r['pcs'] is not None:
                raw=r['tes']; net=round(r['total']-r['pcs'],2); abz=round(raw-net,2)
                if -0.06<=abz<=12:
                    r['tesRaw']=raw; r['abzuege']=abz if abz>0.005 else 0.0; r['tes']=net; conv+=1
print('Netto-TES:',conv)

# ---------- 4) Namens-Kanonisierung ----------
def norm_tokens(s):
    s=unicodedata.normalize('NFD',s.lower())
    s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    for ch in ("'", '’', '´', '`'): s=s.replace(ch,'')   # Apostroph-Varianten (z. B. Nicolò/Nicolo'/Nicolo´)
    return tuple(sorted(s.replace('-',' ').replace('/',' ').replace('~',' ').split()))
def ed(a,b):
    if abs(len(a)-len(b))>1: return 2
    if len(a)>len(b): a,b=b,a
    prev=list(range(len(a)+1))
    for i,cb in enumerate(b,1):
        cur=[i]
        for j,ca in enumerate(a,1):
            cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
allrows=[(e,k,r) for e in seed for k in e['kategorien'] for r in k['rows']]
def apply_renames(rename):
    n=0
    for e,k,r in allrows:
        while r['name'] in rename and rename[r['name']]!=r['name']:
            r['name']=rename[r['name']]; n+=1
    return n
tot_renamed=0
# 4a) Vereinsreste
CLUBTAIL=re.compile(r'(\s+1\.)?(\s+(Kieler|Post|Neukölner|Krc Rolling))+$')
ren={}
for e,k,r in allrows:
    if ' / ' in r['name']: continue
    n2=CLUBTAIL.sub('',r['name']).strip()
    if n2!=r['name'] and len(n2.split())>=2: ren[r['name']]=n2
tot_renamed+=apply_renames(ren)
# 4b) Kader-Varianten (Token-Teilmenge + Aliasse), eindeutig
def build_kader_vars():
    allnames={r['name'] for _,_,r in allrows}
    ALIAS={'Asia Haspolat':[n for n in allnames if 'haspolat' in n.lower()],
     'Lilly Calderone':[n for n in allnames if 'caldarone' in n.lower() or 'calderone' in n.lower()],
     'Alisa Saya Dinerman':[n for n in allnames if 'dinerman' in n.lower()],
     'Lilly Ann Oppermann':[n for n in allnames if 'opperman' in n.lower()],
     'Pauline Rieder / Lennox Geiger':[n for n in allnames if ' / ' in n and 'rieder' in n.lower()]}
    out=[]
    for a in REG:
        isPair=' / ' in a['name']; t=set(norm_tokens(a['name'])); vars=[]
        for n in allnames:
            if (' / ' in n)!=isPair: continue
            nt=set(norm_tokens(n))
            if t==nt or (t<=nt and len(t)>=2) or (nt<=t and len(nt)>=2 and len(t&nt)>=2): vars.append(n)
        for al in ALIAS.get(a['name'],[]):
            if (' / ' in al)==isPair and al not in vars: vars.append(al)
        out.append({'name':a['name'],'gruppe':a.get('gruppe',''),'lv':a.get('lv',''),'varianten':sorted(set(vars))})
    return out
kader=build_kader_vars()
varowner=defaultdict(set)
for kk in kader:
    for v in kk['varianten']: varowner[v].add(kk['name'])
ren={v:next(iter(o)) for v,o in varowner.items() if len(o)==1 and v!=next(iter(o))}
tot_renamed+=apply_renames(ren)
# 4c) gleiche Normalform
cnt=Counter(r['name'] for _,_,r in allrows); names=sorted(cnt)
kadernames={k['name'] for k in kader}
def canonical(group):
    ks=[g for g in group if g in kadernames]
    return ks[0] if ks else sorted(group,key=lambda g:(-cnt[g],-len(g)))[0]
def cooccur(a,b):
    for e in seed:
        for k in e['kategorien']:
            ns={r['name'] for r in k['rows']}
            if a in ns and b in ns: return True
    return False
byn=defaultdict(list)
for n in names: byn[norm_tokens(n)].append(n)
ren={}
for grp in byn.values():
    if len(grp)>1:
        c=canonical(grp)
        for g in grp:
            if g!=c and not cooccur(g,c): ren[g]=c
tot_renamed+=apply_renames(ren)
# 4d) Kurzform -> eindeutige Langform
cnt=Counter(r['name'] for _,_,r in allrows); names=sorted(cnt)
nt={n:set(norm_tokens(n)) for n in names}
ren={}
for a in names:
    if ' / ' in a: continue
    tg=[b for b in names if b!=a and ' / ' not in b and len(nt[a])>=2 and nt[a]<nt[b]]
    if len(tg)==1 and not cooccur(a,tg[0]): ren[a]=tg[0]
tot_renamed+=apply_renames(ren)
# 4e) Tippfehler (1 Tokenpaar, ED<=1, len>=5, eindeutig)
cnt=Counter(r['name'] for _,_,r in allrows); names=sorted(cnt)
nt={n:set(norm_tokens(n)) for n in names}
cand=defaultdict(list)
for i,a in enumerate(names):
    if ' / ' in a: continue
    for b in names[i+1:]:
        if ' / ' in b: continue
        da,db=sorted(nt[a]-nt[b]),sorted(nt[b]-nt[a])
        if len(da)==1 and len(db)==1 and len(nt[a]&nt[b])>=1:
            x,y=da[0],db[0]
            if min(len(x),len(y))>=5 and ed(x,y)<=1:
                cand[a].append(b); cand[b].append(a)
ren={}
for a,bs in cand.items():
    if len(bs)==1 and a not in ren:
        b=bs[0]
        if b in ren: continue
        c=canonical([a,b]); o=b if c==a else a
        if not cooccur(o,c): ren[o]=c
tot_renamed+=apply_renames(ren)
print('Namens-Kanonisierung: Zeilen umbenannt:',tot_renamed)

# ---------- 5) Kategorie-Duplikate mergen ----------
merged=0
for e in seed:
    for k in e['kategorien']:
        byname={}; newrows=[]
        for r in k['rows']:
            t=byname.get(r['name'])
            if t is None: byname[r['name']]=r; newrows.append(r); continue
            a,b=t,r
            if (b.get('platz') is not None and a.get('platz') is None) or (b.get('total') and not a.get('total')):
                a,b=b,a; idx=newrows.index(t); newrows[idx]=a; byname[r['name']]=a
            for f in ('platz','total','nat'):
                if a.get(f) in (None,'') and b.get(f) not in (None,''): a[f]=b[f]
            if a.get('tes') is None and b.get('tes') is not None:
                for f in ('tes','pcs','nseg','segs','tesOk','tesRaw','abzuege'): a[f]=b.get(f)
            merged+=1
        if len(newrows)!=len(k['rows']):
            k['rows']=sorted(newrows,key=lambda r:(r['platz'] is None, r['platz'] or 0))
print('Kategorie-Duplikate gemergt:',merged)

# ---------- 5b) Zwischenstands-Zeilen entwerten ----------
# Teilen sich zwei Athleten einen Platz und einem fehlt ein Segment (z. B. nur Kurzprogramm
# gelaufen, danach zurückgezogen), stammt dessen Platz aus dem Zwischenstand – er wird als
# „nicht im Endklassement" markiert (platz=None, tesOk=False), damit weder Referenzkurven
# noch Bestwerte verfälscht werden. Echte Punktgleichheit (beide vollständig) bleibt unberührt.
zw=0
for e in seed:
    for k in e['kategorien']:
        plc=Counter(r['platz'] for r in k['rows'] if r.get('platz') is not None)
        dup={p:n for p,n in plc.items() if n>1}
        if not dup: continue
        # Sind (fast) alle Plätze mehrfach vergeben, handelt es sich um zusammengelegte
        # Gruppen-/Jahrgangswertungen ohne erkannten Marker – nicht antasten.
        if len(dup)/len(plc)>0.5: continue
        for p in dup:
            rows=[r for r in k['rows'] if r.get('platz')==p]
            grpmax=max((r.get('nseg') or 0) for r in rows)
            for r in rows:
                if (r.get('nseg') or 0)<grpmax:
                    r['platz']=None; r['tesOk']=False; zw+=1
print('Zwischenstands-Zeilen entwertet (Platz aus Kurzprogramm-Zwischenstand):',zw)

# ---------- 5c) Über Jahrgangs-Gruppen verstreute Segmente heilen ----------
# Bei Protokollen mit uneinheitlichen Gruppen-Markern können Segment-Zeilen einer Person in
# einer anderen (Jahrgangs-)Teilwertung landen als ihr Endresultat. Solche verwaisten
# Segment-Zeilen (ohne Platz und Gesamtwert) werden in die Endresultat-Zeile derselben Person
# im selben Event/derselben Klasse zurückgeführt (mit Kontrollgleichungs-Guard) und entfernt.
heal=0
for e in seed:
    bykey=defaultdict(list)
    for k in e['kategorien']:
        bykey[(k['disziplin'],k['klasse'],k.get('gender',''))].append(k)
    for key,kats in bykey.items():
        if len(kats)<2: continue
        fin={}
        for k in kats:
            for r in k['rows']:
                if r.get('total') is not None: fin[r['name']]=r
        for k in kats:
            keep=[]
            for r in k['rows']:
                t=fin.get(r['name'])
                if (r.get('total') is None and r.get('platz') is None and t is not None and t is not r
                    and r.get('tes') is not None and r.get('nseg')):
                    newTes=round((t.get('tes') or 0)+r['tes'],2)
                    newPcs=round((t.get('pcs') or 0)+(r.get('pcs') or 0),2)
                    dedsum=round(sum(sx['ded'] for sx in (t.get('segs') or [])+(r.get('segs') or [])),2)
                    sraw=newTes+newPcs
                    if (t.get('total') is None or -0.01<=sraw-t['total']<=12.01
                        or abs(sraw-dedsum-t['total'])<=0.06):
                        t['tes']=newTes; t['pcs']=newPcs; t['nseg']=(t.get('nseg') or 0)+r['nseg']
                        if r.get('segs'): t['segs']=(t.get('segs') or [])+r['segs']
                        # Konsistenz + Netto-TES für die geheilte Zeile nachziehen
                        if t.get('total') and t['tes'] is not None:
                            ssum=t['tes']+(t['pcs'] or 0)
                            if -0.01<=ssum-t['total']<=12:
                                t['tesOk']=True
                                raw=t['tes']; net=round(t['total']-(t['pcs'] or 0),2); abz=round(raw-net,2)
                                if -0.06<=abz<=12:
                                    t['tesRaw']=raw; t['abzuege']=abz if abz>0.005 else 0.0; t['tes']=net
                        heal+=1
                        continue
                keep.append(r)
            k['rows']=keep
    e['kategorien']=[k for k in e['kategorien'] if k['rows']]
print('Verstreute Segment-Zeilen zurückgeführt:',heal)

json.dump(seed,open('data/seed_v2.json','w'),ensure_ascii=False,indent=1)

# ---------- 6) Kader-Datei final ----------
allrows=[(e,k,r) for e in seed for k in e['kategorien'] for r in k['rows']]
kader=build_kader_vars()
json.dump(kader,open('data/kader.json','w'),ensure_ascii=False,indent=1)
print('Kader zugeordnet:',sum(1 for k in kader if k['varianten']),'von',len(kader))

# ---------- 7) Checks ----------
vmap={k['name']:set(k['varianten'])|{k['name']} for k in kader}
EVMAP={'wc_gap':'AWC Semi-Final Garmisch 2026','wc_fin':'AWC Finale Cesena 2026','wc_ba':'AWC Buenos Aires 2026',
 'dm_stade':'Deutsche Meisterschaften Stade 2026','dp_kuer':'Int. Deutschland-Pokal Freiburg 2026'}
ok=0; bad=[]
for a in REG:
    names=vmap.get(a['name'],{a['name']})
    for ir in a.get('international',[]):
        evn=EVMAP.get(ir.get('event_id'))
        if not evn: continue
        pts=ir.get('punkte'); pl=ir.get('platz')
        if pts is None and pl is None: continue
        hit=0
        for e in seed:
            if e['name']!=evn: continue
            for kk in e['kategorien']:
                for r in kk['rows']:
                    if r['name'] in names and ((pts is not None and r['total'] is not None and abs(r['total']-pts)<0.02) or (pts is None and r['platz']==pl)): hit=1
        ok+=hit
        if not hit: bad.append((a['name'],evn))
inv=dups=0
for ev in seed:
    for k in ev['kategorien']:
        c=Counter(r['name'] for r in k['rows'])
        dups+=sum(1 for x in c.values() if x>1)
        for r in k['rows']:
            if r.get('tesOk') and r['tes'] is not None and r['total'] and r['pcs'] is not None:
                if abs(r['tes']+r['pcs']-r['total'])>0.03: inv+=1
print(f'CHECKS: Register {ok} OK / {len(bad)} fehlen {bad[:4]} | Invarianten {inv} | Duplikate {dups}')
print('Ergebnisse:',sum(len(k["rows"]) for e in seed for k in e["kategorien"]),'| Events:',len(seed))
