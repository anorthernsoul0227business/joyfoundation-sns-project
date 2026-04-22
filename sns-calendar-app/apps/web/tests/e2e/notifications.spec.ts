import { expect, test } from "./fixtures";

test.describe("notifications realtime", () => {
  test.skip(!process.env.E2E_FULL_STACK, "requires backend + Redis + Celery");

  test("notification page shows empty state initially", async ({ authedPage: page }) => {
    await page.goto("/notifications");
    await expect(page.getByText(/通知はまだありません|未読/)).toBeVisible();
  });

  test("bell badge increments on new notification", async ({ authedPage: page }) => {
    await page.goto("/calendar");
    const bell = page.getByRole("button", { name: "通知を開く" });
    await expect(bell).toBeVisible();

    await expect(async () => {
      const badge = bell.locator("span").filter({ hasText: /^\d+$/ }).first();
      await expect(badge).toBeVisible({ timeout: 60_000 });
    }).toPass({ timeout: 90_000 });
  });
});
