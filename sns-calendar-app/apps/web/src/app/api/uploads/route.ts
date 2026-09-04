/**
 * 記事に添える画像を受け取り、Cloudflare R2 に保存する。
 *
 * 2026-09-04: はじめ「署名付きURLを返し、ブラウザから R2 へ直接 PUT」で作ったが、
 * ブラウザからの直接 PUT には R2 側の CORS 設定が要り、いまの R2 トークンには
 * その権限が無かった（PutBucketCors が AccessDenied）。
 * ダッシュボード設定を人にお願いしないと動かない作りは避けたいので、
 * この経路（同一オリジン）で中継する方式に変えた。CORS は関係しなくなる。
 *
 * 画像はブラウザ側で長辺1600pxに縮めてから送られる（数百KB程度）。
 * Vercel の本文上限 4.5MB には十分収まる。
 */
import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { buildImageKey, presignPut, publicUrlFor, readR2Config } from "../../../lib/r2";

export const runtime = "nodejs";

// ブラウザ側で縮めた後の想定は数百KB。桁違いに大きいものは受け取らない
const MAX_BYTES = 4 * 1024 * 1024;
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

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    // 2026-09-04: 画面を開いたままにしていると、古い版（JSONを送る作り）が
    // 動き続けて解析に失敗する。原因が分かる案内にする
    const ct = request.headers.get("content-type") ?? "";
    if (ct.includes("application/json")) {
      return NextResponse.json(
        { error: "画面が古いままです。ページを再読み込みしてから、もう一度お試しください。" },
        { status: 409 },
      );
    }
    return NextResponse.json({ error: "画像を読めませんでした。" }, { status: 400 });
  }

  const orgId = String(form.get("orgId") ?? "");
  const file = form.get("file");
  if (!orgId || !(file instanceof File)) {
    return NextResponse.json({ error: "画像が添えられていません。" }, { status: 400 });
  }
  const ext = EXT[file.type];
  if (!ext) {
    return NextResponse.json(
      { error: "JPEG・PNG・WebP の画像を選んでください。" },
      { status: 400 },
    );
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "画像が大きすぎます。" }, { status: 400 });
  }

  // 利用者のトークンで問い合わせる。RLS が働くので所属しない org は見えない
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
    { global: { headers: { Authorization: `Bearer ${token}` } }, auth: { persistSession: false } },
  );
  const { data: auth } = await supabase.auth.getUser();
  if (!auth?.user) {
    return NextResponse.json({ error: "ログインし直してください。" }, { status: 401 });
  }
  // 組織には複数人いるので、自分の行に絞る
  const { data: member, error } = await supabase
    .from("org_members")
    .select("org_id")
    .eq("org_id", orgId)
    .eq("user_id", auth.user.id)
    .maybeSingle();
  if (error || !member) {
    return NextResponse.json({ error: "この組織には投稿できません。" }, { status: 403 });
  }

  const key = buildImageKey(orgId, ext);
  const put = await fetch(presignPut(cfg, key, file.type), {
    method: "PUT",
    headers: { "Content-Type": file.type },
    body: await file.arrayBuffer(),
  });
  if (!put.ok) {
    return NextResponse.json(
      { error: `画像を保存できませんでした（${put.status}）。` },
      { status: 502 },
    );
  }

  return NextResponse.json({
    storagePath: key,
    publicUrl: publicUrlFor(cfg, key),
    contentType: file.type,
  });
}
