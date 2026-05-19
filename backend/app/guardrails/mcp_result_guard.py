import json
from typing import Any

from app.guardrails.text_cleaner import TextCleaner


class MCPResultGuard:
    restaurant_allowed_fields = {
        "poi_id",
        "name",
        "address",
        "location",
        "distance",
        "category",
        "cuisine_type",
        "rating",
        "avg_price",
        "business_hours",
        "phone",
        "photo",
        "review_summary",
        "recommended_dishes",
        "raw_data",
    }

    required_fields = ["poi_id", "name"]

    #进行MCP数据返回的确认
    @classmethod
    def validate_restaurant(cls, raw: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("MCP result must be a dict")

        data = {
            key: value
            for key, value in raw.items()
            if key in cls.restaurant_allowed_fields
        }

        for field in cls.required_fields:
            if not data.get(field):
                raise ValueError(f"Missing required field: {field}")

        normalized = {
            "poi_id": TextCleaner.clean_text(data.get("poi_id"), 128),
            "name": TextCleaner.clean_text(data.get("name"), 200),
            "address": TextCleaner.clean_text(data.get("address"), 500),
            "location": data.get("location") if isinstance(data.get("location"), dict) else None,
            "distance": cls._to_float(data.get("distance")),
            "category": TextCleaner.clean_text(data.get("category"), 100),
            "cuisine_type": TextCleaner.clean_text(data.get("cuisine_type"), 100),
            "rating": cls._to_float(data.get("rating")),
            "avg_price": cls._to_int(data.get("avg_price")),
            "business_hours": TextCleaner.clean_text(data.get("business_hours"), 100),
            "phone": TextCleaner.clean_text(data.get("phone"), 50),
            "photo": TextCleaner.clean_text(data.get("photo"), 1000),
            "review_summary": TextCleaner.clean_text(data.get("review_summary"), 1000),
            "recommended_dishes": cls._normalize_dishes(data.get("recommended_dishes")),
            "raw_data": cls._limit_raw_data(data.get("raw_data")),
        }
        #保证餐厅名称与表示餐厅的唯一id都存在
        if not normalized["poi_id"]:
            raise ValueError("poi_id cannot be empty")
        if not normalized["name"]:
            raise ValueError("name cannot be empty")

        return normalized

    @classmethod
    def _normalize_dishes(cls, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        #先进行类型转换
        if isinstance(value, dict):
            value = [value]

        if isinstance(value, str):
            value = [value]

        #如果value为空，或者不是列表，则返回空列表
        if not isinstance(value, list):
            return []

        #构建推荐菜品的格式
        dishes = []
        for item in value[:20]:
            if isinstance(item, str):
                dish_name = TextCleaner.clean_text(item, 100)
                if dish_name:
                    dishes.append(
                        {
                            "dish_name": dish_name,
                            "reason": None,
                            "confidence": None,
                        }
                    )
                continue

            if not isinstance(item, dict):
                continue

            dish_name = TextCleaner.clean_text(
                item.get("dish_name") or item.get("name"),
                100,
            )
            if not dish_name:
                continue

            dishes.append(
                {
                    "dish_name": dish_name,
                    "reason": TextCleaner.clean_text(item.get("reason"), 300),
                    "confidence": cls._to_float(item.get("confidence")),
                }
            )

        return dishes

    @classmethod
    def _limit_raw_data(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None

        if not isinstance(value, dict):
            return {"value": TextCleaner.clean_text(value, 1000)}

        cleaned = TextCleaner.clean_dict(value, max_text_length=500)
        limited = dict(list(cleaned.items())[:30])

        encoded = json.dumps(limited, ensure_ascii=False, default=str)
        if len(encoded) <= 5000:
            return limited

        return {
            "truncated": True,
            "preview": encoded[:5000],
        }

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or value == "":
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
