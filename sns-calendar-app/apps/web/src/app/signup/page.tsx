"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthCard } from "../../components/AuthCard";
import { AuthField } from "../../components/AuthField";
import { ApiError, signup } from "../../lib/api-client";
import { useAuthStore } from "../../stores/auth";

const signupSchema = z
  .object({
    display_name: z.string().max(50, "表示名は50文字以内で入力してください。").optional(),
    email: z.string().email("有効なメールアドレスを入力してください。"),
    password: z.string().min(8, "パスワードは8文字以上で入力してください。"),
    passwordConfirm: z.string().min(8, "確認用パスワードは8文字以上で入力してください。"),
  })
  .refine((values) => values.password === values.passwordConfirm, {
    message: "確認用パスワードが一致しません。",
    path: ["passwordConfirm"],
  });

type SignupFormValues = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    setError,
  } = useForm<SignupFormValues>({
    defaultValues: {
      display_name: "",
      email: "",
      password: "",
      passwordConfirm: "",
    },
    resolver: zodResolver(signupSchema),
  });

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, router]);

  async function onSubmit(values: SignupFormValues) {
    try {
      await signup({
        display_name: values.display_name?.trim() || undefined,
        email: values.email,
        password: values.password,
      });
      router.replace("/");
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "登録に失敗しました。時間をおいて再度お試しください。";

      setError("email", {
        message,
        type: "server",
      });
    }
  }

  return (
    <AuthCard
      alternateHref="/login"
      alternateLabel="ログイン"
      alternateText="既にアカウントをお持ちの方は"
      description="最初のアカウントを作成すると、そのままログイン状態でホームへ移動します。ヘルプマークから各入力項目の意図も確認できます。"
      eyebrow="Create Account"
      title="投稿フローを整えるための最初の設定"
    >
      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
        <div>
          <p className="text-2xl font-semibold text-brand-ink">サインアップ</p>
          <p className="mt-2 text-sm text-slate-500">
            必要な情報だけでアカウントを作成できます。
          </p>
        </div>

        <AuthField error={errors.display_name?.message} helpTopic="signup.display_name" label="表示名（任意）">
          <input
            autoComplete="nickname"
            className="w-full rounded-2xl border border-brand-ink/10 bg-brand-sand/40 px-4 py-3 text-base text-brand-ink outline-none transition focus:border-brand-ocean focus:bg-white"
            placeholder="例: 山田 花子"
            type="text"
            {...register("display_name")}
          />
        </AuthField>

        <AuthField error={errors.email?.message} helpTopic="signup.email" label="メールアドレス">
          <input
            autoComplete="email"
            className="w-full rounded-2xl border border-brand-ink/10 bg-brand-sand/40 px-4 py-3 text-base text-brand-ink outline-none transition focus:border-brand-ocean focus:bg-white"
            placeholder="you@example.com"
            type="email"
            {...register("email")}
          />
        </AuthField>

        <AuthField error={errors.password?.message} helpTopic="signup.password" label="パスワード">
          <input
            autoComplete="new-password"
            className="w-full rounded-2xl border border-brand-ink/10 bg-brand-sand/40 px-4 py-3 text-base text-brand-ink outline-none transition focus:border-brand-ocean focus:bg-white"
            placeholder="8文字以上"
            type="password"
            {...register("password")}
          />
        </AuthField>

        <AuthField
          error={errors.passwordConfirm?.message}
          helpTopic="signup.password_confirm"
          label="パスワード（確認）"
        >
          <input
            autoComplete="new-password"
            className="w-full rounded-2xl border border-brand-ink/10 bg-brand-sand/40 px-4 py-3 text-base text-brand-ink outline-none transition focus:border-brand-ocean focus:bg-white"
            placeholder="もう一度入力"
            type="password"
            {...register("passwordConfirm")}
          />
        </AuthField>

        <button
          className="w-full rounded-2xl bg-brand-ocean px-4 py-3 text-base font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "登録中..." : "アカウントを作成"}
        </button>
      </form>
    </AuthCard>
  );
}
