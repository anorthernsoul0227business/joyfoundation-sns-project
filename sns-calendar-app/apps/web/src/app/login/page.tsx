"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthCard } from "../../components/AuthCard";
import { AuthField } from "../../components/AuthField";
import { ApiError, login } from "../../lib/api-client";
import { useAuthStore } from "../../stores/auth";

const loginSchema = z.object({
  email: z.string().email("有効なメールアドレスを入力してください。"),
  password: z.string().min(8, "パスワードは8文字以上で入力してください。"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const [redirect, setRedirect] = useState("/");
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    setError,
  } = useForm<LoginFormValues>({
    defaultValues: {
      email: "",
      password: "",
    },
    resolver: zodResolver(loginSchema),
  });

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    setRedirect(searchParams.get("redirect") || "/");
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(redirect);
    }
  }, [isAuthenticated, redirect, router]);

  async function onSubmit(values: LoginFormValues) {
    try {
      await login(values);
      router.replace(redirect);
    } catch (error) {
      if (error instanceof ApiError) {
        setError("password", {
          message: error.message,
          type: "server",
        });
        return;
      }

      setError("password", {
        message: "ログインに失敗しました。時間をおいて再度お試しください。",
        type: "server",
      });
    }
  }

  return (
    <AuthCard
      alternateHref="/signup"
      alternateLabel="新規登録"
      alternateText="アカウントをお持ちでない方は"
      description="投稿計画と下書き管理に戻るためのサインイン画面です。メールアドレスとパスワードでログインしてください。"
      eyebrow="Welcome Back"
      title="制作の続きを、すぐに再開"
    >
      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
        <div>
          <p className="text-2xl font-semibold text-brand-ink">ログイン</p>
          <p className="mt-2 text-sm text-slate-500">
            アカウント情報を入力して、SNS Calendar に戻ります。
          </p>
        </div>

        <AuthField error={errors.email?.message} helpTopic="login.email" label="メールアドレス">
          <input
            autoComplete="email"
            className="w-full rounded-2xl border border-brand-ink/10 bg-brand-sand/40 px-4 py-3 text-base text-brand-ink outline-none transition focus:border-brand-ocean focus:bg-white"
            placeholder="you@example.com"
            type="email"
            {...register("email")}
          />
        </AuthField>

        <AuthField error={errors.password?.message} helpTopic="login.password" label="パスワード">
          <input
            autoComplete="current-password"
            className="w-full rounded-2xl border border-brand-ink/10 bg-brand-sand/40 px-4 py-3 text-base text-brand-ink outline-none transition focus:border-brand-ocean focus:bg-white"
            placeholder="8文字以上"
            type="password"
            {...register("password")}
          />
        </AuthField>

        <button
          className="w-full rounded-2xl bg-brand-ocean px-4 py-3 text-base font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "ログイン中..." : "ログイン"}
        </button>
      </form>

      <div className="mt-8 rounded-2xl border border-brand-ink/10 bg-brand-sand/40 p-4 text-sm text-slate-500">
        入力情報はこの画面上でのみ利用し、ブラウザのコンソールや画面表示には出しません。
      </div>

      <div className="mt-4 text-sm text-slate-500">
        戻る場合は{" "}
        <Link className="font-semibold text-brand-ocean hover:underline" href="/">
          ホーム
        </Link>
      </div>
    </AuthCard>
  );
}
