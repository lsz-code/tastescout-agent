import * as React from "react";
import { cn } from "@/lib/utils";

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "flex h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm outline-none transition focus:ring-2 focus:ring-ring",
        className,
      )}
      {...props}
    />
  );
}
