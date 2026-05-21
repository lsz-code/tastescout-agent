"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { FolderHeart, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { RestaurantCard } from "@/components/restaurants/restaurant-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  createFavoriteCollection,
  getFavoriteCollections,
  getFavorites,
} from "@/lib/api-client";
import { FavoriteCollection } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { useUserStore } from "@/stores/user-store";

export default function FavoritesPage() {
  const { userId } = useUserStore();
  const queryClient = useQueryClient();
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(
    null,
  );
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [collectionName, setCollectionName] = useState("");
  const [collectionDescription, setCollectionDescription] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const collectionsQuery = useQuery({
    queryKey: ["favorite-collections", userId],
    queryFn: () => getFavoriteCollections(userId),
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });

  const collections = useMemo(
    () => collectionsQuery.data ?? [],
    [collectionsQuery.data],
  );

  useEffect(() => {
    if (collections.length === 0) {
      setSelectedCollectionId(null);
      return;
    }

    const selectedExists = collections.some(
      (collection) => collection.id === selectedCollectionId,
    );
    if (selectedExists) return;

    const defaultCollection =
      collections.find((collection) => collection.is_default) ?? collections[0];
    setSelectedCollectionId(defaultCollection.id);
  }, [collections, selectedCollectionId]);

  const selectedCollection =
    collections.find((collection) => collection.id === selectedCollectionId) ??
    null;

  const favoritesQuery = useQuery({
    queryKey: ["favorites", userId, selectedCollectionId],
    queryFn: () => getFavorites(userId, selectedCollectionId),
    enabled: selectedCollectionId != null,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });

  const createCollectionMutation = useMutation({
    mutationFn: createFavoriteCollection,
    onSuccess: async (collection) => {
      setCollectionName("");
      setCollectionDescription("");
      setShowCreateForm(false);
      setNotice("收藏夹创建成功");
      await queryClient.invalidateQueries({
        queryKey: ["favorite-collections", userId],
      });
      setSelectedCollectionId(collection.id);
      await queryClient.invalidateQueries({
        queryKey: ["favorites", userId, collection.id],
      });
    },
    onError: () => {
      setNotice("收藏夹创建失败，请稍后再试。");
    },
  });

  function handleCreateCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = collectionName.trim();
    const description = collectionDescription.trim();
    if (!name) {
      setNotice("请输入收藏夹名称。");
      return;
    }

    setNotice(null);
    createCollectionMutation.mutate({
      user_id: userId,
      name,
      description: description || null,
    });
  }

  function handleSelectCollection(collection: FavoriteCollection) {
    setNotice(null);
    setSelectedCollectionId(collection.id);
  }

  const restaurants = favoritesQuery.data ?? [];

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">我的收藏</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              这里会展示你收藏过的餐厅，后续会用于总结你的饮食偏好。
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => collectionsQuery.refetch()}
              disabled={collectionsQuery.isFetching || favoritesQuery.isFetching}
            >
              {collectionsQuery.isFetching || favoritesQuery.isFetching
                ? "刷新中..."
                : "刷新收藏"}
            </Button>
            <Button
              type="button"
              onClick={() => {
                setNotice(null);
                setShowCreateForm((current) => !current);
              }}
            >
              <Plus className="h-4 w-4" />
              创建收藏夹
            </Button>
          </div>
        </div>

        {notice ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted-foreground">
              {notice}
            </CardContent>
          </Card>
        ) : null}

        {showCreateForm ? (
          <Card>
            <CardContent className="pt-5">
              <form
                className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto]"
                onSubmit={handleCreateCollection}
              >
                <div>
                  <label
                    className="mb-2 block text-sm font-medium"
                    htmlFor="collection-name"
                  >
                    收藏夹名称
                  </label>
                  <Input
                    id="collection-name"
                    value={collectionName}
                    disabled={createCollectionMutation.isPending}
                    placeholder="例如：周末聚餐"
                    onChange={(event) => setCollectionName(event.target.value)}
                  />
                </div>
                <div>
                  <label
                    className="mb-2 block text-sm font-medium"
                    htmlFor="collection-description"
                  >
                    描述
                  </label>
                  <Input
                    id="collection-description"
                    value={collectionDescription}
                    disabled={createCollectionMutation.isPending}
                    placeholder="可选，例如：适合朋友一起吃的店"
                    onChange={(event) =>
                      setCollectionDescription(event.target.value)
                    }
                  />
                </div>
                <div className="flex items-end gap-2">
                  <Button
                    type="submit"
                    disabled={createCollectionMutation.isPending}
                  >
                    {createCollectionMutation.isPending ? "创建中..." : "创建"}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={createCollectionMutation.isPending}
                    onClick={() => {
                      setShowCreateForm(false);
                      setCollectionName("");
                      setCollectionDescription("");
                    }}
                  >
                    取消
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="h-fit p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold">收藏夹</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  选择一个收藏夹查看餐厅。
                </p>
              </div>
              <FolderHeart className="h-5 w-5 text-muted-foreground" />
            </div>

            {collectionsQuery.isLoading ? (
              <StateText>正在加载收藏夹...</StateText>
            ) : null}

            {collectionsQuery.error instanceof Error ? (
              <StateText>收藏夹加载失败，请检查后端服务。</StateText>
            ) : null}

            {!collectionsQuery.isLoading &&
            !collectionsQuery.error &&
            collections.length === 0 ? (
              <StateText>还没有收藏夹，可以先创建一个收藏夹。</StateText>
            ) : null}

            <div className="space-y-3">
              {collections.map((collection) => (
                <button
                  key={collection.id}
                  type="button"
                  className={cn(
                    "w-full rounded-2xl border border-neutral-200 bg-white p-4 text-left transition-all hover:border-neutral-300 hover:bg-neutral-50 hover:shadow-sm",
                    selectedCollectionId === collection.id &&
                      "border-black bg-neutral-50 shadow-sm",
                  )}
                  onClick={() => handleSelectCollection(collection)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold">
                        {collection.name}
                      </h3>
                      {collection.description ? (
                        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                          {collection.description}
                        </p>
                      ) : (
                        <p className="mt-1 text-xs text-muted-foreground">
                          暂无描述
                        </p>
                      )}
                    </div>
                    {collection.is_default ? (
                      <span className="shrink-0 rounded-full bg-black px-2.5 py-1 text-xs text-white">
                        默认收藏夹
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    共 {collection.restaurant_count} 家餐厅
                  </p>
                </button>
              ))}
            </div>
          </Card>

          <Card className="min-h-[420px] p-5">
            <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">
                  {selectedCollection?.name ?? "收藏餐厅"}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {selectedCollection
                    ? `共 ${restaurants.length} 家餐厅`
                    : "请选择左侧收藏夹查看餐厅"}
                </p>
              </div>
              {selectedCollection?.is_default ? (
                <span className="w-fit rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">
                  默认收藏夹
                </span>
              ) : null}
            </div>

            {selectedCollectionId == null &&
            !collectionsQuery.isLoading &&
            collections.length > 0 ? (
              <StateText>请选择左侧收藏夹查看餐厅。</StateText>
            ) : null}

            {favoritesQuery.isLoading ? (
              <StateText>正在加载收藏餐厅...</StateText>
            ) : null}

            {favoritesQuery.error instanceof Error ? (
              <StateText>收藏餐厅加载失败，请检查后端服务。</StateText>
            ) : null}

            {!favoritesQuery.isLoading &&
            !favoritesQuery.error &&
            selectedCollectionId != null &&
            restaurants.length === 0 ? (
              <StateText>这个收藏夹还没有餐厅。</StateText>
            ) : null}

            <div className="grid gap-5 xl:grid-cols-2">
              {restaurants.map((restaurant) => (
                <RestaurantCard
                  key={`${restaurant.collection_id}-${restaurant.poi_id}`}
                  restaurant={restaurant}
                />
              ))}
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

function StateText({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm leading-6 text-muted-foreground">
      {children}
    </div>
  );
}
