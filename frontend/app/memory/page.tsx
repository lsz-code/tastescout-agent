"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getLongTermMemory, refreshLongTermMemory } from "@/lib/api-client";
import { useUserStore } from "@/stores/user-store";
import { useState } from "react";

function Pills({ items }: { items?: string[] }) {
  if (!items?.length) {
    return <p className="text-sm text-muted-foreground">暂无数据</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full bg-neutral-100 px-3 py-1 text-sm text-neutral-700"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function MemoryPage() {
  const { userId } = useUserStore();
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["long-term-memory", userId],
    queryFn: () => getLongTermMemory(userId),
  });
  const refreshMutation = useMutation({
    mutationFn: () => refreshLongTermMemory(userId),
    onSuccess: async () => {
      setNotice("饮食记忆已更新");
      await queryClient.invalidateQueries({
        queryKey: ["long-term-memory", userId],
      });
    },
    onError: () => {
      setNotice("饮食记忆更新失败");
    },
  });

  const memory = data?.memory;
  const price = memory?.price_preference;

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">饮食记忆</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              系统会根据你的收藏和交互，总结你的菜系、价格和场景偏好。
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            disabled={refreshMutation.isPending}
            onClick={() => refreshMutation.mutate()}
          >
            {refreshMutation.isPending ? "刷新中..." : "刷新饮食记忆"}
          </Button>
        </div>

        {notice ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              {notice}
            </CardContent>
          </Card>
        ) : null}

        {isLoading ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              正在加载饮食记忆...
            </CardContent>
          </Card>
        ) : null}

        {error instanceof Error ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              {error.message}
            </CardContent>
          </Card>
        ) : null}

        {!isLoading && !error ? (
          <div className="grid gap-5 md:grid-cols-2">
            <Card>
              <CardHeader>
                <h2 className="font-semibold">偏好菜系</h2>
              </CardHeader>
              <CardContent>
                <Pills items={memory?.favorite_cuisines} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="font-semibold">口味偏好</h2>
              </CardHeader>
              <CardContent>
                <Pills items={memory?.taste_preference} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="font-semibold">忌口</h2>
              </CardHeader>
              <CardContent>
                <Pills items={memory?.avoid_foods} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="font-semibold">价格偏好</h2>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>最低人均：{price?.min_price ?? "暂无"}</p>
                <p>最高人均：{price?.max_price ?? "暂无"}</p>
                <p>平均人均：{price?.avg_price ?? "暂无"}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="font-semibold">喜欢的菜品</h2>
              </CardHeader>
              <CardContent>
                <Pills items={memory?.favorite_dishes} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="font-semibold">常用场景</h2>
              </CardHeader>
              <CardContent>
                <Pills items={memory?.preferred_scenes} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="font-semibold">记忆摘要</h2>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-muted-foreground">
                  {memory?.memory_summary || "暂无长期偏好总结。"}
                </p>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
