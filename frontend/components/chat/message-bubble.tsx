import { AgentToolCall } from "@/lib/api-types";
import { cn } from "@/lib/utils";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: AgentToolCall[];
  needsFollowup?: boolean;
  missingSlots?: string[];
  casualChat?: boolean;
};

export function MessageBubble({
  message,
  onQuickReply,
  onRequestLocation,
}: {
  message: ChatMessage;
  onQuickReply?: (text: string) => void;
  onRequestLocation?: () => void;
}) {
  const isUser = message.role === "user";
  const showFollowupActions = !isUser && message.needsFollowup;
  const showCuisineQuickReplies =
    showFollowupActions && message.missingSlots?.includes("cuisine");

  return (
    <div className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser ? (
        <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-orange-100 bg-orange-50 text-xl shadow-sm">
          🧑‍🍳
        </div>
      ) : null}
      <div className={cn("max-w-[84%]", isUser ? "text-right" : "text-left")}>
        <div
          className={cn(
            "whitespace-pre-wrap rounded-[18px] px-4 py-3 text-sm leading-6 shadow-sm",
            isUser
              ? "bg-orange-100 text-amber-950"
              : "border border-orange-100 bg-white text-amber-950",
          )}
        >
          {message.content}
          {!isUser && !message.casualChat && message.toolCalls?.length ? (
            <div className="mt-3 border-t border-orange-100 pt-2 text-xs text-muted-foreground">
              已调用工具：
              {message.toolCalls.map((tool) => tool.tool_name).join("、")}
            </div>
          ) : null}
          {showFollowupActions ? (
            <div className="mt-3 flex flex-wrap gap-2 border-t border-orange-100 pt-3">
              {showCuisineQuickReplies
                ? ["川菜", "火锅", "烧烤", "日料"].map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => onQuickReply?.(item)}
                      className="rounded-full bg-orange-50 px-3 py-1 text-xs text-orange-700 hover:bg-orange-100"
                    >
                      {item}
                    </button>
                  ))
                : null}
              {message.missingSlots?.includes("location") ? (
                <button
                  type="button"
                  onClick={onRequestLocation}
                  className="rounded-full bg-orange-500 px-3 py-1 text-xs text-white hover:bg-orange-600"
                >
                  使用我的位置
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
      {isUser ? (
        <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-xl shadow-sm">
          👩🏻
        </div>
      ) : null}
    </div>
  );
}
