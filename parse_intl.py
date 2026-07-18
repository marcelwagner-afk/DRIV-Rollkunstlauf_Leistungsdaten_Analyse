import subprocess, re, json

FILES=[
 ('em2024_free.pdf','EM',2024,'EM Fafe 2024'),('em2024_solo.pdf','EM',2024,'EM Fafe 2024'),('em2024_dance.pdf','EM',2024,'EM Fafe 2024'),
('wm2024_solo.pdf','WM',2024,'WM Rimini 2024'),('wm2024_dance.pdf','WM',2024,'WM Rimini 2024'),
 ('em2025_free.pdf','EM',2025,'EM Triest 2025'),('em2025_solo.pdf','EM',2025,'EM Triest 2025'),('em2025_dance.pdf','EM',2025,'EM Triest 2025'),
 ('wm2025_free.pdf','WM',2025,'WM Peking 2025'),('wm2025_solo.pdf','WM',2025,'WM Peking 2025'),('wm2025_dance.pdf','WM',2025,'WM Peking 2025'),
]
DIS={'Free Skating':'Kürlaufen','Solo Dance':'Solotanz','Couple Dance':'Rolltanz','Pairs':'Paarlauf'}
BAD=('PANEL','JUDGES','RESULT','REVISED','DETAILS','VERIFIED','WORLDSKATE','TECHNICAL','OFFICIAL')
def tcase(n): return ' '.join(w.capitalize() for w in n.title().split())

FULL=re.compile(r'((?:Free Skating|Solo Dance|Couple Dance|Pairs)\s*(?:Ladies|Men)?\s*(?:Seniores|Juniores|Youth|Cadets))\s*(?:-\s*(.+?))?\s*(?:REVISED.*)?$')
events={}
for fn,typ,jahr,label in FILES:
    txt=subprocess.run(['pdftotext','-layout',f'data/{fn}','-'],capture_output=True,text=True,timeout=300).stdout
    m=re.search(r'^\s*(.+?)\s*-\s*(\d\d)/(\d\d)/(\d\d\d\d)\s*$',txt,flags=re.M)
    datum=f'{m.group(4)}-{m.group(3)}-{m.group(2)}' if m else f'{jahr}-01-01'
    ev=events.setdefault((typ,jahr),{'typ':typ,'jahr':jahr,'name':label,'datum':datum,'herkunft':'international','kategorien':{}})
    cat=None; catname=None; mode=None; pendingFinal=[]; pendingSeg=[]; finTables=[]; lastRow=None
    isCouple=lambda: catname and ('Couple' in catname or 'Pairs' in catname)
    for ln in txt.split('\n'):
        s=ln.strip()
        mh=FULL.match(s)
        if mh:
            base=mh.group(1).strip()
            catname=base
            cat=ev['kategorien'].setdefault(base,{'final':{}, 'seg':{}})
            for nm,tes,pcs in pendingSeg:
                d=cat['seg'].setdefault(nm,{'tes':0.0,'pcs':0.0,'nseg':0})
                d['tes']=round(d['tes']+tes,2); d['pcs']=round(d['pcs']+pcs,2); d['nseg']+=1
            pendingSeg=[]; mode=None; lastRow=None; continue
        if re.match(r'(Free Skating|Solo Dance|Couple Dance|Pairs)\b',s) and 'FINAL' not in s and not FULL.match(s):
            # abgeschnittener Kopf – Kategorie unbekannt, Final-Zeilen puffern
            cat=None; catname=s; mode=None; lastRow=None; finTables.append([]); continue  # neue Puffertabelle
        if 'FINAL RESULT' in s: mode='final'; lastRow=None; continue
        if 'RESULTS DETAILS' in s: mode='seg'; lastRow=None; continue
        if re.match(r'Pl\.\s+Name\b',s):
            mode='seg' if 'TES' in s else ('final' if ('Points' in s or 'Nation' in s) else mode)
            lastRow=None; continue
        if 'JUDGES DETAILS' in s: mode=None; lastRow=None; continue
        if mode is None: continue
        if mode=='final':
            mf=re.match(r'(\d+)\s+(.+?)\s+([A-Z]{3})\s+(\d+\.\d\d)\b',s)
            if mf:
                nm=tcase(mf.group(2)); rec={'platz':int(mf.group(1)),'nat':mf.group(3),'total':float(mf.group(4))}
                if cat is not None: cat['final'][nm]=rec; lastRow=('final',nm)
                else:
                    if not finTables: finTables.append([])
                    finTables[-1].append((nm,rec)); lastRow=('pfinal',len(finTables[-1])-1)
                continue
        else:
            ms=re.match(r'(\d+)\s+(.+?)\s+([A-Z]{3})\s+(\d+\.\d\d)\s+(\d+\.\d\d)\s+(-?\d+\.?\d*)\s+(\d+\.\d\d)\b',s)
            if ms:
                nm=tcase(ms.group(2))
                if cat is not None:
                    d=cat['seg'].setdefault(nm,{'tes':0.0,'pcs':0.0,'nseg':0})
                    d['tes']=round(d['tes']+float(ms.group(4)),2); d['pcs']=round(d['pcs']+float(ms.group(5)),2); d['nseg']+=1
                    lastRow=('seg',nm)
                else:
                    pendingSeg.append((nm,float(ms.group(4)),float(ms.group(5)))); lastRow=('pseg',len(pendingSeg)-1)
                continue
        # Partnerzeile bei Paaren
        if lastRow and re.fullmatch(r"[A-ZÄÖÜÉÈÍÓÚÑÇ'’\-\. ]{4,}",s) and not any(b in s for b in BAD):
            p=tcase(s)
            kind=lastRow[0]
            if kind=='final' and cat is not None:
                rec=cat['final'].pop(lastRow[1]); cat['final'][lastRow[1]+' / '+p]=rec; lastRow=('final',lastRow[1]+' / '+p)
            elif kind=='pfinal':
                nm,rec=finTables[-1][lastRow[1]]; finTables[-1][lastRow[1]]=(nm+' / '+p,rec)
            elif kind=='pseg':
                nm,tes,pcs=pendingSeg[lastRow[1]]; pendingSeg[lastRow[1]]=(nm+' / '+p,tes,pcs)
            elif kind=='seg' and cat is not None:
                d=cat['seg'].pop(lastRow[1]); newk=lastRow[1]+' / '+p
                t=cat['seg'].get(newk)
                if t:
                    t['tes']=round(t['tes']+d['tes'],2); t['pcs']=round(t['pcs']+d['pcs'],2); t['nseg']+=d['nseg']
                else:
                    cat['seg'][newk]=d
                lastRow=('seg',newk)
            continue
        lastRow=None

    # Puffertabellen den Kategorien mit groesster Namensueberlappung zuordnen
    for tab in finTables:
        if not tab: continue
        names={nm.split(' / ')[0] for nm,_ in tab}
        best=None; bestov=0
        for base,c in ev['kategorien'].items():
            ov=len(names & {k.split(' / ')[0] for k in c['seg']})
            if ov>bestov: bestov=ov; best=c
        if best is not None and bestov>=max(2,len(tab)//3) and not best['final']:
            for nm,rec in tab: best['final'][nm]=rec

out=[]
for (typ,jahr),ev in sorted(events.items()):
    kats=[]
    for base,cat in ev['kategorien'].items():
        mdis=re.match(r'(Free Skating|Solo Dance|Couple Dance|Pairs)\s*(Ladies|Men)?\s*(Seniores|Juniores|Youth|Cadets)',base)
        if not mdis: continue
        dis=DIS[mdis.group(1)]
        gender={'Ladies':'Damen','Men':'Herren'}.get(mdis.group(2) or '','')
        klasse={'Seniores':'Senioren','Juniores':'Junioren','Youth':'Youth','Cadets':'Cadets'}[mdis.group(3)]
        rows=[]
        for nm,f in cat['final'].items():
            sg=cat['seg'].get(nm) or cat['seg'].get(nm.split(' / ')[0]) or {}
            rows.append({'name':nm,'nat':f['nat'],'platz':f['platz'],'total':f['total'],
                         'tes':sg.get('tes'),'pcs':sg.get('pcs'),'nseg':sg.get('nseg',0)})
        rows.sort(key=lambda r:r['platz'])
        if rows: kats.append({'disziplin':dis,'klasse':klasse,'gender':gender,'rows':rows})
    out.append({'typ':ev['typ'],'jahr':ev['jahr'],'name':ev['name'],'datum':ev['datum'],'herkunft':'international','kategorien':kats})

json.dump(out,open('data/seed_international.json','w'),ensure_ascii=False,indent=1)
for ev in out:
    n=sum(len(k['rows']) for k in ev['kategorien'])
    miss=sum(1 for k in ev['kategorien'] for r in k['rows'] if r['tes'] is None)
    print(ev['name'],'| Kategorien:',len(ev['kategorien']),'| Starter:',n,'| ohne TES:',miss)
    for k in ev['kategorien']:
        if k['disziplin']=='Kürlaufen' and ev['name']=='WM Rimini 2024': print('   FS:',k['klasse'],k['gender'],len(k['rows']))
