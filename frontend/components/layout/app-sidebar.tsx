"use client";

import { Bot, Heart, Home, MessageCircle, UserRoundCog } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "首页", icon: Home },
  { href: "/chat", label: "智能推荐", icon: MessageCircle },
  { href: "/favorites", label: "我的收藏", icon: Heart },
  { href: "/memory", label: "饮食记忆", icon: UserRoundCog },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-[240px] shrink-0 border-r border-border bg-white px-5 py-6 md:block">
      <Link href="/" className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-black text-white">
          <Bot className="h-5 w-5" />
        </div>
        <div>
          <p className="font-semibold tracking-tight">TasteScout Agent</p>
          <p className="text-xs text-muted-foreground">智能美食助手</p>
        </div>
      </Link>

      <nav className="mt-10 space-y-2">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-muted-foreground transition",
                active && "bg-black text-white",
                !active && "hover:bg-neutral-100 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
