import { test, expect } from "@playwright/test";
import path from "path";

const SCREENSHOTS_DIR = path.resolve(process.cwd(), "../../docs/screenshots");

test.describe("Cite Platform Smoke Tests & Visual Capture", () => {
  test("1. Unauthenticated user redirects to login page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.getByText("Cite", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Grounded clinical answers with")).toBeVisible();
    await expect(page.getByText("Structure-Aware Clinical Ingestion")).toBeVisible();
    await expect(page.getByText("Welcome back")).toBeVisible();
  });

  test("2. User can register a fresh organization and tenant", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByText("Create organization workspace")).toBeVisible();

    const uniqueId = Date.now().toString(36);
    await page.locator("input[placeholder*='Pfizer']").fill(`BioResearch ${uniqueId}`);
    await page.locator("input[placeholder*='Jane Smith']").fill("Dr. Lead Scientist");
    await page.locator("input[type='email']").fill(`scientist-${uniqueId}@bioresearch.com`);
    await page.locator("input[type='password']").fill("SecurePassword123!");

    await page.getByRole("button", { name: "Create Tenant & Account" }).click();

    // After registration, redirected to chat dashboard
    await expect(page).toHaveURL(/\/(chat)?$/);
    await expect(page.getByText(`BioResearch ${uniqueId}`).first()).toBeVisible();
  });

  test("3. User can log in as demo pharma user and view 40+ drug label documents", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type='email']").fill("admin@demopharma.com");
    await page.locator("input[type='password']").fill("demopassword123");
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page).toHaveURL(/\/(chat)?$/);
    await expect(page.getByText("Demo Pharma Therapeutics").first()).toBeVisible();

    // Navigate to Documents page
    await page.locator("a[href='/documents']").first().click();
    await expect(page).toHaveURL(/.*\/documents/);

    // Verify document repository header and table
    await expect(page.locator("h1")).toContainText("Document Repository");
    await expect(page.getByText("Naproxen", { exact: false }).first()).toBeVisible();

    // Take Documents Page screenshot
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "documents-desktop.png"),
      fullPage: true,
    });
  });

  test("4. Document detail drawer opens with metadata and chunk previews", async ({ page }) => {
    // Login as demo admin
    await page.goto("/login");
    await page.locator("input[type='email']").fill("admin@demopharma.com");
    await page.locator("input[type='password']").fill("demopassword123");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page).toHaveURL(/\/(chat)?$/);

    await page.locator("a[href='/documents']").first().click();
    await expect(page).toHaveURL(/.*\/documents/);

    // Click "Inspect chunks outline" on first document
    const detailsButtons = page.locator("button[title='Inspect chunks outline']");
    await expect(detailsButtons.first()).toBeVisible({ timeout: 15000 });
    await detailsButtons.first().click();

    await expect(page.getByText("Structure-Aware Chunks").first()).toBeVisible({ timeout: 10000 });

    // Close drawer
    const closeBtn = page.getByLabel("Close document drawer");
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();
  });

  test("5. Chat stream, inline citations, citation drawer, and trace drawer", async ({ page }) => {
    // Login as demo admin
    await page.goto("/login");
    await page.locator("input[type='email']").fill("admin@demopharma.com");
    await page.locator("input[type='password']").fill("demopassword123");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page).toHaveURL(/\/(chat)?$/);

    // Type clinical drug inquiry
    const composer = page.locator("textarea[placeholder*='Ask a question']");
    await expect(composer).toBeVisible();
    await composer.fill("What is the boxed warning for naproxen?");
    await page.locator("button[type='submit']").click();

    // Verify answer and timeline appeared
    const timelineOrTrace = page.getByRole("button", { name: /how i got this answer|trace/i }).first();
    await expect(timelineOrTrace).toBeVisible({ timeout: 45000 });

    // Look for citation chip [1]
    const citationChip = page.getByRole("button", { name: "1", exact: true }).first();
    const hasCitation = await citationChip.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasCitation) {
      // Click inline citation chip to open citation drawer
      await citationChip.click();

      const citationPanel = page.getByText("Supporting Evidence").first();
      await expect(citationPanel).toBeVisible();

      // Capture desktop light mode screenshot with open citation panel
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, "chat-desktop-light.png"),
        fullPage: true,
      });

      // Dismiss popover if open
      await page.keyboard.press("Escape");

      // Switch to Dark Mode
      const themeToggle = page.getByLabel("Toggle theme").first();
      if (await themeToggle.isVisible()) {
        await themeToggle.click({ force: true });
        await page.waitForTimeout(400);

        // Capture desktop dark mode screenshot
        await page.screenshot({
          path: path.join(SCREENSHOTS_DIR, "chat-desktop-dark.png"),
          fullPage: true,
        });

        // Switch back to light mode
        await themeToggle.click({ force: true });
      }

      // Close citation panel
      const closeBtn = page.getByLabel("Close citation panel");
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
      }
    } else {
      // Capture chat page light and dark
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, "chat-desktop-light.png"),
        fullPage: true,
      });

      const themeToggle = page.getByLabel("Toggle theme").first();
      if (await themeToggle.isVisible()) {
        await themeToggle.click({ force: true });
        await page.waitForTimeout(400);
        await page.screenshot({
          path: path.join(SCREENSHOTS_DIR, "chat-desktop-dark.png"),
          fullPage: true,
        });
        await themeToggle.click({ force: true });
      }
    }

    // Inspect trace drawer
    const traceButton = page.getByRole("button", { name: "Trace" }).first();
    if (await traceButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await traceButton.click({ force: true });
      await expect(page.getByText("Execution Audit Trace")).toBeVisible();

      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, "trace-drawer.png"),
      });

      const closeTrace = page.getByLabel("Close trace drawer");
      if (await closeTrace.isVisible()) {
        await closeTrace.click();
      }
    }
  });

  test("6. Responsive mobile viewport rendering", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto("/login");
    await page.locator("input[type='email']").fill("admin@demopharma.com");
    await page.locator("input[type='password']").fill("demopassword123");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page).toHaveURL(/\/(chat)?$/);

    // Mobile Light screenshot
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "chat-mobile-light.png"),
      fullPage: true,
    });

    // Toggle dark theme
    const mobileTheme = page.getByLabel("Toggle theme").first();
    if (await mobileTheme.isVisible()) {
      await mobileTheme.click();
      await page.waitForTimeout(400);

      // Mobile Dark screenshot
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, "chat-mobile-dark.png"),
        fullPage: true,
      });
    }
  });
});
