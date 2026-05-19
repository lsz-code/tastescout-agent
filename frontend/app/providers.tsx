"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useEffect, useState } from "react";
import { bootstrapUser } from "@/lib/api-client";
import { useUserStore } from "@/stores/user-store";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  );
  const initialized = useUserStore((state) => state.initialized);
  const userId = useUserStore((state) => state.userId);
  const initGuestUser = useUserStore((state) => state.initGuestUser);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    initGuestUser();
  }, [initGuestUser]);

  useEffect(() => {
    if (!initialized || !userId) return;

    bootstrapUser(userId, "匿名用户")
      .then(() => {
        setInitError(null);
      })
      .catch(() => {
        setInitError("匿名用户初始化失败，请检查后端服务。");
      });
  }, [initialized, userId]);

  return (
    <QueryClientProvider client={queryClient}>
      {!initialized ? (
        <div className="flex min-h-screen items-center justify-center bg-neutral-100 px-6 text-sm text-muted-foreground">
          正在初始化匿名用户...
        </div>
      ) : (
        <>
          {initError ? (
            <div className="fixed left-1/2 top-4 z-[60] w-[calc(100vw-32px)] max-w-md -translate-x-1/2 rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-700 shadow-lg">
              {initError}
            </div>
          ) : null}
          {children}
        </>
      )}
    </QueryClientProvider>
  );
}
