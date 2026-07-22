#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrahiert die "JUDGES DETAILS PER SKATER"-Blätter (Elemente + Einzel-Components)
aus allen Ergebnis-PDFs. Ausgabe: data/details_raw.json
Struktur je Blatt: event, jahr, herkunft, typ, cat, seg, rank, name, nat,
elemScore, compScore, ded, segTotal, falls, elements[{kind,code,flags,base,qoe,panel}], comps[4]
"""
import subprocess, re, json, os, glob, hashlib, sys

# ---------- Job-Liste: identisch zu parse_all.py + parse_intl.py ----------
JOBS=[
 ({'typ':'EM','jahr':2023,'name':'EM Ponte di Legno 2023','herkunft':'international'},['data/em2023_free.pdf','data/em2023_solo.pdf','data/em2023_dance.pdf','data/em2023_pairs.pdf']),
 ({'typ':'WM','jahr':2023,'name':'WM Ibagué 2023','herkunft':'international'},['data/wm2023_free.pdf','data/wm2023_solo.pdf','data/wm2023_dance.pdf','data/wm2023_pairs.pdf']),
 ({'typ':'EM','jahr':2024,'name':'EM Fafe 2024','herkunft':'international'},['data/em2024_free.pdf','data/em2024_solo.pdf','data/em2024_dance.pdf','data/pairs_new/em2024_pairs.pdf']),
 ({'typ':'WM','jahr':2024,'name':'WM Rimini 2024','herkunft':'international'},['data/wm2024_free.pdf','data/wm2024_solo.pdf','data/wm2024_dance.pdf','data/pairs_new/wm2024_pairs.pdf']),
 ({'typ':'EM','jahr':2025,'name':'EM Triest 2025','herkunft':'international'},['data/em2025_free.pdf','data/em2025_solo.pdf','data/em2025_dance.pdf','data/pairs_new/em2025_pairs.pdf']),
 ({'typ':'WM','jahr':2025,'name':'WM Peking 2025','herkunft':'international'},['data/wm2025_free.pdf','data/wm2025_solo.pdf','data/wm2025_dance.pdf','data/pairs_new/wm2025_pairs.pdf']),
 ({'typ':'WC-SA','jahr':2024,'name':'AIS Brasília 2024','herkunft':'international'},sorted(glob.glob('data/ais_brasilia2024/*.pdf'))),
 ({'typ':'WC-EU','jahr':2024,'name':'AIS Triest 2024','herkunft':'international'},sorted(glob.glob('data/ais_triest2024/*.pdf'))),
 ({'typ':'WC-SA','jahr':2025,'name':'AIS Buenos Aires 2025','herkunft':'international'},['data/ais_ba_free.pdf','data/ais_ba_solo.pdf','data/pairs_new/ba2025_paare.pdf','data/pairs_new/ba2025_rolltanz.pdf']),
 ({'typ':'WC-EU','jahr':2025,'name':'AIS Triest 2025','herkunft':'international'},['data/ais_tri_free.pdf','data/ais_tri_solo.pdf','data/ais_tri_dance.pdf','data/pairs_new/triest2025_pairs.pdf']),
 ({'typ':'WC-F','jahr':2025,'name':'AIS-Finale Reggio Emilia 2025','herkunft':'international'},['data/ais_reg_free.pdf','data/ais_reg_solo.pdf']),
 ({'typ':'WC-SA','jahr':2026,'name':'AWC Buenos Aires 2026','herkunft':'international'},sorted(glob.glob('data/awc26/WCB_*.pdf'))),
 ({'typ':'WC-EU','jahr':2026,'name':'AWC Semi-Final Garmisch 2026','herkunft':'international'},sorted(glob.glob('data/awc26/2026_WCG_*.pdf'))),
 ({'typ':'WC-F','jahr':2026,'name':'AWC Finale Cesena 2026','herkunft':'international'},sorted(glob.glob('data/awc/fin_*.pdf'))),
 ({'typ':'IL','jahr':2023,'name':'Interland Cup Mierlo 2023','herkunft':'international'},['/home/claude/driv-dashboard/data/interland_2023.pdf']),
 ({'typ':'IL','jahr':2024,'name':'Interland Cup Bonn 2024','herkunft':'international'},['/home/claude/driv-dashboard/data/interland_2024.pdf']),
 ({'typ':'IL','jahr':2025,'name':'Interland Cup Zürich 2025','herkunft':'international'},['/home/claude/driv-dashboard/data/interland_2025.pdf']),
 ({'typ':'National','jahr':2026,'name':'Deutsche Meisterschaften Stade 2026','herkunft':'national'},sorted(glob.glob('data/dm26off/*.pdf'))+sorted(glob.glob('/home/claude/driv-dashboard/data/dm/*.pdf'))+['data/dm/dm26_paarlauf.pdf']),
 ({'typ':'IGC','jahr':2025,'name':'Int. Deutschland-Pokal Göttingen 2025','herkunft':'international'},['data/igc2025.pdf']),
 ({'typ':'IGC','jahr':2026,'name':'Int. Deutschland-Pokal Freiburg 2026','herkunft':'international'},['data/igc2026_free.pdf','data/igc2026_solo.pdf']),
 ({'typ':'CoE','jahr':2024,'name':'Cup of Europe Zürich 2024','herkunft':'international'},['data/coe2024_free.pdf','data/coe2024_solo.pdf','data/coe2024_dance.pdf','data/coe2024_pairs.pdf']),
 ({'typ':'CoE','jahr':2023,'name':'Cup of Europe Pula 2023','herkunft':'international'},sorted(glob.glob('data/coe23/*.pdf'))),
 ({'typ':'CoE','jahr':2025,'name':'Cup of Europe Matosinhos 2025','herkunft':'international'},sorted(glob.glob('data/coe25/*FINAL*.pdf'))+sorted(glob.glob('data/coe25/*RESULTS*.pdf'))),
 ({'typ':'National','jahr':2023,'name':'Deutsche Meisterschaften Bayreuth 2023','herkunft':'national'},sorted(glob.glob('data/dm/dm23_*.pdf'))),
 ({'typ':'National','jahr':2024,'name':'Deutsche Meisterschaften Stade 2024','herkunft':'national'},sorted(glob.glob('data/dm/dm24_*.pdf'))),
 ({'typ':'National','jahr':2025,'name':'Deutsche Meisterschaften Ober-Ramstadt 2025','herkunft':'national'},sorted(glob.glob('data/dm/dm25_*.pdf'))),
]
RLW=[('2023','RLW Bonn (DM Show) 2023',['data/rlw23/2023_Bonn_Ergebnisse_Kuerlaufen_.pdf','data/rlw23/2023_Bonn_Ergebnisse_Tanz.pdf']),
 ('2023','RLW Wolfsburg (Hans-Bauer-Pokal) 2023',['data/rlw23/2023_RLW_Wolfsburg_Ergebnisse.pdf']),
 ('2023','RLW Lübeck 2023',['data/rlw23/RL-Wettb_Luebeck_2023_-_Ergebnisse.pdf']),
 ('2023','RLW Hamburg-Bergedorf 2023',['data/rlw23/RL-Wettb_Bergedorf_-_Ergebnisse.pdf']),
 ('2023','RLW Duisburg 2023',['data/rlw23/RL-Wettb_Duisburg_2023_-_Ergebnisse.pdf']),
 ('2024','RLW Eppingen (DM Show) 2024',['data/rlw/24_eppingen_kuer.pdf','data/rlw/24_eppingen_tanz.pdf']),
 ('2024','RLW Stade 2024',['data/rlw/24_stade_kuer.pdf']),
 ('2024','RLW Bremen 2024',['data/rlw/24_bremen_solo.pdf','data/rlw/24_bremen_dance.pdf']),
 ('2024','NDM/RLW Bremerhaven 2024',['data/rlw/24_ndm_free.pdf','data/rlw/24_ndm_solo.pdf','data/rlw/24_ndm_dance.pdf']),
 ('2024','RLW Darmstadt 2024',['data/rlw/24_darmstadt_kuer.pdf']),
 ('2025','RLW Kiel (DM Show) 2025',['data/rlw/25_kiel_kuer.pdf','data/rlw/25_kiel_tanz.pdf']),
 ('2025','RLW Stade 2025',['data/rlw/25_stade_kuer.pdf','data/rlw/25_stade_tanz.pdf']),
 ('2025','RLW Ober-Ramstadt 2025',['data/rlw/25_oberramstadt.pdf']),
 ('2025','RLW Göttingen (IGC) 2025',['data/rlw/25_goettingen_kuer.pdf','data/rlw/25_goettingen_solo.pdf']),
 ('2025','RLW Winnenden 2025',['data/rlw/25_winnenden_solo.pdf','data/rlw/25_winnenden_dance.pdf']),
 ('2025','RLW Duisburg 2025',['data/rlw/25_duisburg.pdf']),
 ('2025','RLW Ismaning 2025',['data/rlw/25_ismaning.pdf']),
 ('2026','RLW Freiburg (DM Show) 2026',['data/rlw/26_freiburg_kuer.pdf','data/rlw/26_freiburg_tanz.pdf']),
 ('2026','RLW Berlin 2026',['data/rlw/26_berlin_kuer.pdf','data/rlw/26_berlin_tanz.pdf']),
 ('2026','RLW Eppingen 2026',['data/rlw/26_eppingen.pdf'])]
for j,nm,fls in RLW:
    JOBS.append(({'typ':'National','jahr':int(j),'name':nm,'herkunft':'national'},fls))

def dedup(files):
    seen=set(); out=[]
    for f in files:
        if not os.path.exists(f): continue
        h=hashlib.md5(open(f,'rb').read()).hexdigest()
        if h in seen: continue
        seen.add(h); out.append(f)
    return out

def tcase(n): return ' '.join(w.capitalize() for w in n.title().split())

HDR=re.compile(r'(Free Skating|Solo Dance|Couple Dance|Pairs)\s+(Ladies|Men)?\s*([A-Za-z][A-Za-z0-9 ]*?)\s*(?:-\s*([A-Za-z][A-Za-z0-9 ]+?))?\s*(?:REVISED.*)?$')
MARK='JUDGES DETAILS PER SKATER'
CODE=re.compile(r'^(\d?[A-Za-z][A-Za-z0-9]{0,7})\s*(<{1,3}|\*)?$')
FLT=re.compile(r'-?\d+\.\d\d(?!\d)')
KINDS=('ComboJump','Jump','ComboSpin','Spin','Step Sequence','Dance Sequence','Lift','Pattern Sequence','Dance Step','Traveling','Cluster','Twist','Throw','Death','Contact','Choreo','Solo')
COMPN=('Skating Skills','Transitions','Performance','Choreography')
NAMES={}

def parse_file(path,meta):
    txt=subprocess.run(['pdftotext','-layout',path,'-'],capture_output=True,text=True,timeout=600).stdout
    sheets=[]; cat=None
    cur=None; mode=None
    def close():
        nonlocal cur
        if cur and cur['elements']:
            cur.pop('_kind',None)
            if cur['elemScore'] is not None:
                cur['ok']=abs(round(sum(e['panel'] for e in cur['elements']),2)-cur['elemScore'])<=0.03
            else: cur['ok']=False
            sheets.append(cur)
        cur=None
    for raw in txt.split('\n'):
        s=raw.strip()
        if not s: continue
        mh=HDR.search(s)
        if mh and ('FINAL' not in s and 'RESULT' not in s.upper()[:40] or True):
            # Kategorie-/Segment-Kopf (auch Seitenfuß der Folgeseite)
            grp,gen,klr,seg=mh.group(1),mh.group(2) or '',mh.group(3).strip(),mh.group(4)
            if klr and len(klr)<25 and not any(b in s for b in ('FINAL RESULT','RESULTS DETAILS')):
                cat={'dis':grp,'gender':gen,'klasse':klr,'seg':seg}
            continue
        if MARK in s:
            close(); mode='head'
            bn=os.path.basename(path).lower()
            hint='dance' if ('tanz' in bn or 'dance' in bn or 'solo' in bn) else ('pairs' if ('paar' in bn or 'pair' in bn) else 'free')
            cur={'file':os.path.basename(path),'event':meta['name'],'jahr':meta['jahr'],'typ':meta['typ'],
                 'herkunft':meta['herkunft'],'cat':dict(cat) if cat else None,'hint':hint,
                 'rank':None,'name':None,'nat':None,'elemScore':None,'compScore':None,'ded':None,
                 'segTotal':None,'falls':0.0,'elements':[],'comps':[None,None,None,None]}
            continue
        if cur is None: continue
        cols=re.split(r'\s{2,}',s)
        if mode=='head':
            BADW=('Total','Rank','Nation','Element','Info','Base','Score','score','Panel','QOE','Deduction')
            if cur['name'] is None:
                m=re.match(r'^(\d{1,3})$',cols[0])
                if m and len(cols)>=2:
                    c1=cols[1].strip()
                    if re.fullmatch(r'[A-Z]{3}',c1):
                        cur['rank']=int(m.group(1)); cur['nat']=c1; cur['name']=''   # Name umgebrochen
                    elif re.search(r'[A-ZÄÖÜ]{2}',c1) and not FLT.search(c1):
                        cur['rank']=int(m.group(1)); cur['name']=c1
                        for c in cols[2:]:
                            if re.fullmatch(r'[A-Z]{3}',c.strip()): cur['nat']=c.strip()
                continue
            fl=[float(x) for x in FLT.findall(s)]
            if len(fl)>=4 and 'Element' not in s and 'Deduction' not in s:
                if re.search(r'[A-ZÄÖÜ]{2}',cols[0]) and not FLT.search(cols[0]) and not any(w in cols[0] for w in BADW):
                    cur['name']=(cur['name']+' '+cols[0].strip()).strip()
                cur['elemScore'],cur['compScore'],cur['ded'],cur['segTotal']=fl[0],fl[1],fl[2],fl[3]
                mode='elem'; continue
            if not fl and re.search(r'[A-ZÄÖÜ]{2}',s) and not any(w in s for w in BADW) and re.fullmatch(r"[A-ZÄÖÜÁÀÂÉÈÊÍÎÓÒÔÚÙÑÇŠŽ0-9'’\. \-/]{3,}",s):
                cur['name']=(cur['name']+' '+s).strip()      # Namens-Fortsetzungszeile
            continue
        if mode in ('elem','after') and s.startswith('Program Components'):
            mode='comp'; continue
        if mode=='elem':
            fl=FLT.findall(s)
            # Elementzeile erkennen
            idx=None; kind=None; ci=0
            m=re.match(r'^(\d{1,2})\s+([A-Za-z][A-Za-z ]*)$',cols[0].strip())
            if m:
                idx=int(m.group(1)); kind=m.group(2).strip(); ci=1
            elif re.fullmatch(r'\d{1,2}',cols[0].strip()) and len(cols)>=2 and re.fullmatch(r'[A-Za-z][A-Za-z ]*',cols[1].strip()):
                idx=int(cols[0]); kind=cols[1].strip(); ci=2
            code=None; flags=''
            if len(cols)>ci:
                tok=cols[ci].strip()
                mc=CODE.match(tok)
                if not mc:
                    mc2=re.match(r'^(\d?[A-Za-z][A-Za-z0-9]{0,7})\s*(<{1,3}|\*)?\s+[A-Za-z]',tok)
                    if mc2 and (ci>0 or kind is not None or len(FLT.findall(s))>=3): mc=mc2
                if mc and not (ci==0 and cols[0].strip() in COMPN):
                    code=mc.group(1); flags=(mc.group(2) or '')
            if kind is not None and code is None and len(fl)==0:
                cur['_kind']=kind; continue           # ComboSpin-Kopfzeile (nur Judges)
            if code is not None and len(fl)>=3:
                if kind is not None: cur['_kind']=kind
                # Beschreibung: Spalte hinter dem Code (für die Code->Name-Tabelle)
                desc=None
                if ci+1<len(cols) and not FLT.search(cols[ci+1]) and re.search(r'[A-Za-z]{3}',cols[ci+1]):
                    desc=cols[ci+1].strip()
                elif ' ' in cols[ci]:
                    t2=cols[ci].split(None,1)
                    if len(t2)==2 and not FLT.search(t2[1]): desc=t2[1].strip()
                if desc: NAMES.setdefault(code,{}); NAMES[code][desc]=NAMES[code].get(desc,0)+1
                base=float(fl[0]); qoe=float(fl[1]); panel=float(fl[-1])
                bpos=s.find(fl[0]); rest=s[bpos+len(fl[0]):bpos+len(fl[0])+8]
                bflag=re.match(r'\s*([%+TYN!*]+)',rest)
                if bflag: flags+=bflag.group(1)
                cur['elements'].append({'kind':cur.get('_kind') or kind or '','code':code,'flags':flags,
                                        'base':base,'qoe':qoe,'panel':panel})
                continue
            if code=='NJ' or (len(cols)>=2 and cols[ci].strip()=='NJ'):
                cur['elements'].append({'kind':cur.get('_kind') or kind or '','code':'NJ','flags':'',
                                        'base':0.0,'qoe':0.0,'panel':0.0})
                continue
            if len(fl)==2 and code is None and kind is None and len(cols)<=2:
                mode='after'; continue                 # Basissummen-/Gesamtzeile
            continue
        if mode=='comp':
            if s.startswith('Judges Total'):
                mode='after'; continue
            fl=FLT.findall(s)
            for i,c in enumerate(COMPN):
                if cols[0].startswith(c) and fl:
                    cur['comps'][i]=float(fl[-1]); break
            continue
        if mode=='after':
            mf=re.search(r'Falls?:\s*(-?\d+\.?\d*)',s)
            if mf: cur['falls']+=abs(float(mf.group(1)))
            if s.startswith('Deductions'):
                fl=FLT.findall(s)
                if fl and cur['ded'] is None: cur['ded']=float(fl[0])
            continue
    close()
    return sheets

if __name__=='__main__':
    allsheets=[]; per=[]
    for meta,files in JOBS:
        files=dedup(files); n0=len(allsheets)
        for f in files:
            try: allsheets+=parse_file(f,meta)
            except Exception as e: print('FEHLER',f,e)
        per.append((meta['name'],len(allsheets)-n0))
    json.dump(allsheets,open('data/details_raw.json','w'),ensure_ascii=False)
    best={c:max(v,key=v.get) for c,v in NAMES.items()}
    json.dump(best,open('data/element_names.json','w'),ensure_ascii=False,indent=0,sort_keys=True)
    nel=sum(len(s['elements']) for s in allsheets)
    c4=sum(1 for s in allsheets if sum(v is not None for v in s['comps'])>=2)
    seg=sum(1 for s in allsheets if s['cat'] and s['cat'].get('seg'))
    # Konsistenz: Summe Panel-Scores ≈ Element-Score
    ok=bad=0
    for s in allsheets:
        if s['elemScore'] is None: continue
        d=abs(round(sum(e['panel'] for e in s['elements']),2)-s['elemScore'])
        ok+=(d<=0.03); bad+=(d>0.03)
    for nm,n in per: print(f'{n:5d}  {nm}')
    print(f'GESAMT Blätter: {len(allsheets)} | Elemente: {nel} | Comps 4/4: {c4} | mit Segment: {seg} | Panel-Summe OK: {ok} / abweichend: {bad}')
