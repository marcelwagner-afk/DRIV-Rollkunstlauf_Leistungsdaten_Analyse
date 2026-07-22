#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quercheck: Detail-Blätter (details_raw.json) gegen die Ergebnislisten (seed_v2.json).
Matcht jedes Blatt auf die kanonische Athleten-Zeile des Events und prüft
Element-Score gegen Segment-TES bzw. tesRaw der Rangliste."""
import json, re, unicodedata
from collections import defaultdict, Counter

ALIASTOK={'caldarone':'calderone','opperman':'oppermann'}
def norm_tokens(s):
    s=unicodedata.normalize('NFD',s.lower())
    s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    for ch in ("'", '’', '´', '`'): s=s.replace(ch,'')
    toks=[ALIASTOK.get(t,t) for t in s.replace('-',' ').replace('/',' ').replace('~',' ').split()]
    return tuple(sorted(toks))

seed=json.load(open('data/seed_v2.json'))
det=json.load(open('data/details_raw.json'))

# Event-Index: normtokens -> kanonischer Name (+ Zeilenliste)
evmap={}
for ev in seed:
    m=defaultdict(list)
    for k in ev['kategorien']:
        for r in k['rows']:
            m[norm_tokens(r['name'])].append((k,r))
    evmap[ev['name']]={'map':m,'ev':ev}

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

DISMAP={'Free Skating':'Kürlaufen','Solo Dance':'Solotanz','Couple Dance':'Rolltanz','Pairs':'Paarlauf'}
def sheet_dis(s):
    if s.get('cat'): return DISMAP.get(s['cat']['dis'])
    sep=(' / ' in s['name']) or (' - ' in s['name'])
    h=s.get('hint')
    if h=='pairs': return 'Paarlauf'
    if h=='dance': return 'Rolltanz' if sep else 'Solotanz'
    return 'Paarlauf' if sep else 'Kürlaufen'

def find(evname,rawname,want_dis=None):
    e=evmap.get(evname)
    if not e: return None,None
    nt=norm_tokens(rawname)
    def rowsfor(key):
        rows=e['map'].get(key,[])
        if want_dis:
            rr=[x for x in rows if x[0]['disziplin']==want_dis]
            return rr if rr else rows
        return rows
    rows=rowsfor(nt)
    if rows: return rows[0]
    # Teilmengen-Match (z. B. abgeschnittene Paarnamen, Zusatztoken)
    best=None; bestn=0
    for key in e['map']:
        ks=set(key); ns=set(nt)
        if (ks<=ns or ns<=ks) and len(ks&ns)>=2:
            if len(ks&ns)>bestn:
                r=rowsfor(key)
                if r: bestn=len(ks&ns); best=r[0]
    if best: return best
    # Fuzzy: gleiche Tokenzahl, Summe der Editierdistanzen <=2, je Token <=1
    cands=[]
    for key in e['map']:
        if len(key)!=len(nt) or len(nt)<2: continue
        d=sum(ed(a,b) for a,b in zip(key,nt))
        if d<=2 and all(ed(a,b)<=1 for a,b in zip(key,nt)):
            r=rowsfor(key)
            if r: cands.append((d,r[0]))
    if len(cands)>=1:
        cands.sort(key=lambda x:x[0])
        if len(cands)==1 or cands[0][0]<cands[1][0]: return cands[0][1]
    return None,None

match=miss=0; tesok=tesbad=0; misslist=Counter(); badlist=[]
segcnt=Counter()
for s in det:
    nm=s['name'].replace(' - ',' / ')
    k,r=find(s['event'],nm,sheet_dis(s))
    if r is None:
        miss+=1; misslist[(s['event'],s['name'])]+=1; continue
    match+=1
    s['canon']=r['name']; s['dis']=k['disziplin']; s['klasse']=k['klasse']; s['gender']=k.get('gender','')
    # TES-Quercheck: Element-Score = Brutto-Segment-TES
    if s['elemScore'] is not None:
        cands=[]
        segs=r.get('segs') or []
        for sg in segs: cands.append(round(sg['tes'],2))
        if r.get('tesRaw') is not None: cands.append(round(r['tesRaw'],2))
        if r.get('tes') is not None: cands.append(round(r['tes'],2))
        if any(abs(s['elemScore']-c)<=0.03 for c in cands) or (len(segs)==0 and r.get('tes') is None):
            tesok+=1
        else:
            # Summe zweier Blätter = tesRaw? (2-Segment-Kategorien)
            tesbad+=1
            if len(badlist)<12: badlist.append((s['event'],s['name'],s['elemScore'],cands[:4]))
print('Blätter gematcht:',match,'| ohne Match:',miss)
print('TES-Quercheck OK (vor Dedup):',tesok,'| offen:',tesbad)
print('häufigste Nicht-Matches:',misslist.most_common(10))

# ---------- Dedup: doppelte Blätter (Doppel-PDFs, REVISED-Fassungen) ----------
def segtes_ok(s,r):
    if s['elemScore'] is None: return False
    cands=[round(sg['tes'],2) for sg in (r.get('segs') or [])]
    if r.get('tesRaw') is not None: cands.append(round(r['tesRaw'],2))
    if r.get('tes') is not None: cands.append(round(r['tes'],2))
    return any(abs(s['elemScore']-c)<=0.03 for c in cands)

groups=defaultdict(list)
for s in det:
    key=(s['event'],s.get('canon') or s['name'],s.get('dis'),(s['cat'] or {}).get('seg'))
    groups[key].append(s)
kept=[]; drop_ident=0; drop_rev=0
for key,v in groups.items():
    if len(v)==1: kept+=v; continue
    # identische Scores zusammenfassen
    seen={}
    for s in v: seen.setdefault(round(s['elemScore'] or -1,2),s)
    uniq=list(seen.values()); drop_ident+=len(v)-len(uniq)
    if len(uniq)==1: kept+=uniq; continue
    # REVISED-Fall: die zur Rangliste passende Fassung gewinnt, sonst letzte
    e=evmap.get(key[0]); r=None
    if e:
        rows=e['map'].get(norm_tokens(key[1])) or []
        rr=[x for x in rows if not key[2] or x[0]['disziplin']==key[2]]
        if rr or rows: r=(rr or rows)[0][1]
    good=[s for s in uniq if r is not None and segtes_ok(s,r)]
    if len(good)>=1: kept.append(good[-1]); drop_rev+=len(uniq)-1
    else: kept.append(uniq[-1]); drop_rev+=len(uniq)-1
det=kept
def rowfor(evname,canon,dis):
    e=evmap.get(evname)
    if not e: return None
    rows=e['map'].get(norm_tokens(canon)) or []
    rr=[x for x in rows if not dis or x[0]['disziplin']==dis]
    return (rr or rows or [(None,None)])[0][1]
print('Dedup: identisch entfernt',drop_ident,'| Fassungen entschieden',drop_rev,'| verbleiben',len(det))

tesok=tesbad=tesna=0; badlist=[]
for s in det:
    if 'canon' not in s or s['elemScore'] is None: continue
    r=rowfor(s['event'],s['canon'],s.get('dis'))
    if r is None: tesna+=1; continue
    cands=[round(sg['tes'],2) for sg in (r.get('segs') or [])]
    if r.get('tesRaw') is not None: cands.append(round(r['tesRaw'],2))
    if r.get('tes') is not None: cands.append(round(r['tes'],2))
    if not cands: tesna+=1; continue
    if any(abs(s['elemScore']-c)<=0.03 for c in cands): tesok+=1
    else:
        tesbad+=1
        if len(badlist)<8:
            badlist.append((s['event'],s['name'],(s['cat'] or {}).get('seg'),s['elemScore'],cands[:5]))
print('TES-Quercheck nach Dedup OK:',tesok,'| offen:',tesbad,'| nicht prüfbar (keine Segmentwerte in Rangliste):',tesna)
for x in badlist: print('  ',x)
json.dump(det,open('data/details_matched.json','w'),ensure_ascii=False)

# Zwei-Blätter-Summe je Athlet+Event vs. tesRaw
bysk=defaultdict(list)
for s in det:
    if 'canon' in s and s['elemScore'] is not None: bysk[(s['event'],s['canon'],s['dis'])].append(s['elemScore'])
ok2=bad2=0; ex=[]
for ev in seed:
    for k in ev['kategorien']:
        for r in k['rows']:
            key=(ev['name'],r['name'],k['disziplin'])
            if key not in bysk: continue
            tot=round(sum(bysk[key]),2)
            ref=r.get('tesRaw') if r.get('tesRaw') is not None else r.get('tes')
            if ref is None: continue
            if abs(tot-ref)<=0.05: ok2+=1
            else:
                bad2+=1
                if len(ex)<8: ex.append((ev['name'],r['name'],tot,ref))
print('Athlet+Event-Summe vs. Rangliste: OK',ok2,'| abweichend',bad2)
for x in ex: print('  ',x)

# Kader-Abdeckung
kader=json.load(open('data/kader.json'))
knames={a['name'] for a in kader.get('athleten',kader) if isinstance(a,dict)} if isinstance(kader,dict) else {a['name'] for a in kader}
kmatch=Counter()
for s in det:
    if s.get('canon') in knames: kmatch[s['canon']]+=1
print('Kader-Athleten mit Detail-Blättern:',len(kmatch),'von',len(knames))
print('ohne Blätter:',sorted(knames-set(kmatch)))
