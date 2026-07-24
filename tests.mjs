// tests.mjs – UI-Regressionstest für Analyse_Tool_DRIV_Rollkunstlauf.html
// Aufruf:   node tests.mjs   (benötigt Node.js + Playwright + Chromium)
// Prüft: alle Tabs, alle Kader-Profile, Kernwerte, Prognose-Regeln, Exporte, Druckmodus, 320-px-Ansicht
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const here = dirname(fileURLToPath(import.meta.url));
const FILE = 'file://' + resolve(here, 'Analyse_Tool_DRIV_Rollkunstlauf.html');
let failed = 0;
const check = (name, ok, extra='') => { console.log((ok?'✓':'✗'), name, extra); if(!ok) failed++; };

const b = await chromium.launch();
const p = await b.newPage({ viewport:{ width:1680, height:1000 } });
const errs = []; p.on('pageerror', e => errs.push(String(e)));
await p.goto(FILE);
await p.waitForFunction(() => document.querySelectorAll('.ovtab').length > 0, { timeout: 30000 });

// 1) Tabs
for (const v of ['kader','vergleich','konstanz','bench','vereine','methodik','daten']) {
  await p.evaluate(x => { state.view = x; state.athlet=''; render(); syncTabs(); }, v);
  await p.waitForTimeout(120);
  check('Tab '+v, await p.evaluate(() => main.children.length > 0));
}

// 2) Alle Kader-Profile
const profErr = await p.evaluate(() => {
  const bad = [];
  KADER.forEach(kd => { try { state.view='kader'; state.athlet=kd.name; render(); }
                        catch(e){ bad.push(kd.name+': '+e.message); } });
  state.athlet=''; state.view='kader'; render();
  return bad;
});
check('79 Athletenprofile fehlerfrei', profErr.length === 0, profErr.slice(0,2).join(' | '));

// 3) Kernwerte (Referenz: DM Stade 2026, Noah Hirsch – aus offiziellem Protokoll)
const core = await p.evaluate(() => {
  const r = rowsOf('Noah Hirsch').find(x => x.ev === 'Deutsche Meisterschaften Stade 2026');
  return r ? r.tes+'/'+r.pcs+'/'+r.total : 'fehlt';
});
check('Kernwerte Hirsch DM 2026 (102.08/63.28/165.36)', core === '102.08/63.28/165.36', core);

// 4) Prognose-Startberechtigung
const prog = await p.evaluate(() => ({
  espoir: projShort('Kürlaufen','Espoir','Damen',55),
  youth:  projShort('Kürlaufen','Youth','Herren',80),
  senior: projShort('Kürlaufen','Senioren','Herren',95),
}));
check('Espoir ohne EM/WM', !/EM|WM/.test(prog.espoir), prog.espoir);
check('Youth mit EM, ohne WM', /EM/.test(prog.youth) && !/WM/.test(prog.youth), prog.youth);
check('Senioren mit WM', /WM/.test(prog.senior), prog.senior);

// 4b) Rückstand auf Platz 1–3 (rechnerische Konsistenz + Anzeige)
const gap = await p.evaluate(() => {
  const cv = curveG('WM','Kürlaufen','Senioren','Herren','tes');
  const p3 = cv ? cv.pts.find(x => x.platz === 3) : null;
  const manuell = p3 ? Math.round((p3.avg - 95) * 100) / 100 : null;
  const kurz = topGapShort('Kürlaufen','Senioren','Herren',95);
  const daten = gapData('Kürlaufen','Senioren','Herren',95,null);
  const wm = daten.find(d => d.typ === 'WM');
  const r3 = wm ? wm.rows.find(r => r.platz === 3) : null;
  state.view='kader'; state.athlet='Noah Hirsch'; render();
  const boxDa = main.textContent.includes('Abstand zu den Referenzwerten für Platz 1–3');
  state.athlet=''; render();
  const spalteDa = main.textContent.includes('Rückstand Platz 3');
  return { manuell, kurz, dT: r3 ? r3.dT : null, boxDa, spalteDa };
});
check('Rückstand: Rechenwert konsistent', gap.manuell !== null && gap.dT === gap.manuell, gap.dT+' vs '+gap.manuell);
check('Rückstand: Kurzform plausibel', /^(WM|EM|EC|IL) P\d: (fehlen |✓)/.test(gap.kurz), gap.kurz);
check('Rückstand: Profil-Box und Übersichts-Spalte vorhanden', gap.boxDa && gap.spalteDa, JSON.stringify({box:gap.boxDa,spalte:gap.spalteDa}));

// 4b2) Basis-Regel: Prognose-Basis ist international, sobald ein internationaler Start vorliegt
const basis = await p.evaluate(() => {
  let verletzt = [], geprueft = 0, natFallback = 0;
  KADER.forEach(kd => {
    const rows = rowsOf(kd.name);
    [...new Set(rows.map(r => r.dis))].forEach(dis => {
      const rel = rows.filter(r => r.dis === dis);
      const b = progBasis(rel, '2026');
      if (!b) return;
      geprueft++;
      const hatInt = rel.some(r => r.herkunft === 'international' && r.tes != null && r.tesOk !== false && r.datum.startsWith('2026'));
      if (hatInt && b.herkunft !== 'international') verletzt.push(kd.name + '/' + dis);
      if (!hatInt) natFallback++;
    });
  });
  const gr = progBasis(rowsOf('Max Grüschow').filter(r => r.dis === 'Kürlaufen'), '2026');
  return { geprueft, natFallback, verletzt, gr: gr ? gr.herkunft + ' ' + gr.tes : 'fehlt' };
});
check('Basis-Regel: int. vor nat. für alle Kader×Disziplin', basis.verletzt.length === 0,
      basis.geprueft + ' geprüft, ' + basis.natFallback + ' nat.-Fallback, Verstöße: ' + basis.verletzt.join(','));
check('Basis-Regel: Grüschow-Basis ist international', basis.gr.startsWith('international'), basis.gr);

// 4c) Vereine & Verbände: Zählung konsistent mit Datenbestand
const ver = await p.evaluate(() => {
  const {list} = vereinsStats();
  let rowsMitVerein = 0, podest = 0;
  DB.forEach(ev => { if (ev.herkunft !== 'national') return;
    ev.kategorien.forEach(k => k.rows.forEach(r => {
      if (!r.club) return; rowsMitVerein++;
      if (r.platz != null && r.platz <= 3) podest++;
    }));
  });
  const sumStarts = list.reduce((s, v) => s + v.startsN, 0);
  const sumPod = list.reduce((s, v) => s + v.podN, 0);
  return { n: list.length, sumStarts, rowsMitVerein, sumPod, podest,
           erb: list.some(v => v.club === 'ERB Bremen' && v.lv === 'Bremen') };
});
check('Vereine: Starts-Summe = Zeilen mit Verein', ver.sumStarts === ver.rowsMitVerein, ver.sumStarts+' vs '+ver.rowsMitVerein);
check('Vereine: Podest-Summe konsistent', ver.sumPod === ver.podest, ver.sumPod+' vs '+ver.podest);
check('Vereine: Liste plausibel (ERB Bremen/Bremen enthalten)', ver.n >= 50 && ver.erb, 'n='+ver.n);

// 4d) v3.7: Sven/Tim-Feedback – Quercheck aller neuen Funktionen
const v37 = await p.evaluate(async () => {
  const out = {};
  // a) Nationale PCS sichtbar + gekennzeichnet (Profil-Tabelle)
  state.view='kader'; state.athlet='Noah Hirsch'; state.showSegs=false; render();
  out.natPcs = [...document.querySelectorAll('td.natv')].some(td => td.textContent.includes('(nat.)'));
  // b) Cut-Kennzeichnung im Datenmodell (Beispiel: Rückzug nach Kurzprogramm, AWC Finale)
  const izadi = (athletIndex().get('Izadi Ruiz Monge') || []).find(r => r.ev.includes('Finale Cesena'));
  out.cutFlag = !!(izadi && izadi.cut);
  // c) Schalter TES je Programmteil
  state.showSegs = true; render();
  out.segCol = [...document.querySelectorAll('th')].some(th => th.textContent.includes('TES je Programmteil'));
  const resTbl = [...document.querySelectorAll('table')].find(t => t.textContent.includes('Rechenweg'));
  out.segVals = resTbl ? /(KP|Kür|SD|KT|PT) \d/.test(resTbl.textContent) : false;
  state.showSegs = false; state.athlet=''; render();
  // d) Referenz-Ausschluss (experimentell): EM 2023 ausblenden → EM-Kurvenfenster ändert sich
  const before = curveG('EM','Kürlaufen','Senioren','Herren','tes').years.join(',');
  state.exclEvents = ['EM Ponte di Legno 2023']; render();
  const after = curveG('EM','Kürlaufen','Senioren','Herren','tes').years.join(',');
  out.exclWirkt = before !== after && !after.includes('2023');
  const mainEl = document.getElementById('main');
  out.exclBanner = mainEl.textContent.includes('Experimentelle Referenzbasis');
  state.exclEvents = []; render();
  out.exclBannerWeg = !mainEl.textContent.includes('Experimentelle Referenzbasis');
  out.exclReset = curveG('EM','Kürlaufen','Senioren','Herren','tes').years.join(',') === before;
  // e) Kader-Verwaltung: aufnehmen als Beobachtung + entfernen + zurücksetzen
  const n0 = KADER.length;
  KADER.push({name:'Catarina Cunha Craveiro',gruppe:'Beobachtung',lv:null,varianten:['Catarina Cunha Craveiro'],inoffiziell:true});
  invalidateDB(); state.view='kader'; render();
  out.beobBadge = document.body.textContent.includes('Beobachtung (inoffiziell)');
  kaderReset(); invalidateDB(); render();
  out.kaderReset = KADER.length === n0 && !KADER.some(k => k.inoffiziell);
  // f) Nationen-/LV-Scopes
  state.view='vereine'; state.natScope='welt'; state.lvScope='dm'; render();
  const txtWelt = document.body.textContent;
  out.scopeWelt = txtWelt.includes('weltoffene Wettbewerbe') && txtWelt.includes('nur Deutsche Meisterschaften');
  state.natScope='alle'; state.lvScope='alle'; render();
  out.scopeAlle = document.body.textContent.includes('eingeschränkt vergleichbar');
  state.natScope='welt'; state.lvScope='dm'; state.view='kader'; render();
  // g) Kader-Verwaltung sichtbar im Daten-Tab
  state.view='daten'; render();
  out.verwaltungDa = document.body.textContent.includes('Kaderliste & Beobachtung – Verwaltung');
  state.view='kader'; render();
  return out;
});
check('v3.7 PCS national sichtbar + (nat.)-Kennzeichnung', v37.natPcs);
check('v3.7 Cut-Kennzeichnung (nicht beendet) im Datenmodell', v37.cutFlag);
check('v3.7 Schalter TES je Programmteil', v37.segCol && v37.segVals);
check('v3.7 Referenz-Ausschluss wirkt + Banner + Reset', v37.exclWirkt && v37.exclBanner && v37.exclBannerWeg && v37.exclReset, JSON.stringify({w:v37.exclWirkt,b:v37.exclBanner,weg:v37.exclBannerWeg,r:v37.exclReset}));
check('v3.7 Beobachtungs-Athlet + Badge + Zurücksetzen', v37.beobBadge && v37.kaderReset);
check('v3.7 Vergleichs-Scopes Nationen/Landesverbände', v37.scopeWelt && v37.scopeAlle);
check('v3.7 Kader-Verwaltung im Daten-Tab', v37.verwaltungDa);

// 4e) v3.8: Element-Konstanz & Schwächen + Component-Profil
const v38 = await p.evaluate(() => {
  const out = {};
  // Detaildaten vorhanden und plausibel
  out.dataDa = !!(DETAILS && DETAILS.det && DETAILS.refc && DETAILS.names);
  out.profileN = DETAILS ? Object.keys(DETAILS.det).length : 0;
  // Martino-Profil: Konstanz-Karte + Element-Status + Component-Balken
  state.view='kader'; state.athlet='Tiziano Martino'; render();
  const heads=[...document.querySelectorAll('#main h2')].map(h=>h.textContent);
  out.kzCard = heads.some(h=>h.includes('Element-Konstanz'));
  out.estat = document.querySelectorAll('.estat').length;
  out.bars  = document.querySelectorAll('.cbar').length;
  // 3S (Salchow) muss als Baustelle erkannt sein (Ø GOE stark negativ, viele Unterrotationen)
  const d = DETAILS.det['Tiziano Martino|Kürlaufen'];
  const s3 = d.el.find(e=>e.c==='3S');
  out.s3neg = s3 && s3.q < -0.3 && s3.dg > 10;
  // Schritte sicher (positive GOE): St2
  const st = d.el.find(e=>e.c==='St2');
  out.stOk = st && st.q >= 0;
  // Klassifikation: NJ ist ausgeblendet
  out.njRaw = d.el.some(e=>e.c==='NJ');            // roh vorhanden
  out.njShown = classifyEl(d.el.find(e=>e.c==='NJ')) === null; // aber ausgeblendet
  // Component-Profil international vorhanden + Referenzmarke
  const cp = compProfile('Tiziano Martino','Kürlaufen');
  out.cpDa = !!cp && cp.querySelectorAll('.cbar i.ref').length >= 3;
  // Konsistenz: konstanz.json Panel-Summe stimmt (Stichprobe: Element-Ø plausibel)
  out.qFinite = d.el.filter(e=>e.c!=='NJ').every(e=>e.q==null||(e.q>-5&&e.q<5));
  state.athlet=''; render();
  return out;
});
check('v3.8 Detaildaten eingebettet (Elemente + Referenz + Namen)', v38.dataDa, 'Profile: '+v38.profileN);
check('v3.8 Konstanz-Karte im Profil (Status-Badges + Component-Balken)', v38.kzCard && v38.estat >= 10 && v38.bars >= 3, JSON.stringify({estat:v38.estat,bars:v38.bars}));
check('v3.8 Schwäche erkannt (3S Salchow: neg. GOE + Unterrotationen)', v38.s3neg);
check('v3.8 Stärke erkannt (Schrittfolge St2 positive GOE)', v38.stOk);
check('v3.8 Kombi-Platzhalter „No Jump" ausgeblendet', v38.njRaw && v38.njShown);
check('v3.8 Component-Profil mit int. Referenzmarken', v38.cpDa);
check('v3.8 Element-GOE-Werte plausibel (keine Ausreißer)', v38.qFinite);

// 4f) v3.9: Podium-Inhaltsvergleich, Konstanz-Übersicht, Abzugsmuster
const v39 = await p.evaluate(() => {
  const out = {};
  out.refelDa = !!(DETAILS.refel && Object.keys(DETAILS.refel).length >= 20);
  // Podium-Referenz plausibel: Junioren-Herren-Kür enthält 2A mit hohem Programm-Anteil
  const jm = DETAILS.refel['Kürlaufen|Junioren|Herren'];
  out.refelPlausibel = jm && jm.el['2A'] && jm.el['2A'][0] > 0.8 && jm.n >= 20;
  // Profil Martino: Podium-Abschnitt + Abzugsmuster + Differenzen
  state.view='kader'; state.athlet='Tiziano Martino'; render();
  const txt=document.getElementById('main').textContent;
  out.podiumSec = txt.includes('Programm-Inhalt im Vergleich zum internationalen Podium');
  out.abzugSec  = txt.includes('Abzugsmuster');
  // Übersichts-Tab: Zeilen für alle Kader-Disziplinen, Badges, Klick-Navigation
  state.view='konstanz'; state.athlet=''; render();
  const rows=document.querySelectorAll('#main table tr').length-1;
  out.ovRows = rows >= 60;
  out.ovBadges = document.querySelectorAll('#main .estat').length >= 100;
  const link=[...document.querySelectorAll('#main a')].find(a=>a.textContent==='Noah Hirsch');
  if(link){ link.click(); out.navWorks = state.view==='kader' && state.athlet==='Noah Hirsch'; }
  state.view='kader'; state.athlet=''; render();
  return out;
});
check('v3.9 Podium-Element-Inventar eingebettet + plausibel (2A Junioren)', v39.refelDa && v39.refelPlausibel);
check('v3.9 Profil: Podium-Vergleich + Abzugsmuster', v39.podiumSec && v39.abzugSec);
check('v3.9 Konstanz-Übersicht (Zeilen + Ampel-Badges + Klick öffnet Profil)', v39.ovRows && v39.ovBadges && v39.navWorks, JSON.stringify(v39));

// 4g) Audit-Fixes: 0-Punkte-Elemente nie "sicher", Podium-Inventar ohne 0-Werte, Component-Text korrekt
const aud = await p.evaluate(() => {
  const out = {};
  // Kein Element mit Grundwert ~0 darf als "sicher"/"ok" klassifiziert werden – über ALLE Profile
  out.zeroOk = 0; out.zeroFail = 0;
  Object.values(DETAILS.det).forEach(d => d.el.forEach(e => {
    const c = classifyEl(e);
    if (c && e.b != null && e.b <= 0.05) { (c.cls === 'fail') ? out.zeroFail++ : (c.cls === 'ok' ? out.zeroOk++ : 0); }
  }));
  // refel enthält keine 0-Punkte-Codes mehr
  out.refelClean = Object.values(DETAILS.refel).every(r => Object.values(r.el).every(v => v[1] > 0.05));
  // Component-Text: kein Doppel-Minus, korrekte Formulierung bei Athleten ÜBER der Referenz (Martino)
  state.view='kader'; state.athlet='Tiziano Martino'; render();
  const txt = document.getElementById('main').textContent;
  out.noDblMinus = !txt.includes('−-') && !txt.includes('--');
  out.aboveRefTxt = txt.includes('auf oder über dem Podium-Referenzwert') || txt.includes('Größter Component-Rückstand');
  // Übersicht: "stärkste Elemente" enthalten kein "No Level"
  state.view='konstanz'; state.athlet=''; render();
  const rows=[...document.querySelectorAll('#main table tr')];
  const okColIdx=7; // Spalte "stärkste Elemente"
  out.noNLinTop = rows.slice(1).every(tr => { const td=tr.children[okColIdx]; return !td || !/No [Ll]evel/.test(td.textContent); });
  state.view='kader'; render();
  return out;
});
check('Audit: 0-Punkte-Elemente = "ohne Level", nie "sicher"', aud.zeroOk === 0 && aud.zeroFail > 0, JSON.stringify({ok:aud.zeroOk,fail:aud.zeroFail}));
check('Audit: Podium-Inventar ohne 0-Punkte-Codes', aud.refelClean);
check('Audit: Component-Fazit ohne Doppel-Minus, korrekt formuliert', aud.noDblMinus && aud.aboveRefTxt);
check('Audit: Übersicht "stärkste Elemente" ohne No-Level-Einträge', aud.noNLinTop);

// 5) Exporte (XLSX + CSV)
let dl = p.waitForEvent('download', { timeout: 15000 }).catch(() => null);
await p.click('button:has-text("Excel (XLSX)")');
check('XLSX-Export', !!(await dl));
dl = p.waitForEvent('download', { timeout: 15000 }).catch(() => null);
await p.click('.fltbar button:has-text("CSV")');
check('CSV-Export', !!(await dl));

// 6) Druckmodus: Kopf/Fuß ausgeblendet, Athleten-Kurzhinweis eingeblendet
await p.evaluate(() => { state.view='kader'; state.athlet='Noah Hirsch'; render(); });
await p.waitForTimeout(250);
await p.emulateMedia({ media: 'print' });
const pr = await p.evaluate(() => ({
  brand: getComputedStyle(document.querySelector('.brandbar')).display,
  foot:  getComputedStyle(document.querySelector('.foot')).display,
  note:  getComputedStyle(document.querySelector('.printonly')).display,
}));
await p.emulateMedia({ media: 'screen' });
check('Druck: Kopf/Fuß aus, Kurzhinweis an',
      pr.brand === 'none' && pr.foot === 'none' && pr.note === 'block', JSON.stringify(pr));

// 7) Mobile 320 px ohne Seiten-Scroll
const m = await b.newPage({ viewport: { width: 320, height: 700 } });
await m.goto(FILE); await m.waitForTimeout(1200);
check('320 px ohne horizontales Seiten-Scrollen',
      !(await m.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 4)));

check('Keine JavaScript-Fehler', errs.length === 0, errs.slice(0,2).join(' | '));
await b.close();
console.log(failed === 0 ? '\nALLE TESTS BESTANDEN ✓' : `\n${failed} TEST(S) FEHLGESCHLAGEN ✗`);
process.exit(failed === 0 ? 0 : 1);
