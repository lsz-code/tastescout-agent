"use client";

import {
  Clock3,
  Heart,
  Home,
  NotebookText,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUserStore } from "@/stores/user-store";

const navItems = [
  { href: "/chat", label: "首页", icon: Home },
  { href: "/favorites", label: "收藏夹", icon: Heart },
  { href: "/memory", label: "饮食记忆", icon: NotebookText },
  { href: "/history", label: "历史对话", icon: Clock3 },
  { href: "/settings", label: "设置", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  const username = useUserStore((state) => state.username);

  return (
    <aside className="warm-panel hidden w-[232px] shrink-0 flex-col rounded-[22px] px-5 py-6 md:flex">
      <Link href="/chat" className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-100 text-2xl shadow-inner">
          🧑‍🍳
        </div>
        <div>
          <p className="text-lg font-bold tracking-tight">美食发现助手</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            发现美味 · 一段美食旅程
          </p>
        </div>
      </Link>

      <nav className="mt-8 space-y-3">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={`${item.href}-${item.label}`}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-amber-950 transition",
                active &&
                  "bg-orange-100 text-orange-600 shadow-sm shadow-orange-100",
                !active && "hover:bg-white/70 hover:text-orange-600",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-[22px] bg-white/70 p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-orange-100 text-xl">
            👩🏻
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-semibold">{username}</p>
              <span className="rounded-full border border-orange-300 px-1.5 py-0.5 text-[10px] font-semibold text-orange-600">
                VIP
              </span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">美食爱好者</p>
          </div>
        </div>
        <div className="mt-4 flex justify-center text-5xl">
          🍝
        </div>
      </div>
    </aside>
  );
}
