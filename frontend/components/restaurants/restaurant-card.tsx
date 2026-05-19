import { Heart, MapPin, Star, Wallet } from "lucide-react";
import { FavoriteRestaurant, RestaurantItem } from "@/lib/api-types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function formatDistance(distance?: number | null) {
  if (distance == null) return "距离未知";
  if (distance >= 1000) return `距离 ${(distance / 1000).toFixed(1)}km`;
  return `距离 ${Math.round(distance)}m`;
}

function formatPrice(price?: number | null) {
  if (price == null) return "价格未知";
  return `¥${Math.round(price)}/人`;
}

function normalizeReason(reason: string) {
  const text = reason
    .replace(/^推荐原因[:：]\s*/u, "")
    .replace(/^推荐理由[:：]\s*/u, "")
    .trim();

  if (text.includes("距离") && text.includes("近")) return "距离近";
  if (text.includes("评分") && text.includes("高")) return "评分高";
  if (text.includes("价格") || text.includes("人均")) return "价格友好";
  if (text.includes("聚餐")) return "适合聚餐";
  if (text.includes("偏好") || text.includes("口味")) return "符合偏好";
  return text.replace(/[。；;]$/u, "");
}

function getRecommendationText({
  restaurant,
  matchReasons,
}: {
  restaurant: RestaurantItem | FavoriteRestaurant;
  matchReasons: string[];
}) {
  const explicitReason = restaurant.recommend_reason
    ?.replace(/^推荐原因[:：]\s*/u, "")
    .replace(/^推荐理由[:：]\s*/u, "")
    .replace(/推荐原因[:：]\s*/gu, "")
    .trim();

  if (explicitReason) {
    return explicitReason.length > 54
      ? `${explicitReason.slice(0, 54)}...`
      : explicitReason;
  }

  const distance = restaurant.distance;
  const rating = restaurant.rating;
  const price = restaurant.avg_price;
  const hasPartyReason = matchReasons.some((reason) => reason.includes("聚餐"));

  if (distance != null && distance <= 500) {
    return hasPartyReason
      ? "离你非常近，适合和朋友轻松聚餐。"
      : "离你非常近，适合现在就出发。";
  }

  if (rating != null && rating >= 4.5 && price != null) {
    return "评分不错，人均适中，适合作为稳妥选择。";
  }

  if (hasPartyReason) {
    return "环境和口味都比较适合朋友聚餐。";
  }

  if (restaurant.cuisine_type) {
    return `这家${restaurant.cuisine_type}匹配你的本次需求。`;
  }

  return "综合评分、距离和偏好后，这家值得优先看看。";
}

export function RestaurantCard({
  restaurant,
  compact = false,
  showFavoriteButton = false,
  onFavorite,
  favoriteLoading = false,
  isFavorited = false,
  selected = false,
  onClick,
}: {
  restaurant: RestaurantItem | FavoriteRestaurant;
  compact?: boolean;
  showFavoriteButton?: boolean;
  onFavorite?: (restaurant: RestaurantItem | FavoriteRestaurant) => Promise<void> | void;
  favoriteLoading?: boolean;
  isFavorited?: boolean;
  selected?: boolean;
  onClick?: () => void;
}) {
  const rank = "rank" in restaurant ? restaurant.rank : null;
  const score = "score" in restaurant ? restaurant.score : null;
  const matchReasons = "match_reasons" in restaurant ? restaurant.match_reasons : [];
  const chips = Array.from(
    new Set((matchReasons ?? []).map(normalizeReason).filter(Boolean)),
  ).slice(0, 3);
  const recommendationText = getRecommendationText({
    restaurant,
    matchReasons: matchReasons ?? [],
  });

  return (
    <Card
      className={cn(
        "overflow-hidden rounded-3xl border-neutral-200 bg-white shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg",
        selected && "scale-[1.01] border-black shadow-xl",
        onClick && "cursor-pointer",
      )}
      onClick={onClick}
    >
      <div className="flex h-full flex-col">
        <div className="relative h-[140px] overflow-hidden bg-neutral-100 sm:h-[180px]">
          <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
            暂无图片
          </div>
          {restaurant.photo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={restaurant.photo}
              alt={restaurant.name}
              className="relative h-full w-full object-cover transition-transform duration-500 hover:scale-[1.03]"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
            />
          ) : null}
          {rank != null ? (
            <span className="absolute left-4 top-4 rounded-full bg-black/70 px-3 py-1 text-sm font-medium text-white shadow-sm backdrop-blur">
              #{rank} 推荐
            </span>
          ) : null}
          {showFavoriteButton ? (
            <Button
              type="button"
              variant="secondary"
              size="icon"
              disabled={favoriteLoading}
              aria-label={isFavorited ? "已收藏" : "收藏"}
              className="absolute right-4 top-4 h-9 w-9 rounded-full bg-white/80 text-neutral-700 shadow-sm backdrop-blur transition-all hover:bg-white hover:shadow-md"
              onClick={(event) => {
                event.stopPropagation();
                onFavorite?.(restaurant);
              }}
            >
              <Heart
                className={cn(
                  "h-4 w-4",
                  isFavorited && "fill-red-500 text-red-500",
                )}
              />
            </Button>
          ) : null}
        </div>

        <CardContent className="flex flex-1 flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="line-clamp-2 text-xl font-bold leading-tight tracking-tight text-neutral-950 sm:text-2xl">
                {restaurant.name}
              </h3>
              {restaurant.cuisine_type ? (
                <p className="mt-1 text-xs text-neutral-400">
                  {restaurant.cuisine_type}
                </p>
              ) : null}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-neutral-500">
            <span className="inline-flex items-center gap-1.5">
              <Star className="h-4 w-4 text-neutral-400" />
              {restaurant.rating != null ? restaurant.rating : "暂无评分"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Wallet className="h-4 w-4 text-neutral-400" />
              {formatPrice(restaurant.avg_price)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-neutral-400" />
              {formatDistance(restaurant.distance)}
            </span>
          </div>

          <p className="mt-4 line-clamp-2 text-sm leading-6 text-neutral-600">
            {recommendationText}
          </p>

          {chips.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {chips.map((reason) => (
                <span
                  key={reason}
                  className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600"
                >
                  {reason}
                </span>
              ))}
            </div>
          ) : null}

          <div className="mt-auto pt-4">
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 truncate text-xs text-neutral-400">
                {restaurant.address ?? "暂无地址"}
              </p>
              {score != null ? (
                <span className="shrink-0 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-500">
                  推荐分 {Math.round(score)}
                </span>
              ) : null}
            </div>
          </div>
        </CardContent>
      </div>
    </Card>
  );
}
