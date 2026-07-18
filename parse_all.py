import subprocess, re, json, glob, os

DIS={'Free Skating':'Kürlaufen','Solo Dance':'Solotanz','Couple Dance':'Rolltanz','Pairs':'Paarlauf'}
KL={'Seniores':'Senioren','Juniores':'Junioren','Youth':'Youth','Cadets':'Cadets','Espoire':'Espoir','Espoir':'Espoir','Minis':'Minis','Tots':'Tots'}
BAD=('PANEL','JUDGES','RESULT','REVISED','DETAILS','VERIFIED','WORLDSKATE','TECHNICAL','OFFICIAL')
FULL=re.compile(r'((?:Free Skating|Solo Dance|Couple Dance|Pairs)\s*(?:Ladies|Men)?\s*(?:Seniores|Juniores|Youth|Cadets|Espoire|Espoir|Minis|Tots))\s*(?:-\s*(.+?))?\s*(?:REVISED.*)?$')
CLUB=r'(?:REV|SC|TV|TGS|VER|VFL|REC|RSV|MTV|PSV|ERC|ERB|RST|FT|SV|OSC|ERV|SF|RRV|1\.|WEDDINGER|WEDDIMGER|NEUKÖLLNER|NEUKÖLLER|NEUKÖLNER|GÜSTROWER|FREIBURGER|ESCHWEILER|HANAUER|ROLLSCHUHPARADIES|KSG|RRD|TSV|SG|REG|TBV|TUS|NORDHEIMER|DELMENHORSTER|ALTONAER|REMSCHEIDER)'
def tcase(n): return ' '.join(w.capitalize() for w in n.title().split())
_CLUBUP={'REV','SC','TV','TGS','VFL','REC','RSV','MTV','PSV','ERC','ERB','RST','FT','SV','OSC','ERV','SF','RRV','KSG','RRD','TSV','SG','REG','TBV','TUS','RSC','EV','VER','VFR','DJK','ESV'}
def _capw(w):
    core=w.rstrip('.')
    if core.upper() in _CLUBUP: return core.upper()+('.' if w.endswith('.') else '')
    return '-'.join(p.capitalize() for p in w.split('-'))
def clubcase(c):
    # Vereinsnamen lesbar machen: bekannte Kürzel groß, Rest wortweise (auch nach Bindestrich) groß
    return ' '.join(_capw(w) for w in c.split())
_LVFIX={'Nied':'Niedersachsen','Niedersachen':'Niedersachsen','Brem':'Bremen','Schl':'Schleswig-Holstein',
        'Berl':'Berlin','Nrw':'Nordrhein-Westfalen','Wriv':'Württemberg','Württtemberg':'Württemberg',
        'Sriv':'Südbaden','Hamb':'Hamburg','Hess':'Hessen','Bay':'Bayern','Sach':'Sachsen'}
# abgeschnittene Zusatzspalten (Nation/LV) am Vereinsende → entfernen, ggf. als LV übernehmen
_TAIL={'ger':'','nie':'Niedersachsen','nied':'Niedersachsen','hes':'Hessen','hess':'Hessen','bay':'Bayern',
       'nrw':'Nordrhein-Westfalen','san':'Sachsen','sach':'Sachsen','schl':'Schleswig-Holstein',
       's-h':'Schleswig-Holstein','sh':'Schleswig-Holstein','berl':'Berlin','brem':'Bremen','hamb':'Hamburg',
       'b-w':'','wriv':'Württemberg','sriv':'Südbaden'}
# Schreibweisen-Kanonisierung (offensichtliche Tippfehler/Varianten aus den Protokollen)
_CLUBFIX={'Weddimger ERC':'Weddinger ERC','FT Freiburh V. 1844':'FT 1844 Freiburg','FT Freiburg V. 1844':'FT 1844 Freiburg',
 'Freiburger FT V. 1844':'FT 1844 Freiburg','Freiburger Turnerschaft':'FT 1844 Freiburg',
 'Freiburger Turnerschaft 1844':'FT 1844 Freiburg','Freiburger Turnerschaft V. 1844':'FT 1844 Freiburg',
 'Freiburger Turnerschaft V.':'FT 1844 Freiburg','Freiburger Turnerschaft Von 1844':'FT 1844 Freiburg',
 'REV Helbronn':'REV Heilbronn','ERC Bremverhaven':'ERC Bremerhaven','TV Jahn Wofsburg':'TV Jahn Wolfsburg',
 'RSV Weil':'RSV Weil Am Rhein','RSV Weil Am Rheim':'RSV Weil Am Rhein','REG Kiel E.v.':'REG Kiel',
 '1.rc Göttingen':'1. RC Göttingen','Eschweiler SG':'SG Eschweiler','Eschweiler SG Rollsport':'SG Eschweiler',
 'MTV Lüneburg':'MTV Treubund Lüneburg','TV Jahn Alverdissen':'TBV Jahn Alverdissen',
 'ERC Bergedorf':'ERV Bergedorf','ERV Viernheim':'ERC Viernheim','TGS Vorwaerts Frankfurt':'TGS Vorwärts Frankfurt',
 'SC Hameln Hilligsfeld':'SC Hameln-Hilligsfeld','SV Wuppertal Neuenhof':'SV Wuppertal-Neuenhof',
 'SV Wuppertal-Neuenhof 1930':'SV Wuppertal-Neuenhof','SV Dresden-Mitte':'SV Dresden Mitte',
 'SV Dresden-Mitte 1950':'SV Dresden Mitte','TV Walsum-Aldenrade':'TV Walsum Aldenrade 07',
 'TV Walsum-Aldenrade 07':'TV Walsum Aldenrade 07','TV Datteln 09':'TV Datteln',
 'RST Hummetal SC Hameln Hilligsfeld':'RST Hummetal','RST Hummetal SC Hameln-Hilligsfeld':'RST Hummetal',
 '1. Kieler REV S-H':'1. Kieler REV','Neuköller SF':'Neuköllner SF','Neukölner SF':'Neuköllner SF'}
def splitclub(raw, prefix=''):
    # "ERB BREMEN (BREMEN) GER" → ('ERB Bremen', 'Bremen'); Klammerzusatz = Landesverband
    raw=raw.strip(); lv=None
    m=re.search(r'\(([^)]+)\)',raw)
    if m:
        lv=' '.join('-'.join(p.capitalize() for p in w.split('-')) for w in m.group(1).strip().split())
        lv=_LVFIX.get(lv,lv)
        raw=(raw[:m.start()]+' '+raw[m.end():]).strip()
    # abgeschnittene Nations-/LV-Spalten am Ende entfernen
    while True:
        ws=raw.split()
        if len(ws)>1 and ws[-1].lower() in _TAIL:
            t=_TAIL[ws[-1].lower()]
            if t and not lv: lv=t
            raw=' '.join(ws[:-1])
        else: break
    if prefix: raw=prefix+' '+raw
    cl=clubcase(raw)
    cl=cl.split(' / ')[0].strip()        # Paare mit zwei Vereinen: erster Verein zählt
    cl=_CLUBFIX.get(cl,cl)
    if cl in ('SF','SV','TV','SC','REV','ERC'): return None, lv   # abgeschnitten/unbrauchbar
    return cl, lv
def cleanclub(n):
    # Vereinsreste am Namensende entfernen (z. B. "1." / "1. Kieler" / "Kieler" von "1. Kieler REV")
    return re.sub(r'(\s+1\.)?(\s+Kieler)?$','',n).strip()

def unvertical(txt):
    # Vertikal gedruckte Kategorie-Titel (1 Buchstabe pro Zeile) zu einer Zeile rekonstruieren
    lines=txt.split('\n'); out=[]; buf=[]
    def flush():
        if len(buf)>=8:
            joined=''.join(l.strip() for l in buf)
            joined=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',joined)
            out.append(joined)
        else:
            out.extend(buf)
        buf.clear()
    for l in lines:
        s=l.strip()
        if len(s)==1 and s.isalpha(): buf.append(l)
        else: flush(); out.append(l)
    flush()
    return '\n'.join(out)

def parse_pdf(path, fmt='nation'):
    txt=subprocess.run(['pdftotext','-layout',path,'-'],capture_output=True,text=True,timeout=400).stdout
    txt=unvertical(txt)
    m=re.search(r'-\s*(\d\d)/(\d\d)/(\d\d\d\d)\s*$',txt,flags=re.M)
    datum=f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else None
    cats={}; cat=None; catname=None; mode=None; lastRow=None; curseg=None
    if fmt=='nation':
        FIN=re.compile(r'(\d+)\s+(.+?)\s+([A-Z]{3})\s+(\d+\.\d\d)\b')
        SEG=re.compile(r'(\d+)\s+(.+?)\s+([A-Z]{3})\s+(\d+\.\d\d)\s+(\d+\.\d\d)\s+(-?\d+\.?\d*)\s+(\d+\.\d\d)\b')
    else:
        FIN=re.compile(r'(\d+)\s+(.+?)\s+('+CLUB+r'\b.*?)\s(\d+\.\d\d)\b')
        SEG=re.compile(r'(\d+)\s+(.+?)\s+('+CLUB+r'\b.*?)\s(\d+\.\d\d)\s+(\d+\.\d\d)\s+(-?\d+\.?\d*)\s+(\d+\.\d\d)\b')
    for ln in txt.split('\n'):
        s=ln.strip()
        # Intermediate-/Breitensport-Kategorien erkennen und getrennt halten (werden nicht ausgewertet)
        if re.match(r'(?:Free Skating|Solo Dance|Couple Dance|Pairs)\s*(?:Ladies|Men)?\s*\w*\s*Intermediate\b',s):
            catname=s.split(' - ')[0].strip()
            cat=cats.setdefault('#IGNORE '+catname,{'final':{},'seg':{}})
            mode=None; lastRow=None; continue
        # Formations-/Gruppenkategorien (Precision, Quartets, Show) sind keine Einzel-/Paar-Wettbewerbe → nicht auswerten
        if re.match(r'(?:Precision|Quartets?|Show ?Groups?)\b',s):
            catname=s.split(' - ')[0].strip()
            cat=cats.setdefault('#IGNORE '+catname,{'final':{},'seg':{}})
            mode=None; lastRow=None; continue
        mh=FULL.match(s)
        if mh:
            catname=mh.group(1).strip()
            curseg=(mh.group(2) or '').strip() or None
            cat=cats.setdefault(catname,{'final':{}, 'seg':{}})
            mode=None; lastRow=None; continue
        if 'FINAL RESULT' in s: mode='final'; lastRow=None; continue
        if 'RESULTS DETAILS' in s: mode='seg'; lastRow=None; continue
        if 'JUDGES DETAILS' in s: mode=None; lastRow=None; continue
        if re.match(r'Pl\.?\s+Name\b',s):
            mode='seg' if 'TES' in s else ('final' if 'Points' in s else None)
            lastRow=None; continue
        if cat is None or mode is None: lastRow=None; continue
        if mode=='final':
            mf=FIN.match(s)
            if not mf and not re.match(r'\d',s):
                if fmt=='nation':
                    m2=re.match(r"([A-ZÄÖÜÉÈÍÓÚÑÇ][^\d]*?)\s+([A-Z]{3})\s+(\d+\.\d\d)\s+(\d+)\s*$",s)
                    if m2:
                        nm=tcase(m2.group(1)); cat['final'][nm]={'platz':int(m2.group(4)),'nat':m2.group(2),'total':float(m2.group(3))}
                        lastRow=('final',nm); continue
                else:
                    m2=re.match(r"([A-ZÄÖÜÉÈÍÓÚÑÇ][^\d]*?)\s+("+CLUB+r"\b.*?)\s(\d+\.\d\d)\s+(\d+)\s*$",s)
                    if m2:
                        nm_raw=tcase(m2.group(1)); nm=cleanclub(nm_raw)
                        cl,lv=splitclub(m2.group(2), prefix=nm_raw[len(nm):].strip())
                        cat['final'][nm]={'platz':int(m2.group(4)),'nat':'GER','total':float(m2.group(3))}
                        if cl: cat['final'][nm]['club']=cl
                        if lv: cat['final'][nm]['lv']=lv
                        lastRow=('final',nm); continue
            if mf:
                nm_raw=tcase(mf.group(2)); nm=nm_raw
                if fmt=='club': nm=cleanclub(nm_raw)
                nat=mf.group(3) if fmt=='nation' else 'GER'
                tot=float(mf.group(4))
                cat['final'][nm]={'platz':int(mf.group(1)),'nat':nat,'total':tot}
                if fmt=='club':
                    cl,lv=splitclub(mf.group(3), prefix=nm_raw[len(nm):].strip())
                    if cl: cat['final'][nm]['club']=cl
                    if lv: cat['final'][nm]['lv']=lv
                lastRow=('final',nm); continue
        else:
            ms=SEG.match(s)
            if not ms and not re.match(r'\d',s):
                if fmt=='nation':
                    m3=re.match(r"([A-ZÄÖÜÉÈÍÓÚÑÇ][^\d]*?)\s+([A-Z]{3})\s+(\d+\.\d\d)\s+(\d+\.\d\d)\s+(-?\d+\.?\d*)\s+(\d+\.\d\d)\s*$",s)
                    if m3:
                        nm=tcase(m3.group(1)); d=cat['seg'].setdefault(nm,{'tes':0.0,'pcs':0.0,'nseg':0,'list':[]})
                        d['tes']=round(d['tes']+float(m3.group(3)),2); d['pcs']=round(d['pcs']+float(m3.group(4)),2); d['nseg']+=1
                        d.setdefault('list',[]).append({'seg':curseg,'tes':float(m3.group(3)),'pcs':float(m3.group(4)),'ded':abs(float(m3.group(5)))})
                        lastRow=('seg',nm); continue
                else:
                    m3=re.match(r"([A-ZÄÖÜÉÈÍÓÚÑÇ][^\d]*?)\s+"+CLUB+r"\b.*?\s(\d+\.\d\d)\s+(\d+\.\d\d)\s+(-?\d+\.?\d*)\s+(\d+\.\d\d)\s*$",s)
                    if m3:
                        nm=cleanclub(tcase(m3.group(1))); d=cat['seg'].setdefault(nm,{'tes':0.0,'pcs':0.0,'nseg':0,'list':[]})
                        d['tes']=round(d['tes']+float(m3.group(2)),2); d['pcs']=round(d['pcs']+float(m3.group(3)),2); d['nseg']+=1
                        d.setdefault('list',[]).append({'seg':curseg,'tes':float(m3.group(2)),'pcs':float(m3.group(3)),'ded':abs(float(m3.group(4)))})
                        lastRow=('seg',nm); continue
            if ms:
                nm=tcase(ms.group(2))
                if fmt=='club': nm=cleanclub(nm)
                if fmt=='nation': tes,pcs,ded=float(ms.group(4)),float(ms.group(5)),abs(float(ms.group(6)))
                else: tes,pcs,ded=float(ms.group(4)),float(ms.group(5)),abs(float(ms.group(6)))
                d=cat['seg'].setdefault(nm,{'tes':0.0,'pcs':0.0,'nseg':0,'list':[]})
                d['tes']=round(d['tes']+tes,2); d['pcs']=round(d['pcs']+pcs,2); d['nseg']+=1
                d.setdefault('list',[]).append({'seg':curseg,'tes':tes,'pcs':pcs,'ded':ded})
                lastRow=('seg',nm); continue
        if lastRow and ('Couple' in catname or 'Pairs' in catname) and re.fullmatch(r"[A-ZÄÖÜÉÈÍÓÚÑÇ'’\-\. ]{4,}",s) and not any(b in s for b in BAD):
            p=tcase(s); kind,key=lastRow
            if kind=='final':
                rec=cat['final'].pop(key); newk=key+' / '+p
                if newk not in cat['final']: cat['final'][newk]=rec
                lastRow=('final',newk)
            else:
                d=cat['seg'].pop(key); newk=key+' / '+p
                t=cat['seg'].get(newk)
                if t:
                    t['tes']=round(t['tes']+d['tes'],2); t['pcs']=round(t['pcs']+d['pcs'],2); t['nseg']+=d['nseg']
                    t.setdefault('list',[]).extend(d.get('list',[]))
                else:
                    cat['seg'][newk]=d
                lastRow=('seg',newk)
            continue
        lastRow=None
    # geschlechtslose Kategorien (aus rekonstruierten Vertikal-Titeln) in eindeutiges Geschlechts-Pendant mergen
    for base in list(cats.keys()):
        md=re.match(r'(Free Skating|Solo Dance)\s+(Seniores|Juniores|Youth|Cadets|Espoire|Espoir|Minis|Tots)$',base)
        if not md: continue
        sibs=[f'{md.group(1)} {g} {md.group(2)}' for g in ('Ladies','Men') if f'{md.group(1)} {g} {md.group(2)}' in cats]
        if len(sibs)!=1: continue
        tgt=cats[sibs[0]]; src=cats.pop(base)
        for nm,v in src['final'].items(): tgt['final'].setdefault(nm,v)
        for nm,v in src['seg'].items(): tgt['seg'].setdefault(nm,v)
    return cats,datum

def cats_to_kats(cats):
    out=[]
    for base,c in cats.items():
        md=re.match(r'(Free Skating|Solo Dance|Couple Dance|Pairs)\s*(Ladies|Men)?\s*(\S+)$',base)
        if not md or (not c['final'] and not c['seg']): continue
        rows=[]
        if c['final']:
            for nm,f in c['final'].items():
                sg=c['seg'].get(nm) or c['seg'].get(nm.split(' / ')[0]) or {}
                row={'name':nm,'nat':f['nat'],'platz':f['platz'],'total':f['total'],
                     'tes':sg.get('tes'),'pcs':sg.get('pcs'),'nseg':sg.get('nseg',0),'segs':sg.get('list') or None}
                if f.get('club'): row['club']=f['club']
                if f.get('lv'): row['lv']=f['lv']
                rows.append(row)
        else:
            for nm,sg in c['seg'].items():
                rows.append({'name':nm,'nat':None,'platz':None,'total':None,
                             'tes':sg['tes'],'pcs':sg['pcs'],'nseg':sg['nseg'],'segs':sg.get('list') or None})
        rows.sort(key=lambda r:(r['platz'] is None, r['platz'] or 0))
        out.append({'disziplin':DIS[md.group(1)],'klasse':KL.get(md.group(3),md.group(3)),'gender':{'Ladies':'Damen','Men':'Herren'}.get(md.group(2) or '',''),'rows':rows})
    return out

def merge_event(ev, cats):
    for k in cats_to_kats(cats):
        ex=next((q for q in ev['kategorien'] if q['disziplin']==k['disziplin'] and q['klasse']==k['klasse'] and q['gender']==k['gender']),None)
        if ex is None: ev['kategorien'].append(k); continue
        byname={r['name']:r for r in ex['rows']}
        byfirst={r['name'].split(' / ')[0]:r for r in ex['rows']}
        for r in k['rows']:
            t=byname.get(r['name']) or byfirst.get(r['name'].split(' / ')[0])
            if t is not None:
                if r['nseg'] and r['tes'] is not None:
                    newTes=round((t['tes'] or 0)+r['tes'],2); newPcs=round((t['pcs'] or 0)+(r['pcs'] or 0),2)
                    tot=t['total'] or r['total']
                    # Guard gegen Doppelzählung: TES+PCS darf Gesamtwert nicht deutlich übersteigen
                    if tot is None or newTes+newPcs<=tot+6:
                        t['tes']=newTes; t['pcs']=newPcs; t['nseg']=(t['nseg'] or 0)+r['nseg']
                        if r.get('segs'):
                            t['segs']=(t.get('segs') or [])+r['segs']
                if r['total'] and not t.get('total'): t['total']=r['total']
                if r['platz'] and not t.get('platz'): t['platz']=r['platz']
                if r['nat'] and not t.get('nat'): t['nat']=r['nat']
                if r.get('club') and not t.get('club'): t['club']=r['club']
                if r.get('lv') and not t.get('lv'): t['lv']=r['lv']
            else:
                ex['rows'].append(r); byname[r['name']]=r; byfirst[r['name'].split(' / ')[0]]=r
        ex['rows'].sort(key=lambda r:(r['platz'] is None, r['platz'] or 0))

JOBS=[
 # Sammel-PDFs 2023 + AIS
 ({'typ':'EM','jahr':2023,'name':'EM Ponte di Legno 2023'},['data/em2023_free.pdf','data/em2023_solo.pdf','data/em2023_dance.pdf','data/em2023_pairs.pdf'],'nation'),
 ({'typ':'WM','jahr':2023,'name':'WM Ibagué 2023'},['data/wm2023_free.pdf','data/wm2023_solo.pdf','data/wm2023_dance.pdf','data/wm2023_pairs.pdf'],'nation'),
 ({'typ':'WC-SA','jahr':2024,'name':'AIS Brasília 2024'},sorted(glob.glob('data/ais_brasilia2024/*.pdf')),'nation'),
 ({'typ':'WC-EU','jahr':2024,'name':'AIS Triest 2024'},sorted(glob.glob('data/ais_triest2024/*.pdf')),'nation'),
 ({'typ':'WC-SA','jahr':2025,'name':'AIS Buenos Aires 2025'},['data/ais_ba_free.pdf','data/ais_ba_solo.pdf','data/pairs_new/ba2025_paare.pdf','data/pairs_new/ba2025_rolltanz.pdf'],'nation'),
 ({'typ':'WC-EU','jahr':2025,'name':'AIS Triest 2025'},['data/ais_tri_free.pdf','data/ais_tri_solo.pdf','data/ais_tri_dance.pdf','data/pairs_new/triest2025_pairs.pdf'],'nation'),
 ({'typ':'WC-F','jahr':2025,'name':'AIS-Finale Reggio Emilia 2025'},['data/ais_reg_free.pdf','data/ais_reg_solo.pdf'],'nation'),
 ({'typ':'WC-SA','jahr':2026,'name':'AWC Buenos Aires 2026'},sorted(glob.glob('data/awc26/WCB_*.pdf')),'nation'),
 ({'typ':'WC-EU','jahr':2026,'name':'AWC Semi-Final Garmisch 2026'},sorted(glob.glob('data/awc26/2026_WCG_*.pdf')),'nation'),
 ({'typ':'WC-F','jahr':2026,'name':'AWC Finale Cesena 2026'},sorted(glob.glob('data/awc/fin_*.pdf')),'nation'),
 ({'typ':'IL','jahr':2023,'name':'Interland Cup Mierlo 2023'},['/home/claude/driv-dashboard/data/interland_2023.pdf'],'nation'),
 ({'typ':'IL','jahr':2024,'name':'Interland Cup Bonn 2024'},['/home/claude/driv-dashboard/data/interland_2024.pdf'],'nation'),
 ({'typ':'IL','jahr':2025,'name':'Interland Cup Zürich 2025'},['/home/claude/driv-dashboard/data/interland_2025.pdf'],'nation'),
 ({'typ':'National','jahr':2026,'name':'Deutsche Meisterschaften Stade 2026'},sorted(glob.glob('data/dm26off/*.pdf'))+sorted(glob.glob('/home/claude/driv-dashboard/data/dm/*.pdf'))+['data/dm/dm26_paarlauf.pdf'],'club'),
]
RLW23=[('2023-02-24','RLW Bonn (DM Show) 2023',['data/rlw23/2023_Bonn_Ergebnisse_Kuerlaufen_.pdf','data/rlw23/2023_Bonn_Ergebnisse_Tanz.pdf']),
 ('2023-03-24','RLW Wolfsburg (Hans-Bauer-Pokal) 2023',['data/rlw23/2023_RLW_Wolfsburg_Ergebnisse.pdf']),
 ('2023-08-26','RLW Lübeck 2023',['data/rlw23/RL-Wettb_Luebeck_2023_-_Ergebnisse.pdf']),
 ('2023-10-07','RLW Hamburg-Bergedorf 2023',['data/rlw23/RL-Wettb_Bergedorf_-_Ergebnisse.pdf']),
 ('2023-10-21','RLW Duisburg 2023',['data/rlw23/RL-Wettb_Duisburg_2023_-_Ergebnisse.pdf'])]
for dat,nm,fls in RLW23:
    JOBS.append(({'typ':'National','jahr':2023,'name':nm},fls,'club'))
RLW=[('2024-02-25','RLW Eppingen (DM Show) 2024',['data/rlw/24_eppingen_kuer.pdf','data/rlw/24_eppingen_tanz.pdf']),
 ('2024-03-10','RLW Stade 2024',['data/rlw/24_stade_kuer.pdf']),
 ('2024-08-18','RLW Bremen 2024',['data/rlw/24_bremen_solo.pdf','data/rlw/24_bremen_dance.pdf']),
 ('2024-09-01','NDM/RLW Bremerhaven 2024',['data/rlw/24_ndm_free.pdf','data/rlw/24_ndm_solo.pdf','data/rlw/24_ndm_dance.pdf']),
 ('2024-09-29','RLW Darmstadt 2024',['data/rlw/24_darmstadt_kuer.pdf']),
 ('2025-03-02','RLW Kiel (DM Show) 2025',['data/rlw/25_kiel_kuer.pdf','data/rlw/25_kiel_tanz.pdf']),
 ('2025-03-16','RLW Stade 2025',['data/rlw/25_stade_kuer.pdf','data/rlw/25_stade_tanz.pdf']),
 ('2025-04-06','RLW Ober-Ramstadt 2025',['data/rlw/25_oberramstadt.pdf']),
 ('2025-06-01','RLW Göttingen (IGC) 2025',['data/rlw/25_goettingen_kuer.pdf','data/rlw/25_goettingen_solo.pdf']),
 ('2025-08-17','RLW Winnenden 2025',['data/rlw/25_winnenden_solo.pdf','data/rlw/25_winnenden_dance.pdf']),
 ('2025-09-28','RLW Duisburg 2025',['data/rlw/25_duisburg.pdf']),
 ('2025-10-12','RLW Ismaning 2025',['data/rlw/25_ismaning.pdf']),
 ('2026-03-01','RLW Freiburg (DM Show) 2026',['data/rlw/26_freiburg_kuer.pdf','data/rlw/26_freiburg_tanz.pdf']),
 ('2026-03-15','RLW Berlin 2026',['data/rlw/26_berlin_kuer.pdf','data/rlw/26_berlin_tanz.pdf']),
 ('2026-03-29','RLW Eppingen 2026',['data/rlw/26_eppingen.pdf'])]
for dat,nm,fls in RLW:
    JOBS.append(({'typ':'National','jahr':int(dat[:4]),'name':nm},fls,'club'))
JOBS.append(({'typ':'National','jahr':2023,'name':'Deutsche Meisterschaften Bayreuth 2023'},sorted(glob.glob('data/dm/dm23_*.pdf')),'club'))
JOBS.append(({'typ':'National','jahr':2024,'name':'Deutsche Meisterschaften Stade 2024'},sorted(glob.glob('data/dm/dm24_*.pdf')),'club'))
JOBS.append(({'typ':'National','jahr':2025,'name':'Deutsche Meisterschaften Ober-Ramstadt 2025'},sorted(glob.glob('data/dm/dm25_*.pdf')),'club'))
JOBS.append(({'typ':'IGC','jahr':2025,'name':'Int. Deutschland-Pokal Göttingen 2025'},['data/igc2025.pdf'],'nation'))
JOBS.append(({'typ':'IGC','jahr':2026,'name':'Int. Deutschland-Pokal Freiburg 2026'},['data/igc2026_free.pdf','data/igc2026_solo.pdf'],'nation'))
JOBS.append(({'typ':'CoE','jahr':2024,'name':'Cup of Europe Zürich 2024'},['data/coe2024_free.pdf','data/coe2024_solo.pdf','data/coe2024_dance.pdf','data/coe2024_pairs.pdf'],'nation'))
JOBS.append(({'typ':'CoE','jahr':2023,'name':'Cup of Europe Pula 2023'},sorted(glob.glob('data/coe23/*.pdf')),'nation'))
JOBS.append(({'typ':'CoE','jahr':2025,'name':'Cup of Europe Matosinhos 2025'},sorted(glob.glob('data/coe25/*FINAL*.pdf'))+sorted(glob.glob('data/coe25/*RESULTS*.pdf')),'nation'))

import hashlib
def dedup(files):
    seen=set(); out=[]
    for f in files:
        if not os.path.exists(f): continue
        h=hashlib.md5(open(f,'rb').read()).hexdigest()
        if h in seen: continue
        seen.add(h); out.append(f)
    return out

seed=json.load(open('data/seed_international.json'))
# Paarlauf-PDFs in die Basis-Events (EM/WM 2024/2025) einmergen
PAIRS_ADD=[('EM Fafe 2024','data/pairs_new/em2024_pairs.pdf'),
 ('EM Triest 2025','data/pairs_new/em2025_pairs.pdf'),
 ('WM Rimini 2024','data/pairs_new/wm2024_pairs.pdf'),
 ('WM Peking 2025','data/pairs_new/wm2025_pairs.pdf')]
for evname,pf in PAIRS_ADD:
    ev=next((e for e in seed if e['name']==evname),None)
    if ev is None or not os.path.exists(pf):
        print('PAIRS-MERGE FEHLT',evname,pf); continue
    try:
        cats,_=parse_pdf(pf,'nation')
        merge_event(ev,cats)
        print('PAIRS →',evname,'| Kat gesamt:',len(ev['kategorien']))
    except Exception as e:
        print('FEHLER PAIRS',pf,e)
for meta,files,fmt in JOBS:
    files=dedup(files)
    ev={'typ':meta['typ'],'jahr':meta['jahr'],'name':meta['name'],'datum':None,
        'herkunft':('national' if meta['typ']=='National' else 'international'),'kategorien':[]}
    for f in files:
        if not os.path.exists(f): continue
        try:
            cats,datum=parse_pdf(f,fmt)
            if datum and (ev['datum'] is None or datum<ev['datum']): ev['datum']=datum
            merge_event(ev,cats)
        except Exception as e:
            print('FEHLER',f,e)
    if ev['datum'] is None: ev['datum']=f"{meta['jahr']}-01-01"
    n=sum(len(k['rows']) for k in ev['kategorien'])
    miss=sum(1 for k in ev['kategorien'] for r in k['rows'] if r['tes'] is None)
    print(ev['name'],'| Kat:',len(ev['kategorien']),'| Starter:',n,'| ohne TES:',miss,'| Datum:',ev['datum'])
    if n: seed.append(ev)
json.dump(seed,open('data/seed_v2.json','w'),ensure_ascii=False,indent=1)
print('GESAMT Events:',len(seed),'Ergebnisse:',sum(len(k['rows']) for e in seed for k in e['kategorien']))
