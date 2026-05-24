import { Heart, MapPin, Star, Wallet } from "lucide-react";
import { FavoriteRestaurant, RestaurantItem } from "@/lib/api-types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function formatDistance(distance?: number | null) {
  if (distance == null) return "距离未知";
  if (distance >= 1000) return `${(distance / 1000).toFixed(1)}km`;
  return `${Math.round(distance)}m`;
}

function formatPrice(price?: number | null) {
  if (price == null) return "价格未知";
  return `人均 ¥${Math.round(price)}`;
}

function normalizeReason(reason: string) {
  const text = reason
    .replace(/^推荐原因[:：]\s*/u, "")
    .replace(/^推荐理由[:：]\s*/u, "")
    .trim();

  if (text.includes("距离") && text.includes("近")) return "距离优雅";
  if (text.includes("评分") && text.includes("高")) return "评分优秀";
  if (text.includes("价格") || text.includes("人均")) return "价格合适";
  if (text.includes("聚餐")) return "适合聚餐";
  if (text.includes("偏好") || text.includes("口味")) return "匹配口味";
  return text.replace(/[。；;]$/u, "");
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
  const matchReasons = "match_reasons" in restaurant ? restaurant.match_reasons : [];
  const chips = Array.from(
    new Set((matchReasons ?? []).map(normalizeReason).filter(Boolean)),
  ).slice(0, compact ? 3 : 4);

  return (
    <article
      className={cn(
        "group overflow-hidden rounded-[20px] border border-orange-100 bg-white shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md",
        selected && "border-orange-300 shadow-lg shadow-orange-100",
        onClick && "cursor-pointer",
        compact ? "grid h-[174px] grid-cols-[42%_1fr]" : "flex flex-col",
      )}
      onClick={onClick}
    >
      <div
        className={cn(
          "relative overflow-hidden bg-orange-50",
          compact ? "h-full" : "h-[190px]",
        )}
      >
        <div className="absolute inset-0 flex items-center justify-center text-4xl">
          🍽️
        </div>
        {restaurant.photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={restaurant.photo}
            alt={restaurant.name}
            className="relative h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            onError={(event) => {
              event.currentTarget.style.display = "none";
            }}
          />
        ) : null}
        {rank != null && !compact ? (
          <span className="absolute left-3 top-3 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-orange-600 shadow-sm">
            #{rank} 推荐
          </span>
        ) : null}
      </div>

      <div className={cn("min-w-0 p-4", compact && "py-4")}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3
              className={cn(
                "line-clamp-1 font-bold tracking-tight text-amber-950",
                compact ? "text-lg" : "text-xl",
              )}
            >
              {restaurant.name}
            </h3>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Star className="h-3.5 w-3.5 fill-orange-400 text-orange-400" />
                {restaurant.rating != null ? restaurant.rating : "暂无评分"}
              </span>
              <span>{formatPrice(restaurant.avg_price)}</span>
              {restaurant.cuisine_type ? <span>{restaurant.cuisine_type}</span> : null}
            </div>
          </div>

          {showFavoriteButton ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={favoriteLoading}
              aria-label={isFavorited ? "已收藏" : "收藏"}
              className="h-9 w-9 shrink-0 rounded-full text-orange-500 hover:bg-orange-50"
              onClick={(event) => {
                event.stopPropagation();
                onFavorite?.(restaurant);
              }}
            >
              <Heart
                className={cn(
                  "h-5 w-5",
                  isFavorited && "fill-red-500 text-red-500",
                )}
              />
            </Button>
          ) : null}
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5" />
            <span className="line-clamp-1">{restaurant.address ?? "暂无地址"}</span>
          </span>
          {!compact ? (
            <span className="inline-flex items-center gap-1">
              <Wallet className="h-3.5 w-3.5" />
              {formatDistance(restaurant.distance)}
            </span>
          ) : null}
        </div>

        {chips.length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {chips.map((reason) => (
              <span
                key={reason}
                className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-700"
              >
                {reason}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}
