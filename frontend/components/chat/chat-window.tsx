"use client";

import { ReactNode } from "react";
import { Filter, Heart, MapPin, Star } from "lucide-react";
import { RestaurantCard } from "@/components/restaurants/restaurant-card";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (
          <div className="flex h-full min-h-80 items-center justify-center text-center">
            <div className="max-w-md">
              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-orange-50 text-4xl shadow-inner">
                🧑‍🍳
              </div>
              <h2 className="text-2xl font-bold tracking-tight">
                今天想吃点什么？
              </h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                告诉我你的口味、心情或忌口，我来帮你推荐餐厅吧～
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
          <div className="inline-flex rounded-2xl border border-orange-100 bg-white px-4 py-3 text-sm text-muted-foreground shadow-sm">
            正在结合位置、记忆和评分为你筛选餐厅...
          </div>
        ) : null}
      </div>
    </div>
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
    <Card className="warm-panel flex h-full min-h-0 max-h-full flex-col overflow-hidden rounded-[22px] p-4 shadow-none">
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <div>
          <h2 className="text-xl font-bold tracking-tight">为你推荐</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {restaurantItems.length > 0
              ? `${restaurantItems.length} 家餐厅`
              : "推荐结果会显示在这里"}
          </p>
        </div>
        <Button variant="secondary" size="sm" className="rounded-full">
          <Filter className="h-4 w-4" />
          筛选
        </Button>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {loading ? (
          <Card className="border-orange-100 shadow-none">
            <CardContent className="pt-5 text-sm text-muted-foreground">
              正在结合位置、记忆和评分为你筛选餐厅...
            </CardContent>
          </Card>
        ) : null}

        {!loading && !hasRecommendation ? (
          <EmptyPanelText>
            先和我说说你想吃什么，我会把推荐餐厅放在这里。
          </EmptyPanelText>
        ) : null}

        {!loading && hasRecommendation && restaurantItems.length === 0 ? (
          <EmptyPanelText>
            这附近暂时没有更多新的推荐了，可以换个关键词或扩大搜索范围。
          </EmptyPanelText>
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
            compact
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

      {restaurantItems.length > 0 ? (
        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <span className="h-px w-10 bg-orange-100" />
          上拉加载更多
          <span className="h-px w-10 bg-orange-100" />
        </div>
      ) : null}
    </Card>
  );
}

function EmptyPanelText({ children }: { children: ReactNode }) {
  return (
    <Card className="border-orange-100 bg-white/80 shadow-none">
      <CardContent className="space-y-3 pt-5 text-sm leading-6 text-muted-foreground">
        <div className="flex items-center gap-2 text-amber-800">
          <Star className="h-4 w-4 text-orange-400" />
          <span className="font-medium">等待你的偏好</span>
        </div>
        <p>{children}</p>
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-3 py-1 text-xs text-orange-700">
            <MapPin className="h-3 w-3" />
            附近
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-700">
            <Heart className="h-3 w-3" />
            口味偏好
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
