// Visual capture helper for UI work. Not a test: the Playwright runner only
// collects *.spec.js, so this file is bookkeeping-free.
//
//   node e2e/capture.mjs                 -> shots before_*.png  (vite on :5173)
//   SHOT_LABEL=after node e2e/capture.mjs
//   VIEWPORTS=desktop node e2e/capture.mjs
//   BASE_URL=http://localhost:3000 node e2e/capture.mjs
//
// Prints per-route horizontal overflow and console errors so a "looks fine"
// screenshot cannot hide a broken layout.
import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://localhost:5173";
const LABEL = process.env.SHOT_LABEL || "before";
const OUT = path.resolve("shots");
const ALL_VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
};
const wanted = (process.env.VIEWPORTS || "desktop,mobile").split(",").map((s) => s.trim());
const viewports = wanted.map((name) => [name, ALL_VIEWPORTS[name]]);

const PATIENT = { email: "verifier@example.com", password: "Verify123!" };
const DOCTOR = { email: "clinician@corvus-demo.com", password: "Clinic123!" };

const PUBLIC = ["/login", "/register"];
const PATIENT_PAGES = ["/dashboard", "/history", "/models", "/profile"];
const DOCTOR_PAGES = [
  "/doctor-dashboard",
  "/patients/mrn-84920",
  "/assign-patients",
  "/doctor-profile",
  "/models/model-comparison",
];

async function signIn(page, { email, password }) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20000 });
  await page.waitForLoadState("networkidle");
}

async function shoot(page, routes, tag) {
  for (const route of routes) {
    const errors = [];
    const onConsole = (m) => m.type() === "error" && errors.push(m.text());
    page.on("console", onConsole);
    await page.goto(BASE + route, { waitUntil: "networkidle" });
    await page.waitForTimeout(350);
    const file = path.join(OUT, `${LABEL}_${tag}${route.replaceAll("/", "_")}.png`);
    await page.screenshot({ path: file, fullPage: true });
    const { scrollW, clientW, h } = await page.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
      h: document.documentElement.scrollHeight,
    }));
    const overflow = scrollW > clientW + 1 ? `OVERFLOW ${scrollW}>${clientW}` : "ok";
    console.log(`${route.padEnd(28)} ${overflow.padEnd(18)} height=${h}  console=${errors.length}`);
    for (const e of errors.slice(0, 3)) console.log(`    ! ${e.slice(0, 160)}`);
    page.off("console", onConsole);
  }
}

await fs.mkdir(OUT, { recursive: true });
const browser = await chromium.launch();

for (const [name, viewport] of viewports) {
  console.log(`\n=== ${name} ${viewport.width}x${viewport.height} ===`);

  const anon = await browser.newContext({ viewport });
  await shoot(await anon.newPage(), PUBLIC, `${name}_public`);
  await anon.close();

  const patientCtx = await browser.newContext({ viewport });
  const patientPage = await patientCtx.newPage();
  await signIn(patientPage, PATIENT);
  await shoot(patientPage, PATIENT_PAGES, `${name}_patient`);
  await patientCtx.close();

  const doctorCtx = await browser.newContext({ viewport });
  const doctorPage = await doctorCtx.newPage();
  await signIn(doctorPage, DOCTOR);
  await shoot(doctorPage, DOCTOR_PAGES, `${name}_doctor`);
  await doctorCtx.close();
}

await browser.close();
console.log(`\nshots written to ${OUT}`);
