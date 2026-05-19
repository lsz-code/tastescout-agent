import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AgentToolCall, RestaurantItem } from "@/lib/api-types";

export type PersistedChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  restaurants?: RestaurantItem[];
  toolCalls?: AgentToolCall[];
  needsFollowup?: boolean;
  missingSlots?: string[];
};

export const EMPTY_CHAT_MESSAGES: PersistedChatMessage[] = [];

type ChatState = {
  chatHistories: Record<string, PersistedChatMessage[]>;
  getMessages: (userId: string, sessionId: string) => PersistedChatMessage[];
  appendMessage: (
    userId: string,
    sessionId: string,
    message: PersistedChatMessage,
  ) => void;
  setMessages: (
    userId: string,
    sessionId: string,
    messages: PersistedChatMessage[],
  ) => void;
  clearMessages: (userId: string, sessionId: string) => void;
  clearAllMessagesForUser: (userId: string) => void;
};

export function getConversationKey(userId: string, sessionId: string) {
  return `${userId}:${sessionId}`;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      chatHistories: {},
      getMessages: (userId, sessionId) =>
        get().chatHistories[getConversationKey(userId, sessionId)] ?? [],
      appendMessage: (userId, sessionId, message) =>
        set((state) => {
          const key = getConversationKey(userId, sessionId);
          const current = state.chatHistories[key] ?? [];
          return {
            chatHistories: {
              ...state.chatHistories,
              [key]: [...current, message],
            },
          };
        }),
      setMessages: (userId, sessionId, messages) =>
        set((state) => ({
          chatHistories: {
            ...state.chatHistories,
            [getConversationKey(userId, sessionId)]: messages,
          },
        })),
      clearMessages: (userId, sessionId) =>
        set((state) => ({
          chatHistories: {
            ...state.chatHistories,
            [getConversationKey(userId, sessionId)]: [],
          },
        })),
      clearAllMessagesForUser: (userId) =>
        set((state) => {
          const next = { ...state.chatHistories };
          Object.keys(next).forEach((key) => {
            if (key.startsWith(`${userId}:`)) {
              delete next[key];
            }
          });
          return { chatHistories: next };
        }),
    }),
    {
      name: "tastescout-chat-histories",
      version: 1,
    },
  ),
);
