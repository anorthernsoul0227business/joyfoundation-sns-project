"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AppHeader } from "./AppHeader";
import { useAuthStore } from "../stores/auth";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const helpModeEnabled = useAuthStore((state) => state.helpModeEnabled);

  useEffect(() => {
    document.body.classList.toggle("help-off", !helpModeEnabled);
  }, [helpModeEnabled]);

  return (
    <>
      <AppHeader />
      <div className={pathname === "/login" || pathname === "/signup" ? "" : "pb-8"}>
        {children}
      </div>
    </>
  );
}
