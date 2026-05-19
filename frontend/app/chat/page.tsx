"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
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
  refreshLongTermMemory,
  sendAgentMessage,
} from "@/lib/api-client";
import { useBrowserLocation } from "@/hooks/use-browser-location";
import {
  AddFavoriteRequest,
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

  const chatMutation = useMutation({
    mutationFn: sendAgentMessage,
    onSuccess: (response) => {
      appendMessage(userId, sessionId, {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        createdAt: new Date().toISOString(),
        restaurants: response.data?.needs_followup
          ? undefined
          : response.data?.restaurants ?? [],
        toolCalls: response.tool_calls,
        needsFollowup: Boolean(response.data?.needs_followup),
        missingSlots: Array.isArray(response.data?.missing_slots)
          ? (response.data?.missing_slots as string[])
          : undefined,
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
    newSession();
  }

  async function handleFavorite(restaurant: RestaurantItem) {
    if (!restaurant.poi_id || favoriteLoadingPoiId) return;

    setNotice(null);
    setFavoriteLoadingPoiId(restaurant.poi_id);

    const payload: AddFavoriteRequest = {
      user_id: userId,
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
      setNotice(
        response.already_exists
          ? "这家餐厅已经在收藏夹里了"
          : `已收藏：${restaurant.name}`,
      );

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
  }, [userId, sessionId]);

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
    </AppShell>
  );
}
