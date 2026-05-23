"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { MapPin, Send, Smile, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const example =
  "附近有什么适合朋友聚餐的川菜，人均200以内";

export function ChatInput({
  disabled,
  locationStatusText,
  locating,
  hasLocation,
  onRequestLocation,
  onClearLocation,
  onSend,
}: {
  disabled?: boolean;
  locationStatusText: string;
  locating?: boolean;
  hasLocation?: boolean;
  onRequestLocation: () => void;
  onClearLocation: () => void;
  onSend: (message: string) => void;
}) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage();
  }

  function submitMessage() {
    const message = value.trim();
    if (!message || disabled) return;
    onSend(message);
    setValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    submitMessage();
  }

  return (
    <form onSubmit={handleSubmit} className="shrink-0 bg-white/80 px-5 pb-5">
      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        {["有什么招牌菜？", "有适合拍照的环境吗？", "附近还有其他推荐吗？"].map(
          (item) => (
            <button
              key={item}
              type="button"
              disabled={disabled}
              onClick={() => onSend(item)}
              className="rounded-full border border-orange-100 bg-white px-3 py-1.5 text-amber-800 shadow-sm hover:bg-orange-50 disabled:opacity-50"
            >
              {item}
            </button>
          ),
        )}
      </div>

      <div className="mb-3 flex flex-col justify-between gap-2 rounded-2xl bg-orange-50 px-3 py-2 text-xs text-amber-800 sm:flex-row sm:items-center">
        <span className="inline-flex min-w-0 items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{locationStatusText}</span>
        </span>
        <div className="flex shrink-0 gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled || locating}
            onClick={onRequestLocation}
            className="h-8 rounded-full px-3 text-xs"
          >
            {locating ? "定位中..." : "使用位置"}
          </Button>
          {hasLocation ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={disabled || locating}
              onClick={onClearLocation}
              className="h-8 w-8 rounded-full"
              title="清除位置"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          ) : null}
        </div>
      </div>

      <div className="flex items-end gap-3 rounded-[26px] border border-orange-100 bg-white px-4 py-3 shadow-sm">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`继续和我聊聊你的需求吧～例如：${example}`}
          disabled={disabled}
          className="min-h-11 flex-1 resize-none border-0 bg-transparent px-0 py-2 shadow-none focus-visible:ring-0"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="mb-1 hidden h-9 w-9 rounded-full text-amber-700 sm:inline-flex"
          title="表情"
        >
          <Smile className="h-5 w-5" />
        </Button>
        <Button
          type="submit"
          disabled={disabled}
          size="icon"
          className="mb-1 h-11 w-11 shrink-0 rounded-full"
          title="发送"
        >
          <Send className="h-5 w-5" />
        </Button>
      </div>
    </form>
  );
}
