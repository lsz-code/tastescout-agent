"use client";

import { MessageSquareText } from "lucide-react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import {
  getConversationKey,
  PersistedChatMessage,
  useChatStore,
} from "@/stores/chat-store";
import { useUserStore } from "@/stores/user-store";
import {
  buildConversationTitle,
  getConversationUpdatedAt,
} from "@/lib/conversation-title";

type ConversationItem = {
  key: string;
  sessionId: string;
  title: string;
  updatedAt: string;
  messageCount: number;
};

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildConversationItems(
  userId: string,
  histories: Record<string, PersistedChatMessage[]>,
) {
  return Object.entries(histories)
    .filter(([key, messages]) => key.startsWith(`${userId}:`) && messages.length > 0)
    .map(([key, messages]) => ({
      key,
      sessionId: key.slice(`${userId}:`.length),
      title: buildConversationTitle(messages),
      updatedAt: getConversationUpdatedAt(messages),
      messageCount: messages.length,
    }))
    .sort(
      (left, right) =>
        new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
    );
}

export default function HistoryPage() {
  const router = useRouter();
  const userId = useUserStore((state) => state.userId);
  const currentSessionId = useUserStore((state) => state.sessionId);
  const setUser = useUserStore((state) => state.setUser);
  const newSession = useUserStore((state) => state.newSession);
  const chatHistories = useChatStore((state) => state.chatHistories);
  const conversations = buildConversationItems(userId, chatHistories);
  const currentKey = getConversationKey(userId, currentSessionId);

  function openConversation(item: ConversationItem) {
    setUser({ sessionId: item.sessionId });
    router.push("/chat");
  }

  function startNewChat() {
    newSession();
    router.push("/chat");
  }

  return (
    <AppShell>
      <section className="warm-panel flex h-[calc(100vh-2rem)] min-h-0 flex-col overflow-hidden rounded-[22px]">
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-orange-100/70 px-7 py-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-amber-950">
              历史对话
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              根据聊天里提到的菜系和用餐场景，自动整理会话名称。
            </p>
          </div>
          <Button type="button" className="rounded-full" onClick={startNewChat}>
            新建对话
          </Button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {conversations.length === 0 ? (
            <div className="flex h-full items-center justify-center text-center">
              <div>
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-orange-50 text-orange-500">
                  <MessageSquareText className="h-7 w-7" />
                </div>
                <h2 className="font-semibold text-amber-950">暂无历史对话</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  开始一次推荐后，这里会显示对应的历史记录。
                </p>
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl divide-y divide-orange-100 rounded-2xl bg-white/75">
              {conversations.map((item) => {
                const active = item.key === currentKey;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => openConversation(item)}
                    className={`flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition ${
                      active
                        ? "bg-orange-50 text-orange-700"
                        : "text-amber-950 hover:bg-orange-50/70"
                    }`}
                  >
                    <span className="min-w-0 truncate text-base font-medium">
                      {item.title}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatTime(item.updatedAt)} · {item.messageCount} 条
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </AppShell>
  );
}
