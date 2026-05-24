"use client";

import { FormEvent, useState } from "react";
import { UserRoundCog } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useUserStore } from "@/stores/user-store";

export default function SettingsPage() {
  const {
    userId,
    username,
    sessionId,
    setUser,
    resetGuestUser,
  } = useUserStore();
  const [draftUsername, setDraftUsername] = useState(username);
  const [draftUserId, setDraftUserId] = useState(userId);
  const [notice, setNotice] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextUsername = draftUsername.trim();
    const nextUserId = draftUserId.trim();

    if (!nextUsername) {
      setNotice("请输入昵称。");
      return;
    }
    if (!nextUserId) {
      setNotice("请输入用户 ID。");
      return;
    }

    setUser({
      username: nextUsername,
      userId: nextUserId,
    });
    setNotice("个人信息已更新。");
  }

  function handleReset() {
    resetGuestUser();
    const next = useUserStore.getState();
    setDraftUsername(next.username);
    setDraftUserId(next.userId);
    setNotice("已切换到新的匿名用户。");
  }

  return (
    <AppShell>
      <section className="warm-panel flex h-[calc(100vh-2rem)] min-h-0 flex-col overflow-hidden rounded-[22px]">
        <div className="flex shrink-0 items-center gap-4 border-b border-orange-100/70 px-7 py-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-100 text-orange-600">
            <UserRoundCog className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-amber-950">
              设置
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              修改本地个人信息，会影响当前浏览器里的会话、收藏和记忆查询身份。
            </p>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-7 py-6">
          <div className="max-w-2xl space-y-5">
            {notice ? (
              <Card className="border-orange-100 bg-orange-50 shadow-none">
                <CardContent className="pt-5 text-sm text-amber-800">
                  {notice}
                </CardContent>
              </Card>
            ) : null}

            <Card className="border-orange-100 bg-white/85 shadow-sm">
              <CardContent className="pt-6">
                <form className="space-y-5" onSubmit={handleSubmit}>
                  <div>
                    <label
                      htmlFor="username"
                      className="mb-2 block text-sm font-semibold text-amber-950"
                    >
                      昵称
                    </label>
                    <Input
                      id="username"
                      value={draftUsername}
                      onChange={(event) => setDraftUsername(event.target.value)}
                      placeholder="例如：小美"
                      className="border-orange-100 bg-white"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="user-id"
                      className="mb-2 block text-sm font-semibold text-amber-950"
                    >
                      用户 ID
                    </label>
                    <Input
                      id="user-id"
                      value={draftUserId}
                      onChange={(event) => setDraftUserId(event.target.value)}
                      placeholder="用于后端收藏和记忆查询"
                      className="border-orange-100 bg-white"
                    />
                    <p className="mt-2 text-xs leading-5 text-muted-foreground">
                      修改用户 ID 后，会切换到另一个用户的数据范围；原用户的本地历史仍保留在浏览器中。
                    </p>
                  </div>

                  <div className="rounded-2xl bg-orange-50 px-4 py-3 text-sm text-amber-800">
                    当前会话：{sessionId}
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <Button type="submit" className="rounded-full">
                      保存个人信息
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      className="rounded-full"
                      onClick={handleReset}
                    >
                      切换匿名用户
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
