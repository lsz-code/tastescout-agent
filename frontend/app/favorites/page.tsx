"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { RestaurantCard } from "@/components/restaurants/restaurant-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getFavorites } from "@/lib/api-client";
import { useUserStore } from "@/stores/user-store";

export default function FavoritesPage() {
  const { userId } = useUserStore();
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["favorites", userId],
    queryFn: () => getFavorites(userId),
  });

  const restaurants = data ?? [];

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">我的收藏</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              这里会展示你收藏过的餐厅，后续会用于总结你的饮食偏好。
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? "刷新中..." : "刷新收藏"}
          </Button>
        </div>

        {isLoading ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              正在加载收藏餐厅...
            </CardContent>
          </Card>
        ) : null}

        {error instanceof Error ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              收藏列表加载失败，请检查后端服务。
            </CardContent>
          </Card>
        ) : null}

        {!isLoading && !error && restaurants.length === 0 ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              还没有收藏餐厅，可以先去智能推荐里收藏喜欢的店。
            </CardContent>
          </Card>
        ) : null}

        <div className="space-y-4">
          {restaurants.map((restaurant) => (
            <RestaurantCard key={restaurant.poi_id} restaurant={restaurant} />
          ))}
        </div>
      </div>
    </AppShell>
  );
}
