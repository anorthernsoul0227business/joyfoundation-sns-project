"use client";

import type { ReactNode } from "react";
import { HelpMark } from "./HelpMark";

type AuthFieldProps = {
  children: ReactNode;
  error?: string;
  helpTopic?: string;
  label: string;
};

export function AuthField({ children, error, helpTopic, label }: AuthFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center gap-2 text-sm font-medium text-brand-ink">
        {label}
        {helpTopic ? <HelpMark topic={helpTopic} /> : null}
      </span>
      {children}
      {error ? <p className="mt-2 text-sm text-rose-600">{error}</p> : null}
    </label>
  );
}
