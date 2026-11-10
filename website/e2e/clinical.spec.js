import { expect, test } from "@playwright/test";

const PASSWORD = "Verify123!";

let counter = 0;
// Unique address per run: registration writes to the real Postgres user table.
const uniqueEmail = () => `e2e.${Date.now()}.${counter++}@example.com`;

async function registerPatient(page) {
  const email = uniqueEmail();
  await page.goto("/register");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: /^patient$/i }).click();
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByText(/Welcome, e2e\./)).toBeVisible();
  return email;
}

// Assertions use case-insensitive regexes because several labels are rendered
// through CSS `uppercase`, so innerText differs from the source string.

test("login page offers both clinical portals", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText(/Corvus CKD Risk Platform/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Sign In to Clinical Console/i })).toBeVisible();
  await page.getByRole("button", { name: /Patient Portal/i }).click();
  await expect(page.getByRole("button", { name: /Sign In to Patient Portal/i })).toBeVisible();
});

test("wrong credentials are rejected", async ({ page }) => {
  await page.goto("/login");
  await page.locator("#email").fill("nobody@example.com");
  await page.locator("#password").fill("definitely-not-the-password");
  await page.getByRole("button", { name: /Sign In to Clinical Console/i }).click();
  await expect(page.getByText(/Invalid credentials for the selected portal/i)).toBeVisible();
});

test("registering a patient opens the assessment dashboard", async ({ page }) => {
  await registerPatient(page);
  await expect(page.getByText(/NHANES Assessment/i)).toBeVisible();
  await expect(page.getByText(/CKD Risk Assessment Form/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Run \/v2\/predict/i })).toBeVisible();
});

test("a prediction is version-stamped and appears in history", async ({ page }) => {
  const email = await registerPatient(page);

  await page.locator("#RIDAGEYR").fill("58");
  await page.locator("#RIAGENDR").selectOption("1");
  await page.locator("#BMXBMI").fill("27.4");
  await page.getByRole("button", { name: /Run \/v2\/predict/i }).click();

  // Result card renders only after /v2/predict answers.
  await expect(page.getByText("model_version: 15")).toBeVisible({ timeout: 30000 });
  await expect(page.getByText(/Decision cutoff/i)).toBeVisible();

  await page.goto("/history");
  await expect(page.getByRole("heading", { name: /Model Runs/i })).toBeVisible();
  await expect(page.getByText(`Model runs for ${email}`)).toBeVisible();
  await expect(page.getByText(/^v15$/).first()).toBeVisible();
});

test("models page reports the pinned serving version", async ({ page }) => {
  await registerPatient(page);
  await page.goto("/models");
  await expect(page.getByText(/Registered model/i).first()).toBeVisible();
  await expect(page.getByText(/corvus-ckd/i).first()).toBeVisible();
  await expect(page.getByText(/^online$/i)).toBeVisible({ timeout: 20000 });
});
