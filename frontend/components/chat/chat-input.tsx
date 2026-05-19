"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
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
  const [value, setValue] = useState(example);

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
    <form
      onSubmit={handleSubmit}
      className="shrink-0 border-t border-border bg-white p-4"
    >
      <div className="mb-3 flex flex-col justify-between gap-3 rounded-2xl bg-neutral-50 px-4 py-3 text-sm text-neutral-700 sm:flex-row sm:items-center">
        <span>{locationStatusText}</span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={disabled || locating}
            onClick={onRequestLocation}
          >
            {locating ? "正在定位..." : "使用我的位置"}
          </Button>
          {hasLocation ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={disabled || locating}
              onClick={onClearLocation}
            >
              清除位置
            </Button>
          ) : null}
        </div>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={example}
        disabled={disabled}
        className="min-h-20 flex-1"
      />
      <Button
        type="submit"
        disabled={disabled}
        className="h-12 px-6 sm:h-auto"
      >
        {disabled ? "推荐中..." : "发送"}
      </Button>
      </div>
    </form>
  );
}
