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
for (const v of ['kader','vergleich','bench','vereine','methodik','daten']) {
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
