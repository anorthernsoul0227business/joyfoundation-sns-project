/**
 * Cloudflare R2 への署名付きアップロードURLを作る（サーバー専用）。
 *
 * 2026-09-04: 画像を記事に直接アップロードできるようにするために追加した。
 * @aws-sdk を入れると関数が重くなるので、必要な PUT の署名だけを自前で作る
 * （AWS Signature Version 4。R2 は S3 互換なので同じ手順で通る）。
 *
 * 保存先のキーは、旧 FastAPI が使っていた規則をそのまま引き継ぐ:
 *   post-media/{org_id}/{YYYY/MM/DD}/{uuid}.{ext}
 */
import { createHash, createHmac } from "node:crypto";

const SERVICE = "s3";
const REGION = "auto";

export interface R2Config {
  accountId: string;
  accessKeyId: string;
  secretAccessKey: string;
  bucket: string;
  publicBaseUrl: string;
}

export function readR2Config(): R2Config | null {
  const accountId = process.env.R2_ACCOUNT_ID;
  const accessKeyId = process.env.R2_ACCESS_KEY_ID;
  const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
  const bucket = process.env.R2_BUCKET_NAME;
  const publicBaseUrl = process.env.R2_PUBLIC_URL;
  if (!accountId || !accessKeyId || !secretAccessKey || !bucket || !publicBaseUrl) {
    return null;
  }
  return { accountId, accessKeyId, secretAccessKey, bucket, publicBaseUrl };
}

const sha256hex = (v: string) => createHash("sha256").update(v, "utf8").digest("hex");
const hmac = (key: Buffer | string, v: string) => createHmac("sha256", key).update(v, "utf8").digest();

/** パスの各要素を RFC3986 で符号化する。encodeURIComponent は ! ' ( ) * を残すため補う */
function encodeSegment(s: string): string {
  return encodeURIComponent(s).replace(
    /[!'()*]/g,
    (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase(),
  );
}

/**
 * 指定キーへ PUT できる署名付きURLを返す。
 *
 * 有効期限内なら誰でもそのキーに書けるため、期限は短くする（既定10分）。
 * 署名は本文を含めない（UNSIGNED-PAYLOAD）ので、ブラウザから直接送れる。
 */
export function presignPut(
  cfg: R2Config,
  key: string,
  contentType: string,
  expiresInSeconds = 600,
): string {
  return presign(cfg, "PUT", key, contentType, expiresInSeconds);
}

/** 保管した画像を消す。記事から外した写真を残しておく理由がないため */
export function presignDelete(cfg: R2Config, key: string, expiresInSeconds = 600): string {
  return presign(cfg, "DELETE", key, null, expiresInSeconds);
}

function presign(
  cfg: R2Config,
  method: "PUT" | "DELETE",
  key: string,
  contentType: string | null,
  expiresInSeconds: number,
): string {
  const host = `${cfg.accountId}.r2.cloudflarestorage.com`;
  const now = new Date();
  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, "");   // 20260904T091500Z
  const dateStamp = amzDate.slice(0, 8);
  const scope = `${dateStamp}/${REGION}/${SERVICE}/aws4_request`;

  const canonicalUri =
    "/" + encodeSegment(cfg.bucket) + "/" + key.split("/").map(encodeSegment).join("/");

  const signedHeaders = contentType ? "content-type;host" : "host";
  // クエリはキー名で昇順に並べる必要がある
  const query: [string, string][] = [
    ["X-Amz-Algorithm", "AWS4-HMAC-SHA256"],
    ["X-Amz-Credential", `${cfg.accessKeyId}/${scope}`],
    ["X-Amz-Date", amzDate],
    ["X-Amz-Expires", String(expiresInSeconds)],
    ["X-Amz-SignedHeaders", signedHeaders],
  ];
  const canonicalQuery = query
    .map(([k, v]) => `${encodeSegment(k)}=${encodeSegment(v)}`)
    .sort()
    .join("&");

  const canonicalHeaders = contentType
    ? `content-type:${contentType}\nhost:${host}\n`
    : `host:${host}\n`;
  const canonicalRequest = [
    method,
    canonicalUri,
    canonicalQuery,
    canonicalHeaders,
    signedHeaders,
    "UNSIGNED-PAYLOAD",
  ].join("\n");

  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    scope,
    sha256hex(canonicalRequest),
  ].join("\n");

  const signingKey = hmac(
    hmac(hmac(hmac(`AWS4${cfg.secretAccessKey}`, dateStamp), REGION), SERVICE),
    "aws4_request",
  );
  const signature = createHmac("sha256", signingKey).update(stringToSign, "utf8").digest("hex");

  return `https://${host}${canonicalUri}?${canonicalQuery}&X-Amz-Signature=${signature}`;
}

/** 画像のオブジェクトキー。旧 FastAPI と同じ規則にそろえる */
export function buildImageKey(orgId: string, ext: string): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  const uuid = crypto.randomUUID().replace(/-/g, "");
  return `post-media/${orgId}/${d.getFullYear()}/${p(d.getMonth() + 1)}/${p(d.getDate())}/${uuid}.${ext}`;
}

export function publicUrlFor(cfg: R2Config, key: string): string {
  return `${cfg.publicBaseUrl.replace(/\/$/, "")}/${key.split("/").map(encodeSegment).join("/")}`;
}
