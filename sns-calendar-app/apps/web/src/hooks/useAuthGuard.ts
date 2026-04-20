"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "../stores/auth";

export function useAuthGuard() {
  const router = useRouter();
  const pathname = usePathname();
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  useEffect(() => {
    if (!hasHydrated || isAuthenticated) {
      return;
    }

    router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
  }, [hasHydrated, isAuthenticated, pathname, router]);

  return {
    isReady: hasHydrated && isAuthenticated,
  };
}
