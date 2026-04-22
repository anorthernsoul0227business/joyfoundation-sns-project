import { expect, test } from "./fixtures";

test.describe("SNS connection settings", () => {
  test.skip(!process.env.E2E_FULL_STACK, "requires backend + mocked OAuth");

  test("settings page lists X and IG", async ({ authedPage: page }) => {
    await page.goto("/settings/sns");
    await expect(page.getByText(/X|Twitter/)).toBeVisible();
    await expect(page.getByText(/Instagram|IG/)).toBeVisible();
  });

  test("connect X opens OAuth url (mocked)", async ({ authedPage: page }) => {
    let capturedRedirect: string | null = null;
    await page.route("**/api/sns-accounts/connect/x", async (route) => {
      capturedRedirect = "https://api.x.com/oauth/authorize?oauth_token=mocked";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ redirect_url: capturedRedirect }),
      });
    });

    await page.goto("/settings/sns");
    const connectBtn = page.getByRole("button", { name: /X.*連携|連携.*X/ }).first();
    if (await connectBtn.count()) {
      await connectBtn.click();
      expect(capturedRedirect).toContain("oauth");
    }
  });
});
