/**
 * 画像アップロード用の署名付きURLを発行する。
 *
 * ブラウザは、ここで受け取ったURLへ画像を直接 PUT する。Vercel を経由しないので
 * 関数の実行時間やリクエスト本文の上限（Hobby は 4.5MB）に縛られない。
 *
 * 認証: Supabase のアクセストークンを Authorization ヘッダで受け取り、
 * その人が指定の org に属しているかを確かめる。誰でも書ける状態にはしない。
 */
import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { buildImageKey, presignPut, publicUrlFor, readR2Config } from "../../../lib/r2";

export const runtime = "nodejs";

// 記事に添える写真の想定。これ以上はブラウザ側で縮小してから送る
const MAX_BYTES = 12 * 1024 * 1024;
const EXT: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

export async function POST(request: Request) {
  const cfg = readR2Config();
  if (!cfg) {
    return NextResponse.json(
      { error: "画像の保管先が設定されていません。管理者にお知らせください。" },
      { status: 503 },
    );
  }

  const token = (request.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!token) {
    return NextResponse.json({ error: "ログインし直してください。" }, { status: 401 });
  }

  let body: { orgId?: string; contentType?: string; size?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "リクエストを読めませんでした。" }, { status: 400 });
  }

  const { orgId, contentType, size } = body;
  const ext = contentType ? EXT[contentType] : undefined;
  if (!orgId || !ext) {
    return NextResponse.json(
      { error: "JPEG・PNG・WebP の画像を選んでください。" },
      { status: 400 },
    );
  }
  if (typeof size === "number" && size > MAX_BYTES) {
    return NextResponse.json({ error: "画像が大きすぎます。" }, { status: 400 });
  }

  // 利用者のトークンで問い合わせる。RLS が働くので、所属しない org は見えない
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
    { global: { headers: { Authorization: `Bearer ${token}` } }, auth: { persistSession: false } },
  );
  const { data: user } = await supabase.auth.getUser();
  if (!user?.user) {
    return NextResponse.json({ error: "ログインし直してください。" }, { status: 401 });
  }
  // 組織には複数人いるので、自分の行に絞る。
  // org_id だけで絞ると2行返り maybeSingle() が失敗する（2026-09-04）
  const { data: member, error } = await supabase
    .from("org_members")
    .select("org_id")
    .eq("org_id", orgId)
    .eq("user_id", user.user.id)
    .maybeSingle();
  if (error || !member) {
    return NextResponse.json({ error: "この組織には投稿できません。" }, { status: 403 });
  }

  const key = buildImageKey(orgId, ext);
  return NextResponse.json({
    uploadUrl: presignPut(cfg, key, contentType!),
    storagePath: key,
    publicUrl: publicUrlFor(cfg, key),
    contentType,
  });
}
