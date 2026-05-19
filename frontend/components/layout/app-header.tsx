"use client";

import { CircleCheck, RefreshCcw, UserRoundPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUserStore } from "@/stores/user-store";

export function AppHeader() {
  const { userId, sessionId, newSession, resetGuestUser } = useUserStore();

  function handleResetGuestUser() {
    const confirmed = window.confirm(
      "切换匿名用户后，将使用新的收藏和记忆，当前浏览器的旧用户不会自动删除。确定切换吗？",
    );
    if (confirmed) {
      resetGuestUser();
    }
  }

  return (
    <header className="flex min-h-20 items-center justify-between border-b border-border bg-white px-4 md:px-8">
      <div>
        <p className="text-sm font-medium">TasteScout Agent</p>
        <p className="text-xs text-muted-foreground md:hidden">
          智能美食推荐
        </p>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden text-right text-xs text-muted-foreground lg:block">
          <p>当前用户：{userId}</p>
          <p>当前会话：{sessionId}</p>
        </div>
        <span className="hidden items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-700 sm:inline-flex">
          <CircleCheck className="h-3.5 w-3.5" />
          Agent 在线
        </span>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={newSession}
          title="新会话"
        >
          <RefreshCcw className="h-4 w-4" />
          <span className="hidden sm:inline">新会话</span>
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleResetGuestUser}
          title="切换匿名用户"
        >
          <UserRoundPlus className="h-4 w-4" />
          <span className="hidden sm:inline">切换匿名用户</span>
        </Button>
      </div>
    </header>
  );
}
