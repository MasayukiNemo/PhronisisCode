import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, "char_counter.html"), "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) {
  console.error("script block not found");
  process.exit(1);
}

function makeEl() {
  return {
    value: "",
    textContent: "",
    _handlers: {},
    addEventListener(type, fn) {
      this._handlers[type] = fn;
    },
  };
}
const ids = ["text", "c-total", "c-nonewline", "c-lines", "c-nospace", "c-full", "c-half"];
const els = {};
for (const id of ids) els[id] = makeEl();

const sandbox = {
  document: { getElementById: (id) => els[id] || null },
  requestAnimationFrame: (fn) => fn(),
  console,
};
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox);

const textEl = els["text"];
function setText(v) {
  textEl.value = v;
  textEl._handlers.input();
}
function num(id) {
  return Number(els[id].textContent.replace(/,/g, ""));
}
function out() {
  return {
    total: num("c-total"),
    noNewline: num("c-nonewline"),
    lines: num("c-lines"),
    noSpace: num("c-nospace"),
    full: num("c-full"),
    half: num("c-half"),
  };
}

const cases = [
  ["", { total: 0, noNewline: 0, lines: 0, noSpace: 0, full: 0, half: 0 }],
  ["abc", { total: 3, noNewline: 3, lines: 1, noSpace: 3, full: 0, half: 3 }],
  ["あいう", { total: 3, noNewline: 3, lines: 1, noSpace: 3, full: 3, half: 0 }],
  ["abあ", { total: 3, noNewline: 3, lines: 1, noSpace: 3, full: 1, half: 2 }],
  ["a\nb", { total: 3, noNewline: 2, lines: 2, noSpace: 2, full: 0, half: 3 }],
  ["a\n", { total: 2, noNewline: 1, lines: 2, noSpace: 1, full: 0, half: 2 }],
  ["a\r\nb", { total: 4, noNewline: 2, lines: 2, noSpace: 2, full: 0, half: 4 }],
  [" \u3000\t", { total: 3, noNewline: 3, lines: 1, noSpace: 0, full: 1, half: 2 }],
  ["\u{1F600}", { total: 1, noNewline: 1, lines: 1, noSpace: 1, full: 1, half: 0 }],
  ["\uFF21\uFF11", { total: 2, noNewline: 2, lines: 1, noSpace: 2, full: 2, half: 0 }],
  ["\uFF71", { total: 1, noNewline: 1, lines: 1, noSpace: 1, full: 0, half: 1 }],
  ["漢字とカナとABC", { total: 9, noNewline: 9, lines: 1, noSpace: 9, full: 6, half: 3 }],
];

let failed = 0;
for (const [input, expected] of cases) {
  setText(input);
  const got = out();
  const keys = Object.keys(expected);
  const eq = keys.every((k) => got[k] === expected[k]);
  const sum = got.full + got.half === got.total;
  if (!eq || !sum) {
    failed++;
    console.error(`FAIL ${JSON.stringify(input)}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(got)}\n  full+half==total: ${sum}`);
  } else {
    console.log(`ok   ${JSON.stringify(input)} -> ${JSON.stringify(got)}`);
  }
}

console.log(failed === 0 ? `\nALL PASS (${cases.length} cases, equality held)` : `\n${failed} FAILED`);
process.exit(failed === 0 ? 0 : 1);
