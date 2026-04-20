"use client";

import {
  createPostApiPostsPost,
  deletePostApiPostsPostIdDelete,
  getCalendarApiCalendarGet,
  getPostApiPostsPostIdGet,
  listPostsApiPostsGet,
  loginApiAuthLoginPost,
  logoutApiAuthLogoutPost,
  meApiAuthMeGet,
  publishNowApiPostsPostIdPublishNowPost,
  refreshApiAuthRefreshPost,
  schedulePostApiPostsPostIdSchedulePost,
  signupApiAuthSignupPost,
  updatePostApiPostsPostIdPatch,
} from "../generated/sdk.gen";
import type {
  CalendarResponse,
  PostCreate,
  PostListResponse,
  PostResponse,
  PostUpdate,
  SessionResponse,
  UserResponse,
} from "../generated/types.gen";
import { client } from "../generated/client.gen";
import type { AuthSession, AuthUser } from "../stores/auth";
import { useAuthStore } from "../stores/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

client.setConfig({
  baseUrl: API_BASE_URL,
});

client.interceptors.request.use((request) => {
  const token = useAuthStore.getState().session?.accessToken;
  if (token) {
    request.headers.set("Authorization", `Bearer ${token}`);
  }

  return request;
});

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let refreshPromise: Promise<boolean> | null = null;

type ClientResult<TData, TError = unknown> =
  | {
      data: TData;
      error: undefined;
      request: Request;
      response: Response;
    }
  | {
      data: undefined;
      error: TError;
      request: Request;
      response: Response;
    };

function normalizeUser(user: UserResponse): AuthUser {
  return {
    id: user.id,
    email: user.email,
    displayName: user.display_name ?? null,
    uiMode: user.ui_mode === "pro" ? "pro" : "simple",
    helpModeEnabled: user.help_mode_enabled ?? true,
    defaultOrgId: user.default_org_id ?? null,
  };
}

function normalizeSession(response: SessionResponse): {
  session: AuthSession;
  user: AuthUser;
} {
  return {
    session: {
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      expiresAt: Math.floor(Date.now() / 1000) + response.expires_in,
    },
    user: normalizeUser(response.user),
  };
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return fallback;
  }

  try {
    const payload = (await response.clone().json()) as
      | { detail?: string | Array<{ msg?: string }> }
      | undefined;

    if (typeof payload?.detail === "string") {
      return payload.detail;
    }

    if (Array.isArray(payload?.detail)) {
      return payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
    }
  } catch {
    return fallback;
  }

  return fallback;
}

async function unwrapResult<TData, TError>(result: ClientResult<TData, TError>): Promise<TData> {
  if (result.data !== undefined) {
    return result.data;
  }

  const fallback = result.response.status === 401 ? "認証に失敗しました。" : "リクエストに失敗しました。";
  throw new ApiError(await readErrorMessage(result.response, fallback), result.response.status);
}

async function refreshSession(): Promise<boolean> {
  const refreshToken = useAuthStore.getState().session?.refreshToken;
  if (!refreshToken) {
    useAuthStore.getState().clear();
    return false;
  }

  if (!refreshPromise) {
    refreshPromise = (async () => {
      const result = await refreshApiAuthRefreshPost({
        body: { refresh_token: refreshToken },
      });

      if ("data" in result && result.data) {
        const normalized = normalizeSession(result.data);
        useAuthStore.getState().setSession(normalized.user, normalized.session);
        return true;
      }

      useAuthStore.getState().clear();
      return false;
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function withAuthRetry<TData, TError>(
  request: () => Promise<ClientResult<TData, TError>>,
): Promise<TData> {
  const result = await request();
  if (result.data !== undefined) {
    return result.data;
  }

  if (result.response.status === 401 && (await refreshSession())) {
    const retried = await request();
    return unwrapResult(retried);
  }

  if (result.response.status === 401) {
    useAuthStore.getState().clear();
  }

  return unwrapResult(result);
}

export async function login(values: { email: string; password: string }) {
  const response = await unwrapResult(
    (await loginApiAuthLoginPost({
      body: values,
    })) as ClientResult<SessionResponse>,
  );

  const normalized = normalizeSession(response);
  useAuthStore.getState().setSession(normalized.user, normalized.session);
  return normalized;
}

export async function signup(values: {
  display_name?: string;
  email: string;
  password: string;
}) {
  const response = await unwrapResult(
    (await signupApiAuthSignupPost({
      body: values,
    })) as ClientResult<SessionResponse>,
  );

  const normalized = normalizeSession(response);
  useAuthStore.getState().setSession(normalized.user, normalized.session);
  return normalized;
}

export async function fetchCurrentUser() {
  const user = await withAuthRetry(() => meApiAuthMeGet() as Promise<ClientResult<UserResponse>>);
  const normalized = normalizeUser(user);
  useAuthStore.getState().setUser(normalized);
  return normalized;
}

export async function fetchCalendarEvents(query: {
  from: string;
  to: string;
  platforms?: Array<"x" | "ig" | "note" | "youtube" | "line">;
}) {
  return withAuthRetry(
    () =>
      getCalendarApiCalendarGet({
        query,
      }) as Promise<ClientResult<CalendarResponse>>,
  );
}

export async function fetchPostList(params?: {
  status?: "draft" | "scheduled" | "publishing" | "published" | "failed" | "archived";
  platform?: "x" | "ig" | "note" | "youtube" | "line";
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}) {
  return withAuthRetry(
    () =>
      listPostsApiPostsGet({
        query: params,
      }) as Promise<ClientResult<PostListResponse>>,
  );
}

export async function fetchPostDetail(postId: string) {
  return withAuthRetry(
    () =>
      getPostApiPostsPostIdGet({
        path: {
          post_id: postId,
        },
      }) as Promise<ClientResult<PostResponse>>,
  );
}

export async function createPost(values: PostCreate) {
  return withAuthRetry(
    () =>
      createPostApiPostsPost({
        body: values,
      }) as Promise<ClientResult<PostResponse>>,
  );
}

export async function updatePost(postId: string, values: PostUpdate) {
  return withAuthRetry(
    () =>
      updatePostApiPostsPostIdPatch({
        body: values,
        path: {
          post_id: postId,
        },
      }) as Promise<ClientResult<PostResponse>>,
  );
}

export async function schedulePost(postId: string, scheduledAt: string) {
  return withAuthRetry(
    () =>
      schedulePostApiPostsPostIdSchedulePost({
        body: {
          scheduled_at: scheduledAt,
        },
        path: {
          post_id: postId,
        },
      }) as Promise<ClientResult<PostResponse>>,
  );
}

export async function publishPostNow(postId: string) {
  return withAuthRetry(
    () =>
      publishNowApiPostsPostIdPublishNowPost({
        path: {
          post_id: postId,
        },
      }) as Promise<ClientResult<PostResponse>>,
  );
}

export async function deletePost(postId: string) {
  return withAuthRetry(
    () =>
      deletePostApiPostsPostIdDelete({
        path: { post_id: postId },
      }) as Promise<ClientResult<unknown>>,
  );
}

export async function logout() {
  try {
    await withAuthRetry(() => logoutApiAuthLogoutPost() as Promise<ClientResult<unknown>>);
  } finally {
    useAuthStore.getState().clear();
  }
}
