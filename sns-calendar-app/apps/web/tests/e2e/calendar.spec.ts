import { expect, test } from "./fixtures";

test.describe("calendar view & drag & drop", () => {
  test.skip(!process.env.E2E_FULL_STACK, "requires backend + Supabase");

  test("calendar renders", async ({ authedPage: page }) => {
    await page.goto("/calendar");
    await expect(page.locator(".fc")).toBeVisible();
  });

  test("draft can be dragged onto a day cell", async ({ authedPage: page }) => {
    await page.goto("/create");
    const body = `dnd body ${Date.now()}`;
    await page.getByLabel(/本文|投稿内容/).fill(body);
    await page.getByRole("button", { name: /下書き|保存/ }).click();

    await page.goto("/calendar");

    const draftCard = page.locator("[data-draft-id]").filter({ hasText: body }).first();
    await expect(draftCard).toBeVisible();

    const dayCell = page.locator(".fc-daygrid-day").first();
    await draftCard.dragTo(dayCell);

    await expect(page.getByText(body)).toBeVisible();
  });
});
