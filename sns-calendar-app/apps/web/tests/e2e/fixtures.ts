import { test as base, expect, type Page } from "@playwright/test";

export type TestUser = {
  email: string;
  password: string;
  displayName: string;
};

export function buildTestUser(prefix = "e2e"): TestUser {
  const stamp = Date.now();
  return {
    email: `${prefix}-${stamp}@test.local`,
    password: "SecretPass!234",
    displayName: `${prefix}-${stamp}`,
  };
}

export async function signup(page: Page, user: TestUser): Promise<void> {
  await page.goto("/signup");
  await page.getByLabel("メールアドレス").fill(user.email);
  await page.getByLabel("パスワード").fill(user.password);
  const displayField = page.getByLabel("表示名", { exact: false });
  if (await displayField.count()) {
    await displayField.fill(user.displayName);
  }
  await page.getByRole("button", { name: /新規登録|登録/ }).click();
  await expect(page).not.toHaveURL(/\/signup$/);
}

export async function login(page: Page, user: TestUser): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("メールアドレス").fill(user.email);
  await page.getByLabel("パスワード").fill(user.password);
  await page.getByRole("button", { name: /ログイン/ }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

export async function logout(page: Page): Promise<void> {
  await page.getByRole("button", { name: "ログアウト" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

export async function mockExternalSnsApis(page: Page): Promise<void> {
  await page.route(/api\.x\.com|api\.twitter\.com/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { id: "mocked-x-post-id" } }),
    });
  });

  await page.route(/graph\.facebook\.com/, async (route) => {
    const url = route.request().url();
    if (url.includes("/media_publish")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "mocked-ig-post-id" }),
      });
      return;
    }
    if (url.includes("/media")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "mocked-ig-container-id" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "mocked-generic" }),
    });
  });
}

type Fixtures = {
  testUser: TestUser;
  authedPage: Page;
};

export const test = base.extend<Fixtures>({
  testUser: async ({}, use) => {
    await use(buildTestUser());
  },
  authedPage: async ({ page, testUser }, use) => {
    await mockExternalSnsApis(page);
    await signup(page, testUser);
    await use(page);
  },
});

export { expect };
