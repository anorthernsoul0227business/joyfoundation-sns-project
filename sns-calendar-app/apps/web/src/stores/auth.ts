"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  displayName?: string | null;
  uiMode: "simple" | "pro";
  helpModeEnabled: boolean;
  defaultOrgId?: string | null;
}

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

interface AuthState {
  hasHydrated: boolean;
  helpModeEnabled: boolean;
  session: AuthSession | null;
  user: AuthUser | null;
  clear: () => void;
  isAuthenticated: () => boolean;
  setHasHydrated: (value: boolean) => void;
  setSession: (user: AuthUser, session: AuthSession) => void;
  setUser: (user: AuthUser) => void;
  toggleHelpMode: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      hasHydrated: false,
      helpModeEnabled: true,
      session: null,
      user: null,
      clear: () =>
        set((state) => ({
          session: null,
          user: null,
          helpModeEnabled: state.helpModeEnabled,
        })),
      isAuthenticated: () => {
        const session = get().session;
        if (!session) {
          return false;
        }

        return session.expiresAt > Math.floor(Date.now() / 1000);
      },
      setHasHydrated: (value) => set({ hasHydrated: value }),
      setSession: (user, session) =>
        set({
          user,
          session,
          helpModeEnabled: user.helpModeEnabled,
        }),
      setUser: (user) =>
        set({
          user,
          helpModeEnabled: user.helpModeEnabled,
        }),
      toggleHelpMode: () =>
        set((state) => {
          const helpModeEnabled = !state.helpModeEnabled;
          return {
            helpModeEnabled,
            user: state.user
              ? {
                  ...state.user,
                  helpModeEnabled,
                }
              : state.user,
          };
        }),
    }),
    {
      name: "sns-calendar-auth",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({
        helpModeEnabled: state.helpModeEnabled,
        session: state.session,
        user: state.user,
      }),
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
