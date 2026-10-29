#!/usr/bin/env node
/**
 * Ordinary result import must reject synthetic-replay display files.
 * The synthetic page must reject ordinary result / recipe schemas and any
 * display whose website_import_supported is not false.
 *
 * Usage: node check_website_import.mjs <generated-display.json>
 * Exit 0 and print {"verdict":"blocks",...} when every probe is rejected
 * or, for a false flag, accepted without entering `results`.
 */
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../../../..');
const source = await readFile(path.join(root, 'dist/app.js'), 'utf8');
const runnable = JSON.parse(await readFile(path.join(root, 'dist/runnable.json'), 'utf8'));
const r01 = JSON.parse(await readFile(path.join(root, 'harness/results/R01-selfcheck.json'), 'utf8')).reference;
const liveDisplayPath = process.argv[2];
if (!liveDisplayPath) {
  console.error('usage: node check_website_import.mjs <display.json>');
  process.exit(1);
}
const liveDisplay = JSON.parse(await readFile(liveDisplayPath, 'utf8'));

async function load(name) {
  return JSON.parse(await readFile(path.join(here, name), 'utf8'));
}
const fixtures = {
  minimal: await load('minimal-display.json'),
  websiteTrue: await load('display-website-true.json'),
  websiteOmitted: await load('display-website-omitted.json'),
  engineering: await load('ordinary-engineering.json'),
  ordinary: await load('ordinary-result.json'),
  record: await load('synthetic-record.json'),
  recipe: await load('recipe-actual.json'),
};

const decode = s => s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const ids = new Map();
const groups = new Map();
class Element {
  constructor() { this.value = ''; this.textContent = ''; this.dataset = {}; this.checked = false; this.open = false; this.markup = ''; this.children = []; this.classList = {toggle() {}}; }
  set innerHTML(html) {
    for (const child of this.children) {
      if (child.id) ids.delete('#' + child.id);
      for (const entries of groups.values()) {
        const index = entries.indexOf(child);
        if (index >= 0) entries.splice(index, 1);
      }
    }
    this.children = [];
    this.markup = html;
    for (const match of html.matchAll(/<(?:input|select|button|p|div|pre)\b([^>]*)>/g)) {
      const attrs = match[1];
      const el = new Element();
      for (const attribute of attrs.matchAll(/([\w-]+)="([^"]*)"/g)) {
        const value = decode(attribute[2]);
        if (attribute[1] === 'id') { el.id = value; ids.set('#' + value, el); }
        if (attribute[1] === 'value') el.value = value;
        if (attribute[1].startsWith('data-')) {
          el.dataset[attribute[1].slice(5)] = value;
          const sel = '[' + attribute[1] + ']';
          if (!groups.has(sel)) groups.set(sel, []);
          groups.get(sel).push(el);
        }
      }
      this.children.push(el);
    }
  }
  get innerHTML() { return this.markup; }
  addEventListener() {}
  focus() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
}
for (const id of ['content', 'detail', 'detailContent', 'closeDetail', 'total', 'runnable', 'repoLink']) ids.set('#' + id, new Element());
const nav = ['start', 'catalog', 'planner', 'results', 'synthetic', 'protocol', 'roadmap'].map(view => {
  const element = new Element();
  element.dataset.view = view;
  return element;
});
const ctx = vm.createContext({
  console, Blob, Date, setTimeout: fn => { fn(); return 0; },
  URL: {createObjectURL() { return 'blob:test'; }, revokeObjectURL() {}},
  document: {
    querySelector: selector => ids.get(selector),
    querySelectorAll: selector => selector === 'nav button' ? nav : (groups.get(selector) || []),
    createElement() { return {click() {}}; },
  },
  localStorage: {getItem: () => null, setItem() {}},
  fetch: async name => ({ok: true, json: async () => name === 'runnable.json' ? runnable : []}),
});
vm.runInContext(source, ctx, {filename: 'dist/app.js'});
await new Promise(setImmediate);
vm.runInContext("view='results';renderResults()", ctx);

async function importResult(value, name = 'result.json') {
  const text = JSON.stringify(value);
  await ids.get('#resultFile').onchange({target: {files: [{name, size: Buffer.byteLength(text), text: async () => text}]}});
  return vm.runInContext('({results: results.length, message: resultMessage})', ctx);
}

function probe(value) {
  vm.runInContext('payload = ' + JSON.stringify(value), ctx);
  return vm.runInContext(`(() => { try { validateSyntheticDisplay(payload); return {ok:true, results:results.length}; } catch (e) { return {ok:false, error:e.message, results:results.length}; } })()`, ctx);
}

const report = {checks: {}};
const r01Import = await importResult(r01, 'R01-reference.json');
report.results_after_r01 = r01Import.results;
const displayImport = await importResult(liveDisplay, 'display.json');
report.results_after_display = displayImport.results;
report.display_import_error = displayImport.message;
const kept = r01Import.results;
const failures = [];
if (r01Import.results !== 1) failures.push('ordinary R01 reference was not imported');
if (displayImport.results !== kept) failures.push('display import changed the result list');
if (!String(displayImport.message).includes('不是支持的单次验收结果')) failures.push('display import error: ' + displayImport.message);

if (!String(displayImport.message).includes('本批未导入任何记录')) failures.push('display import was not refused as a batch');
for (const [name, value] of [
  ['minimal_display', fixtures.minimal],
  ['synthetic_record', fixtures.record],
  ['ordinary_engineering', fixtures.engineering],
  ['ordinary_result', fixtures.ordinary],
  ['display_array', [fixtures.minimal]],
]) {
  const imported = await importResult(value, name + '.json');
  report.checks[name + '_results'] = imported.results;
  report.checks[name + '_error'] = imported.message;
  if (imported.results !== kept) failures.push(name + ' changed results');
  if (!String(imported.message).includes('本批未导入任何记录')) failures.push(name + ' was imported into results');
}

for (const [name, value, token] of [
  ['engineering', fixtures.engineering, 'engineering-1.0'],
  ['ordinary_result', fixtures.ordinary, 'schema_version 1.0'],
  ['recipe', fixtures.recipe, 'recipe-1.0'],
  ['website_true', fixtures.websiteTrue, 'website_import_supported'],
  ['website_omitted', fixtures.websiteOmitted, 'website_import_supported'],
  ['json_array', [fixtures.minimal], 'JSON 数组'],
]) {
  const result = probe(value);
  report.checks['synthetic_page_' + name] = result.ok ? 'accepted' : result.error;
  if (result.ok || !result.error.includes(token) || result.results !== kept) failures.push('synthetic page failed to reject ' + name);
}

for (const [name, value] of [['minimal', fixtures.minimal], ['generated_display', liveDisplay]]) {
  const result = probe(value);
  report.checks['synthetic_page_accepts_' + name] = result.ok;
  if (!result.ok || result.results !== kept) failures.push('synthetic page rejected a website_import_supported false display: ' + name + ' ' + (result.error || ''));
}

report.results_final = vm.runInContext('results.length', ctx);
if (report.results_final !== kept) failures.push('results length changed after synthetic validation');
report.verdict = failures.length ? 'still-fails' : 'blocks';
report.failures = failures;
console.log(JSON.stringify(report));
process.exit(failures.length ? 1 : 0);
