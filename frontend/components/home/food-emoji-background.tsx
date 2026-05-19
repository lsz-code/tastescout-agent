const rows = [
  [
    "🍜 吃拉面",
    "🍙 饭团猫",
    "🧋 奶茶熊",
    "🥢 小兔开饭",
    "🍲 火锅狗",
    "🍣 寿司狐",
    "🍰 蛋糕团子",
    "🍔 汉堡鸭",
  ],
  [
    "🍣 寿司狐",
    "🍰 蛋糕团子",
    "🍔 汉堡鸭",
    "🍜 吃拉面",
    "🍙 饭团猫",
    "🥢 小兔开饭",
    "🧋 奶茶熊",
    "🍲 火锅狗",
  ],
  [
    "🧋 奶茶熊",
    "🍲 火锅狗",
    "🍙 饭团猫",
    "🍣 寿司狐",
    "🍔 汉堡鸭",
    "🍜 吃拉面",
    "🍰 蛋糕团子",
    "🥢 小兔开饭",
  ],
];

function FoodRow({
  items,
  direction,
}: {
  items: string[];
  direction: "left" | "right";
}) {
  const doubled = [...items, ...items];

  return (
    <div className="relative flex w-[200%] gap-4">
      <div
        className={
          direction === "left"
            ? "food-marquee-left flex min-w-[50%] gap-4"
            : "food-marquee-right flex min-w-[50%] gap-4"
        }
      >
        {doubled.map((item, index) => (
          <span
            key={`${item}-${index}`}
            className="whitespace-nowrap rounded-full border border-neutral-200 bg-white/80 px-5 py-3 text-sm text-neutral-700 shadow-sm backdrop-blur"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

export function FoodEmojiBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden opacity-70">
      <div className="absolute inset-x-[-12%] top-14 space-y-7 rotate-[-6deg]">
        {rows.map((row, index) => (
          <FoodRow
            key={index}
            items={row}
            direction={index % 2 === 0 ? "left" : "right"}
          />
        ))}
      </div>
      <div className="absolute inset-x-[-12%] bottom-10 space-y-7 rotate-[5deg]">
        {rows.map((row, index) => (
          <FoodRow
            key={`bottom-${index}`}
            items={row}
            direction={index % 2 === 0 ? "right" : "left"}
          />
        ))}
      </div>
    </div>
  );
}
