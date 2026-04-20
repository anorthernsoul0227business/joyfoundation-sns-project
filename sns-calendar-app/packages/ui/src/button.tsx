import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ className = "", type = "button", ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center rounded-md bg-brand-ink px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 ${className}`.trim()}
      type={type}
      {...props}
    />
  );
}

