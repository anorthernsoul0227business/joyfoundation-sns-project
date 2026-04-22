import { buildTestUser, expect, mockExternalSnsApis, signup, test } from "./fixtures";

test.describe("core publish flow", () => {
  test.skip(!process.env.E2E_FULL_STACK, "requires backend + Celery + Supabase");

  test("signup → create post → schedule → publish → notification", async ({ page }) => {
    const user = buildTestUser("core");
    await mockExternalSnsApis(page);
    await signup(page, user);

    await page.goto("/create");
    await page.getByLabel(/本文|投稿内容/).fill("E2E test post body");

    const xCheckbox = page.getByLabel("X", { exact: true });
    if (await xCheckbox.count()) {
      await xCheckbox.check();
    }

    const scheduleInput = page.getByLabel(/予約|scheduled/i);
    if (await scheduleInput.count()) {
      const soon = new Date(Date.now() + 10_000);
      await scheduleInput.fill(soon.toISOString().slice(0, 16));
    }

    await page.getByRole("button", { name: /予約|投稿/ }).click();

    await expect(page.getByText(/投稿成功|post_published/)).toBeVisible({
      timeout: 90_000,
    });

    await page.goto("/notifications");
    await expect(page.getByText(/投稿成功/)).toBeVisible();
  });
});
