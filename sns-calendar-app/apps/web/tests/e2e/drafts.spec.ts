import { expect, test } from "./fixtures";

test.describe("drafts management", () => {
  test.skip(!process.env.E2E_FULL_STACK, "requires backend + Supabase");

  test("create, search, and delete a draft", async ({ authedPage: page }) => {
    await page.goto("/create");
    const body = `draft body ${Date.now()}`;
    await page.getByLabel(/本文|投稿内容/).fill(body);
    await page.getByRole("button", { name: /下書き|保存/ }).click();

    await page.goto("/drafts");
    await expect(page.getByText(body)).toBeVisible();

    const searchInput = page.getByPlaceholder(/検索/);
    if (await searchInput.count()) {
      await searchInput.fill(body.slice(0, 8));
      await expect(page.getByText(body)).toBeVisible();
    }

    await page.getByRole("button", { name: /削除/ }).first().click();
    const confirm = page.getByRole("button", { name: /削除する|確定|OK/ });
    if (await confirm.count()) {
      await confirm.click();
    }
    await expect(page.getByText(body)).not.toBeVisible();
  });
});
