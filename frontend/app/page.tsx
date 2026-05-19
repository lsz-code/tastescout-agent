import { ArrowRight, Brain, MapPinned, Route, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FoodEmojiBackground } from "@/components/home/food-emoji-background";

const features = [
  { label: "地图搜索", description: "通过后端业务服务调用高德 MCP", icon: MapPinned },
  { label: "饮食记忆", description: "结合短期会话和长期偏好", icon: Brain },
  { label: "推荐排序", description: "综合距离、评分、价格和口味", icon: SlidersHorizontal },
  { label: "工作流", description: "使用 LangGraph 编排 Agent", icon: Route },
];

export default function HomePage() {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-neutral-50 px-6 py-8">
      <FoodEmojiBackground />
      <section className="relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col justify-center">
        <div className="mx-auto max-w-3xl rounded-[2rem] border border-white/70 bg-white/85 px-8 py-10 text-center shadow-soft backdrop-blur md:px-14 md:py-14">
          <p className="mb-4 text-sm font-medium text-muted-foreground">
            连接后端工作流的智能美食助手
          </p>
          <h1 className="text-5xl font-semibold tracking-tight text-foreground md:text-7xl">
            等会吃什么呢？
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
            一个会记住你口味的智能美食推荐助手。
          </p>
          <div className="mt-8 flex justify-center">
            <Link href="/chat">
              <Button>
                开始找饭
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>

        <div className="mt-16 grid gap-4 md:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Card key={feature.label} className="shadow-soft">
                <CardContent className="pt-5">
                  <Icon className="mb-5 h-5 w-5 text-muted-foreground" />
                  <h2 className="font-semibold">{feature.label}</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>
    </main>
  );
}
