import re
from typing import Any


class IntentParser:
    FAVORITE_RANK_PATTERN = re.compile(r"收藏第\s*([0-9一二三四五六七八九十]+)\s*家")

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
                "不想吃这些",
                "再来几个",
                "重新推荐",
                "换一批",
                "推荐个吃饭的地方",
                "我想吃饭",
                "吃什么",
                "随便推荐",
                "找个餐厅",
                "想吃点东西",
                "附近",
                "周边",
                "好吃",
                "美食",
                "吃什么",
                "推荐",
                "餐厅",
                "饭店",
                "川菜",
                "火锅",
                "烧烤",
                "日料",
            ],
        ):
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
