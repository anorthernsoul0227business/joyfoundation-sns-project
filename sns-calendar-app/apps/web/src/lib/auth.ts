"use client";

/**
 * Supabase Auth を直接使うログイン処理。
 *
 * FastAPI の /api/auth/* を置き換える。既存画面（AppHeader / useAuthGuard）は
 * useAuthStore の session / user だけを見ているので、同じ形で store に入れれば
 * そのまま動く。
 */
import type { Session } from "@supabase/supabase-js";
import { requireSupabaseClient } from "./supabase";
import { useAuthStore, type AuthSession, type AuthUser } from "../stores/auth";

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

function toAuthSession(session: Session): AuthSession {
  return {
    accessToken: session.access_token,
    refreshToken: session.refresh_token,
    // expires_at は秒。無い場合は expires_in から起こす
    expiresAt: session.expires_at ?? Math.floor(Date.now() / 1000) + session.expires_in,
  };
}

/** public.users のプロファイルを AuthUser に写す。無ければ auth 情報だけで組む */
async function loadProfile(session: Session): Promise<AuthUser> {
  const supabase = requireSupabaseClient();
  const { data } = await supabase
    .from("users")
    .select("id, email, display_name, ui_mode, help_mode_enabled, default_org_id")
    .eq("id", session.user.id)
    .maybeSingle();

  return {
    id: session.user.id,
    email: data?.email ?? session.user.email ?? "",
    displayName: data?.display_name ?? null,
    uiMode: data?.ui_mode === "pro" ? "pro" : "simple",
    helpModeEnabled: data?.help_mode_enabled ?? true,
    defaultOrgId: data?.default_org_id ?? null,
  };
}

function describeSignInError(message: string): string {
  // Supabase のエラー文は英語なので、圭一郎さんに見せる言葉に直す
  if (/invalid login credentials/i.test(message)) {
    return "メールアドレスかパスワードが違います。";
  }
  if (/email not confirmed/i.test(message)) {
    return "メールアドレスの確認が済んでいません。届いたメールのリンクを開いてください。";
  }
  if (/rate limit/i.test(message)) {
    return "しばらく時間をおいてから、もう一度お試しください。";
  }
  return "ログインに失敗しました。時間をおいて再度お試しください。";
}

export async function signIn(values: { email: string; password: string }): Promise<AuthUser> {
  const supabase = requireSupabaseClient();
  const { data, error } = await supabase.auth.signInWithPassword(values);
  if (error || !data.session) {
    throw new AuthError(describeSignInError(error?.message ?? ""));
  }
  const user = await loadProfile(data.session);
  useAuthStore.getState().setSession(user, toAuthSession(data.session));
  return user;
}

export async function signOut(): Promise<void> {
  const supabase = requireSupabaseClient();
  await supabase.auth.signOut();
  useAuthStore.getState().clear();
}

/**
 * ブラウザに残っている Supabase セッションを store に写す。
 * store とは別に supabase-js もセッションを持つため、起動時に揃えておく。
 * 返り値は「有効なセッションがあるか」。
 */
export async function syncSessionFromSupabase(): Promise<boolean> {
  const supabase = requireSupabaseClient();
  const { data } = await supabase.auth.getSession();
  if (!data.session) {
    useAuthStore.getState().clear();
    return false;
  }
  const store = useAuthStore.getState();
  if (!store.user || store.user.id !== data.session.user.id) {
    const user = await loadProfile(data.session);
    store.setSession(user, toAuthSession(data.session));
  } else {
    store.setSession(store.user, toAuthSession(data.session));
  }
  return true;
}
