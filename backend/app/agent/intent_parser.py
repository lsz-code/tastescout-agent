import re
from typing import Any


class IntentParser:
    FAVORITE_RANK_PATTERN = re.compile(r"收藏第\s*([0-9一二三四五六七八九十]+)\s*家")
    SHOP_SEARCH_PATTERN = re.compile(
        r"(?:找找|找一下|搜一下|搜索|帮我找|有没有|查一下|看看|想找)([^，,。！？!?]+?(?:店|餐厅|饭店|酒馆|火锅|烧烤|奶茶|咖啡|面馆|小馆|食堂|酒吧|居酒屋))"
    )
    GENERIC_SHOP_SEARCH_PATTERN = re.compile(
        r"(?:找找|找一下|搜一下|搜索|帮我找|有没有|查一下|看看|想找)([^，,。！？!?]{2,30})"
    )

    CN_NUMBERS = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }

    def parse(
        self,
        message: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        normalized = message.strip()

        if self._is_casual_chat(normalized):
            return {
                "tool_name": "casual_chat",
                "arguments": {},
            }

        if self._contains_any(normalized, ["收藏夹", "我收藏"]):
            return {
                "tool_name": "show_favorites",
                "arguments": {"user_id": user_id},
            }

        if self._contains_any(normalized, ["偏好", "记忆", "口味"]):
            return {
                "tool_name": "get_user_memory",
                "arguments": {"user_id": user_id},
            }

        if self._contains_any(normalized, ["收藏第", "加入收藏"]):
            return {
                "tool_name": "add_favorite_by_rank",
                "arguments": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "rank": self._extract_rank(normalized) or 1,
                },
            }

        if self._contains_any(
            normalized,
            [
                "再推荐几家",
                "换几家",
                "还有别的吗",
                "还有别的么",
                "还有其他的吗",
                "有没有其他的",
                "不想吃这些",
                "再来几个",
                "再推荐一些别的",
                "重新推荐",
                "换一批",
                "推荐个吃饭的地方",
                "我想吃饭",
                "随便推荐",
                "找个餐厅",
                "找家店",
                "找店",
                "想吃点东西",
                "附近",
                "周边",
                "好吃",
                "美食",
                "推荐",
                "餐厅",
                "饭店",
                "酒馆",
                "奶茶",
                "夜宵",
                "川菜",
                "火锅",
                "烧烤",
                "日料",
            ],
        ) or self._is_shop_search(normalized):
            return {
                "tool_name": "search_restaurants",
                "arguments": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "keyword": normalized,
                    "limit": 5,
                },
            }

        return None

    @classmethod
    def _is_shop_search(cls, message: str) -> bool:
        if cls.SHOP_SEARCH_PATTERN.search(message) or message.endswith(
            ("在哪", "在哪里", "在哪儿")
        ):
            return True
        match = cls.GENERIC_SHOP_SEARCH_PATTERN.search(message)
        if not match:
            return False
        candidate = match.group(1).strip()
        return candidate not in {"餐厅", "饭店", "吃的", "好吃的", "美食", "吃饭的地方"}

    @staticmethod
    def _is_casual_chat(message: str) -> bool:
        if not message:
            return False

        search_keywords = [
            "附近",
            "周边",
            "推荐",
            "找",
            "搜",
            "餐厅",
            "饭店",
            "酒馆",
            "奶茶",
            "夜宵",
            "火锅",
            "烧烤",
            "川菜",
        ]
        casual_phrases = [
            "哈哈",
            "我饿疯了",
            "今天不想动",
            "张嘴喂我",
            "选择困难症犯了",
            "你觉得我该吃啥",
            "好事全让我赶上了",
            "我染上吃饭了",
            "太难选了",
            "随便聊聊",
            "你真懂我",
            "累死了",
            "不想出门",
            "今天好烦",
            "想吃点开心的",
            "需要一点安慰",
        ]
        #如果没有说帮助找什么餐厅或者其他工具相关的关键词，但说了一些比较随意的话，就认为这是在进行闲聊
        if any(phrase in message for phrase in casual_phrases):
            return not any(keyword in message for keyword in search_keywords)

        return False

    def _extract_rank(self, message: str) -> int | None:
        match = self.FAVORITE_RANK_PATTERN.search(message)
        if not match:
            return None

        raw_rank = match.group(1)
        if raw_rank.isdigit():
            return int(raw_rank)

        return self.CN_NUMBERS.get(raw_rank)

    @staticmethod
    def _contains_any(message: str, keywords: list[str]) -> bool:
        return any(keyword in message for keyword in keywords)
