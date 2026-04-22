import { buildTestUser, expect, login, logout, signup, test } from "./fixtures";

test.describe("authentication flow", () => {
  test.skip(!process.env.E2E_FULL_STACK, "requires backend + Supabase");

  test("new user can signup and logout", async ({ page }) => {
    const user = buildTestUser("auth-signup");
    await signup(page, user);
    await expect(page).toHaveURL(/\/(calendar|drafts|home|$)/);
    await logout(page);
  });

  test("existing user can login", async ({ page }) => {
    const user = buildTestUser("auth-login");
    await signup(page, user);
    await logout(page);
    await login(page, user);
    await expect(page).not.toHaveURL(/\/login$/);
  });

  test("wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("メールアドレス").fill("nobody@test.local");
    await page.getByLabel("パスワード").fill("wrong-password");
    await page.getByRole("button", { name: /ログイン/ }).click();
    await expect(page.getByText(/認証|失敗|invalid/i)).toBeVisible();
  });
});
