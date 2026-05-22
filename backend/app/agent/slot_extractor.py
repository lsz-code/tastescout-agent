import re
from typing import Any


class SlotExtractor:
    CUISINES = [
        "川菜",
        "火锅",
        "烧烤",
        "日料",
        "粤菜",
        "湘菜",
        "韩餐",
        "西餐",
        "面馆",
        "小吃",
        "奶茶",
        "甜品",
    ]
    SHOP_SUFFIXES = (
        "店",
        "餐厅",
        "饭店",
        "酒馆",
        "火锅",
        "烧烤",
        "奶茶",
        "咖啡",
        "面馆",
        "小馆",
        "食堂",
        "酒吧",
        "居酒屋",
    )
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

    def extract(
        self,
        message: str,
        short_term_memory: dict[str, Any] | None = None,
        request_location: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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

        shop_keyword = self._extract_shop_keyword(message)
        cuisine = self._extract_first(message, self.CUISINES)
        if shop_keyword:
            slots["keyword"] = shop_keyword
        elif cuisine:
            slots["cuisine"] = cuisine
            slots["keyword"] = cuisine
        elif self._contains_any(
            message,
            ["美食", "餐厅", "饭店", "好吃", "随便推荐", "吃饭", "吃点东西"],
        ):
            slots["keyword"] = "美食"

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

        return slots

    @classmethod
    def _extract_address(cls, message: str) -> str | None:
        patterns = [
            r"我(?:现在|目前|这会儿|刚好)?在([^，,。；;]+)",
            r"(?:我)?人在([^，,。；;]+)",
            r"(?:现在|目前|这会儿|刚好)在([^，,。；;]+)",
            r"(?:位置|地址)(?:是|在)?([^，,。；;]+)",
            r"我在([^，,。；;]+)",
            r"在([^，,。；;]+?)附近",
            r"([^，,。；;]+?)附近",
            r"([^，,。；;]{2,20})(?:这边|这里|当地)",
            r"([^，,。；;]{2,20})(?:有啥|有什么)好吃",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                address = cls._clean_address(match.group(1))
                if address and address not in {"附近", "周边"}:
                    return address
        return None

    @staticmethod
    def _clean_address(address: str) -> str:
        address = re.sub(r"^(?:帮我|你)?(?:找找|找一下|搜一下|搜索|查一下|看看|找|搜)?", "", address.strip())
        return re.sub(r"(附近|周边)$", "", address.strip()).strip()

    @classmethod
    def _extract_shop_keyword(cls, message: str) -> str | None:
        patterns = [
            r"(?:附近|周边)的?([^，,。！？!?]+?(?:店|餐厅|饭店|酒馆|火锅|烧烤|奶茶|咖啡|面馆|小馆|食堂|酒吧|居酒屋))",
            r"(?:找找|找一下|搜一下|搜索|帮我找|有没有|查一下|看看|想找)([^，,。！？!?]+?(?:店|餐厅|饭店|酒馆|火锅|烧烤|奶茶|咖啡|面馆|小馆|食堂|酒吧|居酒屋))",
            r"([^，,。！？!?]+?(?:店|餐厅|饭店|酒馆|火锅|烧烤|奶茶|咖啡|面馆|小馆|食堂|酒吧|居酒屋))(?:在哪|在哪里|在哪儿)",
            r"(?:找找|找一下|搜一下|搜索|帮我找|有没有|查一下|看看|想找)([^，,。！？!?]{2,30})",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                keyword = cls._clean_shop_keyword(match.group(1))
                if keyword:
                    return keyword
        return None

    @classmethod
    def _clean_shop_keyword(cls, keyword: str) -> str:
        keyword = re.sub(r"^(?:的|这家|那家|一下|附近的?)", "", keyword.strip())
        keyword = re.sub(r"(?:在哪|在哪里|在哪儿)$", "", keyword).strip()
        if keyword in {"餐厅", "饭店", "吃的", "好吃的", "美食", "吃饭的地方"}:
            return ""
        if keyword.endswith(cls.SHOP_SUFFIXES):
            return keyword
        return keyword if 2 <= len(keyword) <= 30 else ""

    @staticmethod
    def _extract_budget(message: str) -> int | None:
        patterns = [
            r"人均\s*(\d+)\s*(?:元|块)?以内",
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
        match = re.search(r"(\d+)\s*(?:米|m|M)内", message)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_limit(message: str) -> int | None:
        match = re.search(r"(\d+)\s*家", message)
        if match:
            return max(1, min(int(match.group(1)), 20))
        return None

    @classmethod
    def _extract_first(cls, message: str, candidates: list[str]) -> str | None:
        for item in candidates:
            if item in message:
                return item
        return None

    @staticmethod
    def _contains_any(message: str, keywords: list[str]) -> bool:
        return any(keyword in message for keyword in keywords)
