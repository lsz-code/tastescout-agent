"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, MapPin, MessageCircle, Star, Wallet } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { getRestaurantDetail, submitRestaurantReview } from "@/lib/api-client";
import { useUserStore } from "@/stores/user-store";

function formatPrice(price?: number | null) {
  if (price == null) return "价格未知";
  return `¥${Math.round(price)}/人`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function RestaurantDetailPage() {
  const params = useParams<{ poiId: string }>();
  const poiId = Array.isArray(params.poiId) ? params.poiId[0] : params.poiId;
  const decodedPoiId = decodeURIComponent(poiId ?? "");
  const userId = useUserStore((state) => state.userId);
  const queryClient = useQueryClient();
  const [content, setContent] = useState("");
  const [rating, setRating] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ["restaurant-detail", decodedPoiId],
    queryFn: () => getRestaurantDetail(decodedPoiId),
    enabled: Boolean(decodedPoiId),
  });

  const currentUserReview = useMemo(
    () =>
      detailQuery.data?.reviews.find((review) => review.user_id === userId) ??
      null,
    [detailQuery.data?.reviews, userId],
  );

  const reviewMutation = useMutation({
    mutationFn: () =>
      submitRestaurantReview(decodedPoiId, {
        user_id: userId,
        content,
        rating: rating ? Number(rating) : null,
      }),
    onSuccess: async () => {
      setNotice(currentUserReview ? "评论已更新" : "评论已发布");
      setContent("");
      setRating("");
      await queryClient.invalidateQueries({
        queryKey: ["restaurant-detail", decodedPoiId],
      });
    },
    onError: () => {
      setNotice("评论保存失败，请稍后再试。");
    },
  });

  function handleSubmitReview() {
    const trimmed = content.trim();
    if (!trimmed) {
      setNotice("请先写下你的评论。");
      return;
    }

    const ratingValue = rating ? Number(rating) : null;
    if (ratingValue != null && (ratingValue < 1 || ratingValue > 5)) {
      setNotice("评分需要在 1 到 5 分之间。");
      return;
    }

    setNotice(null);
    reviewMutation.mutate();
  }

  const restaurant = detailQuery.data;

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition hover:text-neutral-950"
        >
          <ArrowLeft className="h-4 w-4" />
          返回智能推荐
        </Link>

        {detailQuery.isLoading ? (
          <Card className="rounded-3xl">
            <CardContent className="p-6 text-sm text-muted-foreground">
              正在加载餐厅详情...
            </CardContent>
          </Card>
        ) : null}

        {detailQuery.error ? (
          <Card className="rounded-3xl">
            <CardContent className="space-y-3 p-6">
              <h1 className="text-xl font-semibold">餐厅详情加载失败</h1>
              <p className="text-sm text-muted-foreground">
                这家餐厅还没有保存到系统中，可以先从智能推荐结果进入详情页。
              </p>
            </CardContent>
          </Card>
        ) : null}

        {restaurant ? (
          <>
            <Card className="overflow-hidden rounded-3xl">
              <div className="relative h-64 bg-neutral-100 sm:h-80">
                <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
                  暂无图片
                </div>
                {restaurant.photo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={restaurant.photo}
                    alt={restaurant.name}
                    className="relative h-full w-full object-cover"
                    onError={(event) => {
                      event.currentTarget.style.display = "none";
                    }}
                  />
                ) : null}
              </div>
              <CardContent className="p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h1 className="text-3xl font-bold tracking-tight text-neutral-950">
                      {restaurant.name}
                    </h1>
                    {restaurant.cuisine_type ? (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {restaurant.cuisine_type}
                      </p>
                    ) : null}
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-4 text-sm text-neutral-600">
                  <span className="inline-flex items-center gap-1.5">
                    <Star className="h-4 w-4 text-neutral-400" />
                    {restaurant.rating ?? "暂无评分"}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Wallet className="h-4 w-4 text-neutral-400" />
                    {formatPrice(restaurant.avg_price)}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="h-4 w-4 text-neutral-400" />
                    {restaurant.address ?? "暂无地址"}
                  </span>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
              <Card className="rounded-3xl">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h2 className="text-xl font-semibold tracking-tight">
                        用户评论
                      </h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        来自 TasteScout 用户的真实体验。
                      </p>
                    </div>
                    <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-500">
                      共 {restaurant.reviews.length} 条
                    </span>
                  </div>

                  <div className="mt-6 space-y-4">
                    {restaurant.reviews.length === 0 ? (
                      <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-5 text-sm text-muted-foreground">
                        还没有评论，来写下第一条体验吧。
                      </div>
                    ) : null}

                    {restaurant.reviews.map((review) => (
                      <div
                        key={review.id}
                        className="rounded-2xl border border-neutral-200 bg-white p-4"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="font-medium text-neutral-950">
                              {review.username || review.user_id}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {formatDate(review.updated_at)}
                            </p>
                          </div>
                          {review.rating ? (
                            <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">
                              {review.rating} 分
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-neutral-700">
                          {review.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="h-fit rounded-3xl">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <MessageCircle className="h-5 w-5 text-neutral-500" />
                    <h2 className="text-lg font-semibold tracking-tight">
                      写评论
                    </h2>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    每位用户对同一家餐厅保留一条评论，再次提交会更新原评论。
                  </p>

                  {currentUserReview ? (
                    <div className="mt-4 rounded-2xl bg-neutral-50 px-4 py-3 text-xs leading-5 text-muted-foreground">
                      你已经评论过这家餐厅，本次提交会更新之前的内容。
                    </div>
                  ) : null}

                  <div className="mt-5 space-y-3">
                    <Input
                      type="number"
                      min={1}
                      max={5}
                      step={0.5}
                      value={rating}
                      onChange={(event) => setRating(event.target.value)}
                      placeholder="评分，可选，例如 4.5"
                    />
                    <Textarea
                      value={content}
                      onChange={(event) => setContent(event.target.value)}
                      placeholder="写下你的口味、环境、服务或适合的用餐场景..."
                    />
                  </div>

                  {notice ? (
                    <div className="mt-4 rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-700">
                      {notice}
                    </div>
                  ) : null}

                  <Button
                    type="button"
                    className="mt-5 w-full"
                    disabled={reviewMutation.isPending}
                    onClick={handleSubmitReview}
                  >
                    {reviewMutation.isPending ? "正在保存..." : "发布评论"}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
