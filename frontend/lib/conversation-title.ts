import { PersistedChatMessage } from "@/stores/chat-store";

const cuisines = [
  "川菜",
  "火锅",
  "烧烤",
  "日料",
  "粤菜",
  "湘菜",
  "韩餐",
  "西餐",
  "意大利菜",
  "泰国菜",
  "奶茶",
  "甜品",
  "咖啡",
];

const scenes = [
  "朋友聚餐",
  "约会",
  "一人食",
  "家庭聚餐",
  "商务宴请",
  "夜宵",
  "午餐",
  "晚餐",
  "拍照",
  "安静",
  "加班",
];

function compactText(text: string) {
  return text.replace(/\s+/g, " ").trim();
}

export function buildConversationTitle(messages: PersistedChatMessage[]) {
  const userMessages = messages.filter((message) => message.role === "user");
  const text = compactText(userMessages.map((message) => message.content).join(" "));
  const cuisine = cuisines.find((item) => text.includes(item));
  const scene = scenes.find((item) => text.includes(item));

  if (cuisine && scene) return `${cuisine} · ${scene}`;
  if (cuisine) return `${cuisine}推荐`;
  if (scene) return `${scene}推荐`;

  const firstUserMessage = compactText(userMessages[0]?.content ?? "");
  if (firstUserMessage) {
    return firstUserMessage.length > 18
      ? `${firstUserMessage.slice(0, 18)}...`
      : firstUserMessage;
  }

  const firstAssistantMessage = compactText(messages[0]?.content ?? "");
  if (firstAssistantMessage) {
    return firstAssistantMessage.length > 18
      ? `${firstAssistantMessage.slice(0, 18)}...`
      : firstAssistantMessage;
  }

  return "新的美食对话";
}

export function getConversationUpdatedAt(messages: PersistedChatMessage[]) {
  return messages[messages.length - 1]?.createdAt ?? new Date(0).toISOString();
}
