#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1) Heilt Ranglisten-Zeilen mit unvollständigen Segmentdaten aus den Detail-Blättern
   (nur wenn die Blatt-Summen exakt zum Gesamtergebnis passen; entwertete Zeilen bleiben unberührt).
2) Aggregiert pro Athlet+Disziplin Element-Konstanz und Einzel-Components -> data/konstanz.json
"""
import json, math
from collections import defaultdict

det=json.load(open('data/details_matched.json'))
seed=json.load(open('data/seed_v2.json'))

SEGORD={'Short Program':0,'Style Dance':0,'Compulsory 1':0,'Compulsory 2':1,'Free Program':9,'Free Dance':9,'Long Program':9}
bysk=defaultdict(list)
for s in det:
    if 'canon' in s: bysk[(s['event'],s['canon'],s['dis'])].append(s)

# ---------- 1) Heilung ----------
heal=0; healed_ev=defaultdict(int)
for ev in seed:
    for k in ev['kategorien']:
        for r in k['rows']:
            if r.get('platz') is None: continue          # entwertete Zwischenstands-Zeilen nicht anfassen
            sh=bysk.get((ev['name'],r['name'],k['disziplin']))
            if not sh or r['total'] is None: continue
            if any(x['segTotal'] is None or x['elemScore'] is None for x in sh): continue
            stot=round(sum(x['segTotal'] for x in sh),2)
            if abs(stot-r['total'])>0.05: continue        # Blätter decken nicht alle Segmente ab
            selem=round(sum(x['elemScore'] for x in sh),2)
            raw=r.get('tesRaw') if r.get('tesRaw') is not None else r.get('tes')
            if raw is not None and abs(selem-raw)<=0.03 and (r.get('nseg') or 0)==len(sh): continue
            abz=round(sum(abs(x['ded'] or 0) for x in sh),2)
            pcs=round(sum(x['compScore'] or 0 for x in sh),2)
            tes=round(selem-abz,2)
            if abs((tes+pcs)-r['total'])>0.05: continue   # Identität muss aufgehen
            sh2=sorted(sh,key=lambda x:SEGORD.get((x['cat'] or {}).get('seg') or '',5))
            r['tesRaw']=selem; r['abzuege']=abz; r['tes']=tes; r['pcs']=pcs
            r['nseg']=len(sh2); r['tesOk']=True
            r['segs']=[{'seg':(x['cat'] or {}).get('seg') or 'Programm','tes':x['elemScore'],
                        'pcs':x['compScore'],'ded':abs(x['ded'] or 0)} for x in sh2]
            heal+=1; healed_ev[ev['name']]+=1
print('Geheilte Zeilen:',heal)
for e,n in sorted(healed_ev.items(),key=lambda x:-x[1])[:8]: print('  ',e,n)
json.dump(seed,open('data/seed_v2.json','w'),ensure_ascii=False,indent=1)

# ---------- 2) Aggregation Konstanz ----------
def grp(kind,code):
    kl=(kind or '').lower()
    if 'jump' in kl or code=='NJ': return 'J'
    if 'spin' in kl: return 'P'
    if 'step' in kl and 'dance' not in kl: return 'S'
    return 'D'

SEGKEY={'Short Program':'KP','Free Program':'Kür','Long Program':'Kür','Style Dance':'SD',
        'Free Dance':'KT','Compulsory 1':'PT','Compulsory 2':'PT','Compulsory Dance':'PT'}
agg=defaultdict(lambda:{'el':defaultdict(lambda:defaultdict(list)),
                        'comps':defaultdict(lambda:defaultdict(list)),
                        'abz':defaultdict(lambda:[0,0.0]),'starts':0,'intN':0,'natN':0,
                        'seg':defaultdict(lambda:[0,0.0])})
for s in det:
    if 'canon' not in s: continue
    key=s['canon']+'|'+s['dis']
    a=agg[key]; a['starts']+=1
    a['intN' if s['herkunft']=='international' else 'natN']+=1
    jahr=s['jahr']
    ab=a['abz'][jahr]; ab[0]+=1; ab[1]+=abs(s['ded'] or 0)
    sk=SEGKEY.get((s['cat'] or {}).get('seg') or '','?')
    sg=a['seg'][sk]; sg[0]+=1; sg[1]+=abs(s['ded'] or 0)
    for e in s['elements']:
        a['el'][(e['code'],grp(e['kind'],e['code']))][jahr].append(e)
    if any(v is not None for v in s['comps']):
        a['comps'][s['herkunft']][jahr].append(s['comps'])

def r2(x): return round(x,2)
# Nur deutsche Szene + Kader: alle mit nationalen Starts, GER-Nation international, Kader-Namen
gernames=set()
for ev in seed:
    for k in ev['kategorien']:
        for r in k['rows']:
            if ev['herkunft']=='national' or (r.get('nat')=='GER'): gernames.add(r['name'])
kad=json.load(open('data/kader.json'))
for a_ in (kad.get('athleten',kad) if isinstance(kad,dict) else kad):
    if isinstance(a_,dict): gernames.add(a_['name'])
OUT={}
for key,a in agg.items():
    if key.split('|')[0] not in gernames: continue
    el=[]
    for (code,g),byjahr in a['el'].items():
        allE=[e for v in byjahr.values() for e in v]
        yl=max(byjahr)
        lastE=byjahr[yl]
        n=len(allE)
        if code=='NJ':
            el.append({'c':'NJ','g':g,'n':n,'yl':yl,'nl':len(lastE)}); continue
        ps=[e['panel'] for e in allE]; m=sum(ps)/n
        sd=math.sqrt(sum((p-m)**2 for p in ps)/n) if n>1 else None
        neg=sum(1 for e in allE if e['qoe']<-0.001)
        dg=sum(1 for e in allE if '<' in e['flags'] or '*' in e['flags'])
        rec={'c':code,'g':g,'n':n,'m':r2(m),'q':r2(sum(e['qoe'] for e in allE)/n),
             'b':r2(sum(e['base'] for e in allE)/n),'mx':r2(max(ps)),'ng':neg,'dg':dg,'yl':yl,
             'nl':len(lastE),'ml':r2(sum(e['panel'] for e in lastE)/len(lastE)),
             'ngl':sum(1 for e in lastE if e['qoe']<-0.001)}
        if sd is not None: rec['s']=r2(sd)
        el.append(rec)
    el.sort(key=lambda x:(-x.get('n',0)))
    comps={}
    for hk,byjahr in a['comps'].items():
        y={}
        for jahr,rowsc in byjahr.items():
            sums=[0.0]*4; cnts=[0]*4
            for c in rowsc:
                for i,v in enumerate(c):
                    if v is not None: sums[i]+=v; cnts[i]+=1
            y[jahr]=[len(rowsc)]+[r2(sums[i]/cnts[i]) if cnts[i] else None for i in range(4)]
        comps['int' if hk=='international' else 'nat']=y
    OUT[key]={'el':el,'comps':comps,'starts':a['starts'],'intN':a['intN'],'natN':a['natN'],
              'abz':{str(j):[v[0],r2(v[1])] for j,v in a['abz'].items()},
              'seg':{k:[v[0],r2(v[1])] for k,v in a['seg'].items() if k!='?'}}

# ---------- Referenz: Einzel-Components int. Podium je Klasse+Disziplin+Geschlecht ----------
refc=defaultdict(lambda:[ [0.0,0]*1 for _ in range(4)])
refagg=defaultdict(lambda:{'p':[[0.0,0] for _ in range(4)],'t8':[[0.0,0] for _ in range(4)]})
rankmap={}
for ev in seed:
    if ev['herkunft']!='international': continue
    for k in ev['kategorien']:
        for r in k['rows']:
            if r.get('platz'): rankmap[(ev['name'],r['name'],k['disziplin'])]=r['platz']
for s in det:
    if 'canon' not in s or s['herkunft']!='international': continue
    pl=rankmap.get((s['event'],s['canon'],s['dis']))
    if not pl: continue
    key=s['dis']+'|'+s['klasse']+'|'+(s.get('gender') or '')
    for i,v in enumerate(s['comps']):
        if v is None: continue
        if pl<=3: refagg[key]['p'][i][0]+=v; refagg[key]['p'][i][1]+=1
        if pl<=8: refagg[key]['t8'][i][0]+=v; refagg[key]['t8'][i][1]+=1
REFC={k:{'p':[r2(x[0]/x[1]) if x[1] else None for x in v['p']],
         't8':[r2(x[0]/x[1]) if x[1] else None for x in v['t8']]} for k,v in refagg.items()}

# ---------- Referenz: Element-Inventar des int. Podiums je Klasse+Disziplin+Geschlecht ----------
# Welche Elemente zeigen die Podiumsprogramme (Platz 1-3) – Anteil der Programme mit dem Element
# und durchschnittlicher Panel-Score. Basis: die letzten beiden belegten Jahre je Gruppe (aktueller Stand).
podprog=defaultdict(list)   # key -> Liste von Programmen (je Programm: dict code->beste panel)
for s in det:
    if 'canon' not in s or s['herkunft']!='international': continue
    pl=rankmap.get((s['event'],s['canon'],s['dis']))
    if not pl or pl>3: continue
    key=s['dis']+'|'+s['klasse']+'|'+(s.get('gender') or '')
    prog={}
    for e in s['elements']:
        if e['code']=='NJ': continue
        c=e['code']
        if c not in prog or e['panel']>prog[c][0]: prog[c]=[e['panel'],grp(e['kind'],e['code'])]
    if prog: podprog[key].append({'jahr':s['jahr'],'prog':prog})
REFEL={}
for key,progs in podprog.items():
    jahre=sorted({p['jahr'] for p in progs})[-2:]        # letzte 2 belegte Jahre = aktueller Elementstand
    cur=[p for p in progs if p['jahr'] in jahre]
    if len(cur)<4: cur=progs                             # zu wenig aktuell -> alle Jahre
    n=len(cur)
    codes=defaultdict(lambda:[0,0.0,''])
    for p in cur:
        for c,(panel,g) in p['prog'].items():
            codes[c][0]+=1; codes[c][1]+=panel; codes[c][2]=g
    el={c:[r2(v[0]/n),r2(v[1]/v[0]),v[2]] for c,v in codes.items() if v[0]/n>=0.25}
    if el: REFEL[key]={'n':n,'jahre':jahre,'el':el}

names=json.load(open('data/element_names.json'))
json.dump({'det':OUT,'refc':REFC,'refel':REFEL,'names':names},open('data/konstanz.json','w'),ensure_ascii=False)
import os
print('Athlet|Disziplin-Profile:',len(OUT),'| Referenzgruppen:',len(REFC),
      '| Dateigröße:',round(os.path.getsize('data/konstanz.json')/1024),'KB')
ger=[k for k in OUT if OUT[k]['natN']>0]
print('davon mit nationalen Starts (≈deutsche):',len(ger))
