import { AgentToolCall } from "@/lib/api-types";
import { cn } from "@/lib/utils";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: AgentToolCall[];
  needsFollowup?: boolean;
  missingSlots?: string[];
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

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[82%]", isUser ? "text-right" : "text-left")}>
        <div className="mb-1 px-1 text-xs text-muted-foreground">
          {isUser ? "我" : "TasteScout"}
        </div>
        <div
          className={cn(
            "whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm",
            isUser ? "bg-black text-white" : "border border-border bg-white",
          )}
        >
          {message.content}
          {!isUser && message.toolCalls?.length ? (
            <div className="mt-3 border-t border-neutral-200 pt-2 text-xs text-muted-foreground">
              已调用工具：
              {message.toolCalls.map((tool) => tool.tool_name).join("、")}
            </div>
          ) : null}
          {showFollowupActions ? (
            <div className="mt-3 flex flex-wrap gap-2 border-t border-neutral-200 pt-3">
              {["川菜", "火锅", "烧烤", "日料"].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => onQuickReply?.(item)}
                  className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-700 hover:bg-neutral-200"
                >
                  {item}
                </button>
              ))}
              {message.missingSlots?.includes("location") ? (
                <button
                  type="button"
                  onClick={onRequestLocation}
                  className="rounded-full bg-black px-3 py-1 text-xs text-white hover:bg-black/80"
                >
                  使用我的位置
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
