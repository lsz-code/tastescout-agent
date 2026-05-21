"use client";

import { RestaurantCard } from "@/components/restaurants/restaurant-card";
import { Card, CardContent } from "@/components/ui/card";
import { RestaurantItem } from "@/lib/api-types";
import { ChatMessage, MessageBubble } from "./message-bubble";

export function ChatWindow({
  messages,
  loading,
  onQuickReply,
  onRequestLocation,
}: {
  messages: ChatMessage[];
  loading?: boolean;
  onQuickReply?: (text: string) => void;
  onRequestLocation?: () => void;
}) {
  return (
    <Card className="flex min-h-0 flex-1 flex-col rounded-none border-0 p-5 shadow-none">
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <div className="flex h-full min-h-80 items-center justify-center text-center">
            <div>
              <h2 className="text-xl font-semibold tracking-tight">
                开始你的第一次美食推荐吧。
              </h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                你可以告诉我位置、菜系、预算和用餐场景，我会结合记忆和评分为你筛选。
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onQuickReply={onQuickReply}
              onRequestLocation={onRequestLocation}
            />
          ))
        )}
        {loading ? (
          <div className="rounded-2xl border border-border bg-white px-4 py-3 text-sm text-muted-foreground">
            正在结合位置、记忆和评分为你筛选餐厅...
          </div>
        ) : null}
      </div>
    </Card>
  );
}

export function RecommendationPanel({
  restaurants,
  selectedPoiId,
  onSelectRestaurant,
  hasRecommendation,
  loading,
  favoritedPoiIds,
  favoriteLoadingPoiId,
  onFavorite,
  onOpenRestaurant,
  openingPoiId,
}: {
  restaurants?: RestaurantItem[];
  selectedPoiId?: string | null;
  onSelectRestaurant?: (poiId: string) => void;
  hasRecommendation?: boolean;
  loading?: boolean;
  favoritedPoiIds?: Set<string>;
  favoriteLoadingPoiId?: string | null;
  onFavorite?: (restaurant: RestaurantItem) => Promise<void> | void;
  onOpenRestaurant?: (restaurant: RestaurantItem) => Promise<void> | void;
  openingPoiId?: string | null;
}) {
  const restaurantItems = restaurants ?? [];

  return (
    <Card className="flex h-full min-h-0 flex-col p-5">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">本次推荐结果</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {restaurantItems.length > 0
              ? `共找到 ${restaurantItems.length} 家餐厅，点击卡片可在地图中定位。`
              : "最近一次推荐会显示在这里，方便你对比选择。"}
          </p>
        </div>

        <div className="mt-5 min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
          {loading ? (
            <Card className="shadow-none">
              <CardContent className="pt-5 text-sm text-muted-foreground">
                正在结合位置、记忆和评分为你筛选餐厅...
              </CardContent>
            </Card>
          ) : null}

          {!loading && !hasRecommendation ? (
            <Card className="shadow-none">
              <CardContent className="pt-5 text-sm leading-6 text-muted-foreground">
                暂无推荐结果，先和我说说你想吃什么。
              </CardContent>
            </Card>
          ) : null}

          {!loading && hasRecommendation && restaurantItems.length === 0 ? (
            <Card className="shadow-none">
              <CardContent className="pt-5 text-sm leading-6 text-muted-foreground">
                这附近暂时没有更多新的推荐了，可以换个关键词或扩大搜索范围。
              </CardContent>
            </Card>
          ) : null}

          {restaurantItems.map((restaurant) => (
            <RestaurantCard
              key={restaurant.poi_id || `${restaurant.rank}-${restaurant.name}`}
              restaurant={restaurant}
              selected={selectedPoiId === restaurant.poi_id}
              onClick={() => {
                onSelectRestaurant?.(restaurant.poi_id);
                onOpenRestaurant?.(restaurant);
              }}
              showFavoriteButton
              onFavorite={() => onFavorite?.(restaurant)}
              isFavorited={favoritedPoiIds?.has(restaurant.poi_id)}
              favoriteLoading={
                favoriteLoadingPoiId === restaurant.poi_id ||
                openingPoiId === restaurant.poi_id
              }
            />
          ))}
        </div>
      </Card>
  );
}
