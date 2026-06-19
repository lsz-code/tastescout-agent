from __future__ import annotations

import re
from typing import Any


class SlotExtractor:
    """基于规则的餐厅搜索槽位抽取器。"""

    CUISINES = [
        "川菜",
        "火锅",
        "烧烤",
        "日料",
        "粤菜",
        "广东菜",
        "潮汕菜",
        "湘菜",
        "东北菜",
        "韩餐",
        "西餐",
        "面馆",
        "小吃",
        "奶茶",
        "甜品",
    ]
    SCENES = [
        "朋友聚餐",
        "约会",
        "一人食",
        "家庭聚餐",
        "商务宴请",
        "夜宵",
        "下班",
        "午餐",
        "晚餐",
    ]
    GENERIC_KEYWORDS = {
        "美食",
        "餐厅",
        "饭店",
        "吃饭",
        "吃的",
        "好吃的",
        "吃点东西",
        "随便推荐",
    }

    def extract(
        self,
        message: str,
        short_term_memory: dict[str, Any] | None = None,
        request_location: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """从用户输入和短期记忆中提取搜索槽位。"""
        slots: dict[str, Any] = {}
        short_term_memory = short_term_memory or {}

        if request_location:
            slots["location"] = request_location
        elif self._contains_any(message, ["附近", "周边"]):
            memory_location = short_term_memory.get("current_location")
            if isinstance(memory_location, dict):
                slots["location"] = memory_location

        address = self._extract_address(message)
        if address:
            slots["address"] = address

        keyword = self._extract_search_keyword(message)
        cuisine = self._extract_first(message, self.CUISINES)

        if keyword:
            slots["keyword"] = keyword
            slots["search_query"] = keyword
            slots["search_type"] = "keyword"
        elif cuisine:
            slots["cuisine"] = cuisine
            slots["keyword"] = cuisine
            slots["search_query"] = cuisine
            slots["search_type"] = "cuisine"
        elif self._contains_any(message, list(self.GENERIC_KEYWORDS)):
            slots["keyword"] = "美食"
            slots["search_query"] = "美食"
            slots["search_type"] = "generic"

        budget = self._extract_budget(message)
        if budget is not None:
            slots["budget"] = budget

        scene = self._extract_first(message, self.SCENES)
        if scene:
            slots["scene"] = scene

        radius = self._extract_radius(message)
        if radius is not None:
            slots["radius"] = radius

        limit = self._extract_limit(message)
        if limit is not None:
            slots["limit"] = limit

        city = self._extract_city(message)
        if city:
            slots["city"] = city

        return slots

    @classmethod
    def _extract_search_keyword(cls, message: str) -> str | None:
        """提取用户明确想搜的店名、菜品名或关键词。"""
        patterns = [
            r"(?:附近|周边|范围内|公里内|km范围内|KM范围内)的?([^，。！？；,;]+?)(?:饭店|餐厅|店)?(?:$|[，。！？；,;])",
            r"(?:我要找的是|想找的是|找的是)(?:.*?(?:附近|周边)的?)?([^，。！？；,;]+?)(?:饭店|餐厅|店)?(?:$|[，。！？；,;])",
            r"(?:帮我找找|帮我找|找找|找一下|搜索|查一下|我想找|想找|找)(?:.*?(?:附近|周边)的?)?([^，。！？；,;]+?)(?:饭店|餐厅|店)?(?:$|[，。！？；,;])",
            r"(?:吃|想吃|要吃)([^，。！？；,;]+?)(?:$|[，。！？；,;])",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if not match:
                continue
            keyword = cls._clean_keyword(match.group(1))
            if keyword:
                return keyword
        return None

    @classmethod
    def _clean_keyword(cls, keyword: str) -> str:
        """清洗关键词中的位置、范围和泛化搜索词。"""
        text = keyword.strip()
        text = re.sub(r"^的", "", text).strip()
        text = re.sub(r"^(?:附近的|周边的|附近|周边)", "", text).strip()
        text = re.sub(r"^(?:哈尔滨|北京|上海|广州|深圳|成都|杭州|南京|武汉|西安|重庆|天津|海口)的", "", text).strip()
        text = re.sub(r"^(?:一家|一个|几家|几个)", "", text).strip()
        text = re.sub(r"(?:饭店|餐厅|店)$", "", text).strip()
        text = re.sub(r"^(?:有没有|有无|有没有专门做)", "", text).strip()

        if not text or text in cls.GENERIC_KEYWORDS:
            return ""
        if len(text) < 2 or len(text) > 30:
            return ""
        return text

    @staticmethod
    def _extract_address(message: str) -> str | None:
        """提取文本地址，主要用于 geocode 或附近搜索。"""
        patterns = [
            r"(?:我在|人在|当前位置在|位置在|地址是|在)([^，。！？；,;]+?)(?:附近|周边|这边|这里|$|[，。！？；,;])",
            r"(?:帮我找找|帮我找|找找|找一下|搜索|查一下)([^，。！？；,;]+?)[，,]\s*(?:半径|方圆|周边|附近|范围)",
            r"([^，。！？；,;]{2,40}?)(?:附近|周边)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if not match:
                continue
            address = SlotExtractor._clean_address(match.group(1))
            if address:
                return address
        return None

    @staticmethod
    def _clean_address(address: str) -> str:
        """清洗地址中的搜索动词和无关后缀。"""
        text = address.strip()
        text = re.sub(r"^(?:帮我找找|帮我找|找找|找一下|搜索|查一下|我要找的是|我想找|想找|找)", "", text).strip()
        text = re.sub(r"(?:附近|周边|这边|这里)$", "", text).strip()
        text = re.sub(r"的.*$", "", text).strip() if "附近的" in text or "周边的" in text else text
        return text if text and text not in {"附近", "周边"} else ""

    @staticmethod
    def _extract_budget(message: str) -> int | None:
        """提取人均预算上限。"""
        patterns = [
            r"人均\s*(\d+)\s*(?:元|块)?\s*以内",
            r"预算\s*(\d+)",
            r"(\d+)\s*块左右",
            r"别超过\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_radius(message: str) -> int | None:
        """提取搜索半径，统一转换成米。"""
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:公里|千米|km|KM)\s*(?:范围内|内|以内)?", message)
        if match:
            return int(float(match.group(1)) * 1000)

        match = re.search(r"(\d+)\s*(?:米|m|M)\s*(?:范围内|内|以内)?", message)
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def _extract_limit(message: str) -> int | None:
        """提取用户想要的推荐数量。"""
        match = re.search(r"(\d+)\s*家", message)
        if match:
            return max(1, min(int(match.group(1)), 20))
        return None

    @staticmethod
    def _extract_city(message: str) -> str | None:
        """提取常见城市名，作为 text search 的城市约束。"""
        for city in ("北京", "上海", "广州", "深圳", "哈尔滨", "成都", "杭州", "南京", "武汉", "西安", "重庆", "天津", "海口"):
            if city in message:
                return city
        return None

    @staticmethod
    def _extract_first(message: str, candidates: list[str]) -> str | None:
        """从候选词中提取第一个命中的值。"""
        for item in candidates:
            if item in message:
                return item
        return None

    @staticmethod
    def _contains_any(message: str, keywords: list[str]) -> bool:
        """判断文本中是否包含任意关键词。"""
        return any(keyword in message for keyword in keywords)
