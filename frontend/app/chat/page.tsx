"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { ChatInput } from "@/components/chat/chat-input";
import {
  ChatWindow,
  RecommendationPanel,
} from "@/components/chat/chat-window";
import { RestaurantMap } from "@/components/map/restaurant-map";
import { ChatMessage } from "@/components/chat/message-bubble";
import {
  addFavorite,
  getFavoriteCollections,
  refreshLongTermMemory,
  sendAgentMessage,
  upsertRestaurantFromRecommendation,
} from "@/lib/api-client";
import { useBrowserLocation } from "@/hooks/use-browser-location";
import {
  AddFavoriteRequest,
  FavoriteCollection,
  RestaurantItem,
} from "@/lib/api-types";
import { Button } from "@/components/ui/button";
import {
  EMPTY_CHAT_MESSAGES,
  getConversationKey,
  PersistedChatMessage,
  useChatStore,
} from "@/stores/chat-store";
import { useUserStore } from "@/stores/user-store";

export default function ChatPage() {
  const router = useRouter();
  const {
    userId,
    sessionId,
    newSession,
    currentLocation,
    locationLabel,
    locationPermission,
    setCurrentLocation,
    clearCurrentLocation,
    setLocationPermission,
  } = useUserStore();
  const queryClient = useQueryClient();
  const browserLocation = useBrowserLocation();
  const conversationKey = getConversationKey(userId, sessionId);
  const messages = useChatStore(
    (state) => state.chatHistories[conversationKey] ?? EMPTY_CHAT_MESSAGES,
  );
  const appendMessage = useChatStore((state) => state.appendMessage);
  const [favoritedPoiIds, setFavoritedPoiIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [favoriteLoadingPoiId, setFavoriteLoadingPoiId] = useState<string | null>(
    null,
  );
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedPoiId, setSelectedPoiId] = useState<string | null>(null);
  const [mapOpen, setMapOpen] = useState(false);
  const [favoriteTarget, setFavoriteTarget] = useState<RestaurantItem | null>(
    null,
  );
  const [selectedFavoriteCollectionId, setSelectedFavoriteCollectionId] =
    useState<number | null>(null);
  const [openingPoiId, setOpeningPoiId] = useState<string | null>(null);

  const chatMutation = useMutation({
    mutationFn: sendAgentMessage,
    onSuccess: (response) => {
      const isCasualChat = response.data?.casual_chat === true;
      appendMessage(userId, sessionId, {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        createdAt: new Date().toISOString(),
        restaurants: isCasualChat || response.data?.needs_followup
          ? undefined
          : response.data?.restaurants ?? [],
        toolCalls: isCasualChat ? undefined : response.tool_calls,
        needsFollowup: Boolean(response.data?.needs_followup),
        missingSlots: Array.isArray(response.data?.missing_slots)
          ? (response.data?.missing_slots as string[])
          : undefined,
        casualChat: isCasualChat,
      });
    },
    onError: () => {
      appendMessage(userId, sessionId, {
        id: `assistant-error-${Date.now()}`,
        role: "assistant",
        content: "推荐失败，请检查后端服务是否正常运行。",
        createdAt: new Date().toISOString(),
      });
    },
  });

  const favoriteCollectionsQuery = useQuery({
    queryKey: ["favorite-collections", userId],
    queryFn: () => getFavoriteCollections(userId),
    enabled: Boolean(favoriteTarget),
  });

  function handleSend(message: string) {
    setNotice(null);
    appendMessage(userId, sessionId, {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      createdAt: new Date().toISOString(),
    });
    chatMutation.mutate({
      user_id: userId,
      session_id: sessionId,
      message,
      location: currentLocation,
      location_label: locationLabel,
    });
  }

  function handleReroll() {
    handleSend("换一批");
  }

  function handleNewSession() {
    setNotice(null);
    setFavoriteLoadingPoiId(null);
    setFavoriteTarget(null);
    newSession();
  }

  function handleFavorite(restaurant: RestaurantItem) {
    if (!restaurant.poi_id || favoriteLoadingPoiId) return;
    setNotice(null);
    setFavoriteTarget(restaurant);
  }

  async function handleOpenRestaurant(restaurant: RestaurantItem) {
    if (!restaurant.poi_id || openingPoiId) return;

    setOpeningPoiId(restaurant.poi_id);
    setNotice(null);
    try {
      await upsertRestaurantFromRecommendation(restaurant);
      router.push(`/restaurants/${encodeURIComponent(restaurant.poi_id)}`);
    } catch {
      setNotice("餐厅详情打开失败，请稍后再试。");
    } finally {
      setOpeningPoiId(null);
    }
  }

  async function handleConfirmFavorite() {
    const restaurant = favoriteTarget;
    if (!restaurant?.poi_id || favoriteLoadingPoiId) return;

    if (selectedFavoriteCollectionId == null) {
      setNotice("请选择一个收藏夹。");
      return;
    }

    setNotice(null);
    setFavoriteLoadingPoiId(restaurant.poi_id);

    const payload: AddFavoriteRequest = {
      user_id: userId,
      collection_id: selectedFavoriteCollectionId,
      poi_id: restaurant.poi_id,
      name: restaurant.name,
      address: restaurant.address,
      photo: restaurant.photo,
      location: restaurant.location,
      cuisine_type: restaurant.cuisine_type,
      rating: restaurant.rating,
      avg_price: restaurant.avg_price,
      distance: restaurant.distance,
      recommended_dishes: restaurant.recommended_dishes,
      review_summary: restaurant.review_summary,
      recommend_reason: restaurant.recommend_reason,
      raw_data: restaurant.raw_data,
    };

    try {
      const response = await addFavorite(payload);
      setFavoritedPoiIds((current) => {
        const next = new Set(current);
        next.add(restaurant.poi_id);
        return next;
      });
      setFavoriteTarget(null);
      setNotice(
        response.already_exists
          ? `这家餐厅已经收藏过了：${restaurant.name}`
          : `已收藏：${restaurant.name}`,
      );

      if (!response.already_exists) {
        queryClient.setQueryData(
          ["favorites", userId, selectedFavoriteCollectionId],
          (current: unknown) => {
            if (!Array.isArray(current)) return current;
            const exists = current.some(
              (item) =>
                typeof item === "object" &&
                item !== null &&
                "poi_id" in item &&
                item.poi_id === restaurant.poi_id,
            );
            if (exists) return current;

            return [
              {
                id: response.favorite_id ?? Date.now(),
                collection_id: selectedFavoriteCollectionId,
                poi_id: restaurant.poi_id,
                name: restaurant.name,
                address: restaurant.address,
                photo: restaurant.photo,
                cuisine_type: restaurant.cuisine_type,
                rating: restaurant.rating,
                avg_price: restaurant.avg_price,
                distance: restaurant.distance,
                recommended_dishes: restaurant.recommended_dishes,
                review_summary: restaurant.review_summary,
                recommend_reason: restaurant.recommend_reason,
                created_at: new Date().toISOString(),
              },
              ...current,
            ];
          },
        );

        queryClient.setQueryData(
          ["favorite-collections", userId],
          (current: unknown) => {
            if (!Array.isArray(current)) return current;
            return current.map((collection) => {
              if (
                typeof collection !== "object" ||
                collection === null ||
                !("id" in collection) ||
                collection.id !== selectedFavoriteCollectionId
              ) {
                return collection;
              }
              const restaurantCount =
                "restaurant_count" in collection &&
                typeof collection.restaurant_count === "number"
                  ? collection.restaurant_count
                  : 0;
              return {
                ...collection,
                restaurant_count: restaurantCount + 1,
              };
            });
          },
        );
      }

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["favorite-collections", userId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["favorites", userId],
        }),
      ]);

      refreshLongTermMemory(userId).catch((error) => {
        console.warn("刷新长期记忆失败", error);
      });
    } catch {
      setNotice("收藏失败，请稍后再试。");
    } finally {
      setFavoriteLoadingPoiId(null);
    }
  }

  async function handleRequestLocation() {
    setNotice(null);
    setLocationPermission("requesting");

    try {
      const location = await browserLocation.requestLocation();
      if (!location) return;
      setCurrentLocation(location, "当前位置");
      setNotice("已获取当前位置，可以直接说‘附近有什么好吃的’。");
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : typeof error === "object" && error !== null && "message" in error
            ? String(error.message)
            : "定位失败，请稍后重试。";
      setLocationPermission(
        message.includes("拒绝") ? "denied" : "error",
      );
      setNotice(message);
    }
  }

  function handleClearLocation() {
    clearCurrentLocation();
    setNotice("已清除当前位置。");
  }

  function getLocationStatusText() {
    if (locationPermission === "requesting" || browserLocation.loading) {
      return "正在定位...";
    }
    if (locationPermission === "denied") {
      return "定位权限被拒绝";
    }
    if (currentLocation) {
      return `已使用${locationLabel ?? "当前位置"}`;
    }
    return "未获取位置";
  }

  const latestAssistantWithRestaurants = [...messages]
    .reverse()
    .find(
      (message) =>
        message.role === "assistant" && message.restaurants !== undefined,
    ) as PersistedChatMessage | undefined;
  const latestRestaurants = latestAssistantWithRestaurants?.restaurants ?? [];
  const hasRecommendation = Boolean(latestAssistantWithRestaurants);
  const hasMapRestaurants = latestRestaurants.length > 0;

  useEffect(() => {
    setFavoritedPoiIds(new Set());
    setFavoriteLoadingPoiId(null);
    setNotice(null);
    setMapOpen(false);
    setSelectedPoiId(null);
    setFavoriteTarget(null);
    setSelectedFavoriteCollectionId(null);
    setOpeningPoiId(null);
  }, [userId, sessionId]);

  useEffect(() => {
    if (!favoriteTarget) return;

    const collections = favoriteCollectionsQuery.data ?? [];
    if (collections.length === 0) {
      setSelectedFavoriteCollectionId(null);
      return;
    }

    const selectedExists = collections.some(
      (collection) => collection.id === selectedFavoriteCollectionId,
    );
    if (selectedExists) return;

    const defaultCollection =
      collections.find((collection) => collection.is_default) ?? collections[0];
    setSelectedFavoriteCollectionId(defaultCollection.id);
  }, [
    favoriteCollectionsQuery.data,
    favoriteTarget,
    selectedFavoriteCollectionId,
  ]);

  useEffect(() => {
    if (
      selectedPoiId &&
      !latestRestaurants.some((restaurant) => restaurant.poi_id === selectedPoiId)
    ) {
      setSelectedPoiId(null);
    }
  }, [latestRestaurants, selectedPoiId]);

  useEffect(() => {
    if (!hasMapRestaurants && mapOpen) {
      setMapOpen(false);
    }
  }, [hasMapRestaurants, mapOpen]);

  return (
    <AppShell>
      <div className="flex min-h-[620px] flex-col xl:h-[calc(100vh-120px)] xl:overflow-hidden">
        <div className="mb-5 flex shrink-0 flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">智能美食推荐</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              告诉我你的位置、想吃的菜系、预算和用餐场景，我会结合你的饮食记忆进行推荐。
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={chatMutation.isPending}
              onClick={handleReroll}
            >
              换一批
            </Button>
            <Button type="button" variant="secondary" onClick={handleNewSession}>
              新会话
            </Button>
          </div>
        </div>
        {notice ? (
          <div className="mb-5 shrink-0 rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-700 shadow-sm">
            {notice}
          </div>
        ) : null}
        <div className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[minmax(0,1fr)_520px]">
          <div className="flex min-h-[620px] flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-soft xl:sticky xl:top-6 xl:h-full xl:min-h-0">
            <ChatWindow
              messages={messages as ChatMessage[]}
              loading={chatMutation.isPending}
              onQuickReply={handleSend}
              onRequestLocation={handleRequestLocation}
            />
            <ChatInput
              disabled={chatMutation.isPending}
              locationStatusText={getLocationStatusText()}
              locating={browserLocation.loading || locationPermission === "requesting"}
              hasLocation={Boolean(currentLocation)}
              onRequestLocation={handleRequestLocation}
              onClearLocation={handleClearLocation}
              onSend={handleSend}
            />
          </div>
          <div className="min-h-0 xl:h-full xl:overflow-hidden">
            <RecommendationPanel
              restaurants={latestRestaurants}
              selectedPoiId={selectedPoiId}
              onSelectRestaurant={setSelectedPoiId}
              hasRecommendation={hasRecommendation}
              loading={chatMutation.isPending}
              favoritedPoiIds={favoritedPoiIds}
              favoriteLoadingPoiId={favoriteLoadingPoiId}
              onFavorite={handleFavorite}
              onOpenRestaurant={handleOpenRestaurant}
              openingPoiId={openingPoiId}
            />
          </div>
        </div>
      </div>

      {mapOpen ? (
        <div className="fixed bottom-24 right-4 z-50 flex h-[420px] w-[calc(100vw-32px)] flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-2xl sm:right-6 sm:w-[520px]">
          <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-4 py-3">
            <div>
              <h2 className="text-base font-semibold tracking-tight">附近地图</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                点击标记查看餐厅位置
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setMapOpen(false)}
            >
              关闭
            </Button>
          </div>
          <div className="min-h-0 flex-1">
            <RestaurantMap
              restaurants={latestRestaurants}
              userLocation={currentLocation}
              selectedPoiId={selectedPoiId}
              onSelectRestaurant={setSelectedPoiId}
            />
          </div>
        </div>
      ) : null}

      <Button
        type="button"
        disabled={!hasMapRestaurants}
        className="fixed bottom-6 right-6 z-50 rounded-full bg-black px-5 text-white shadow-lg transition-all hover:scale-[1.03] hover:bg-black hover:shadow-2xl"
        onClick={() => setMapOpen((current) => !current)}
      >
        {hasMapRestaurants ? "查看地图" : "暂无地图"}
      </Button>

      {favoriteTarget ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/30 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-3xl border border-border bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">
                  选择收藏夹
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  将“{favoriteTarget.name}”加入到你选择的收藏夹。
                </p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={Boolean(favoriteLoadingPoiId)}
                onClick={() => setFavoriteTarget(null)}
              >
                关闭
              </Button>
            </div>

            <div className="mt-5 space-y-3">
              {favoriteCollectionsQuery.isLoading ? (
                <ModalStateText>正在加载收藏夹...</ModalStateText>
              ) : null}

              {favoriteCollectionsQuery.error instanceof Error ? (
                <ModalStateText>收藏夹加载失败，请检查后端服务。</ModalStateText>
              ) : null}

              {!favoriteCollectionsQuery.isLoading &&
              !favoriteCollectionsQuery.error &&
              (favoriteCollectionsQuery.data ?? []).length === 0 ? (
                <ModalStateText>
                  还没有收藏夹，可以先到“我的收藏”页面创建收藏夹。
                </ModalStateText>
              ) : null}

              {(favoriteCollectionsQuery.data ?? []).map(
                (collection: FavoriteCollection) => (
                  <button
                    key={collection.id}
                    type="button"
                    disabled={Boolean(favoriteLoadingPoiId)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition-all ${
                      selectedFavoriteCollectionId === collection.id
                        ? "border-black bg-neutral-50 shadow-sm"
                        : "border-neutral-200 bg-white hover:bg-neutral-50"
                    }`}
                    onClick={() => setSelectedFavoriteCollectionId(collection.id)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="min-w-0 truncate text-sm font-semibold">
                        {collection.name}
                      </span>
                      {collection.is_default ? (
                        <span className="shrink-0 rounded-full bg-black px-2.5 py-1 text-xs text-white">
                          默认收藏夹
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      共 {collection.restaurant_count} 家餐厅
                    </p>
                    {collection.description ? (
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                        {collection.description}
                      </p>
                    ) : null}
                  </button>
                ),
              )}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={Boolean(favoriteLoadingPoiId)}
                onClick={() => setFavoriteTarget(null)}
              >
                取消
              </Button>
              <Button
                type="button"
                disabled={
                  Boolean(favoriteLoadingPoiId) ||
                  selectedFavoriteCollectionId == null ||
                  favoriteCollectionsQuery.isLoading
                }
                onClick={handleConfirmFavorite}
              >
                {favoriteLoadingPoiId ? "收藏中..." : "确认收藏"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}

function ModalStateText({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm leading-6 text-muted-foreground">
      {children}
    </div>
  );
}
