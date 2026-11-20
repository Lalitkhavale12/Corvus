// Design audit for the parts of a UI that don't need eyes: contrast, type
// sizes, tap targets, overflow and off-palette colours. Run after a change:
//
//   node e2e/audit.mjs                     (vite on :5173)
//   BASE_URL=http://localhost:3000 node e2e/audit.mjs
//
// Exit code is 1 when a hard failure is found, so it can gate a build.
import { chromium } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:5173";
const PATIENT = { email: "verifier@example.com", password: "Verify123!" };
const DOCTOR = { email: "clinician@corvus-demo.com", password: "Clinic123!" };
const ROUTES = {
  public: ["/login", "/register"],
  patient: ["/dashboard", "/history", "/models", "/profile"],
  doctor: ["/doctor-dashboard", "/patients/mrn-84920", "/assign-patients", "/doctor-profile", "/models/model-comparison"],
};
const VIEWPORTS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } };

// Runs in the page. Inlines the WCAG maths so no dependency is needed.
const AUDIT = () => {
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const [r, g, b, a = 1] = m[1].split(/[,/]/).map((v) => parseFloat(v));
    return { r, g, b, a };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const blend = (top, bottom) => {
    const a = top.a;
    return {
      r: top.r * a + bottom.r * (1 - a),
      g: top.g * a + bottom.g * (1 - a),
      b: top.b * a + bottom.b * (1 - a),
      a: 1,
    };
  };
  const ratio = (a, b) => {
    const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  const bgOf = (el) => {
    let node = el;
    let acc = null;
    while (node) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) {
        acc = acc ? blend(acc, c) : c;
        if (c.a === 1) return acc;
      }
      node = node.parentElement;
    }
    return acc || { r: 255, g: 255, b: 255, a: 1 };
  };

  const contrast = [];
  const tiny = [];
  const targets = [];
  const colors = new Set();

  for (const el of document.querySelectorAll("body *")) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || el.closest("[aria-hidden='true']")) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    colors.add(cs.color);

    const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (hasText) {
      const size = parseFloat(cs.fontSize);
      const weight = parseInt(cs.fontWeight, 10) || 400;
      const large = size >= 24 || (size >= 18.66 && weight >= 700);
      const fgRaw = parse(cs.color);
      const bg = bgOf(el);
      const fg = fgRaw.a < 1 ? blend(fgRaw, bg) : fgRaw;
      const r = ratio(fg, bg);
      const need = large ? 3 : 4.5;
      if (r < need) {
        contrast.push({
          text: el.textContent.trim().slice(0, 40),
          cls: (el.className || "").toString().slice(0, 70),
          size,
          ratio: +r.toFixed(2),
          need,
        });
      }
      if (size < 12) tiny.push({ size, text: el.textContent.trim().slice(0, 30), cls: (el.className || "").toString().slice(0, 60) });
    }

    if (el.matches("button, a[href], input, select, textarea, [role='button']")) {
      const label = (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 24) || el.tagName;
      // Inline links inside a sentence and visually-hidden inputs are exempt
      // from WCAG 2.5.8 / are not real tap targets.
      const inline = el.tagName === "A" && (el.parentElement?.tagName === "P" || el.parentElement?.tagName === "LI");
      if (rect.height <= 1 || rect.width <= 1 || inline) continue;
      if (rect.height < 32 || rect.width < 24) targets.push({ label, w: Math.round(rect.width), h: Math.round(rect.height) });
    }
  }

  return {
    contrast: contrast.slice(0, 12),
    contrastCount: contrast.length,
    tiny: tiny.slice(0, 8),
    tinyCount: tiny.length,
    targets: targets.slice(0, 8),
    targetCount: targets.length,
    palette: [...colors],
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
  };
};

async function signIn(page, { email, password }) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 });
}

const browser = await chromium.launch();
let hard = 0;

for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
  console.log(`\n########## ${vpName} ${viewport.width}x${viewport.height} ##########`);
  const sessions = [
    ["public", null],
    ["patient", PATIENT],
    ["doctor", DOCTOR],
  ];
  for (const [tag, creds] of sessions) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    if (creds) await signIn(page, creds);
    for (const route of ROUTES[tag]) {
      await page.goto(BASE + route, { waitUntil: "networkidle" });
      await page.waitForTimeout(250);
      const r = await page.evaluate(AUDIT);
      const overflow = r.scrollW > r.clientW + 1;
      const flag = r.contrastCount || r.tinyCount || overflow;
      if (flag) hard += 1;
      console.log(
        `${route.padEnd(26)} contrast<AA=${String(r.contrastCount).padEnd(3)} text<12px=${String(r.tinyCount).padEnd(3)} smallTargets=${String(r.targetCount).padEnd(3)} ${overflow ? `OVERFLOW ${r.scrollW}>${r.clientW}` : ""}`,
      );
      for (const c of r.contrast) console.log(`   contrast ${c.ratio} < ${c.need}  ${c.size}px  "${c.text}"  ${c.cls}`);
      for (const t of r.tiny.slice(0, 4)) console.log(`   tiny ${t.size}px "${t.text}"  ${t.cls}`);
      for (const t of r.targets.slice(0, 4)) console.log(`   target ${t.w}x${t.h} "${t.label}"`);
    }
    await ctx.close();
  }
}

await browser.close();
console.log(`\n${hard === 0 ? "PASS: no contrast/overflow/type failures" : `FAIL: ${hard} route-viewport combos flagged`}`);
process.exit(hard === 0 ? 0 : 1);
