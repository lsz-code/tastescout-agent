import json
from typing import Any

from app.guardrails.mcp_result_guard import MCPResultGuard
from app.guardrails.text_cleaner import TextCleaner


class DatabaseWriteGuard:
    writable_fields = {
        "poi_id",
        "name",
        "address",
        "photo",
        "location",
        "cuisine_type",
        "rating",
        "avg_price",
        "distance",
        "recommended_dishes",
        "review_summary",
        "recommend_reason",
        "raw_data",
    }

    @classmethod
    def validate_favorite_restaurant(cls, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Favorite restaurant data must be a dict")

        poi_id = TextCleaner.clean_text(data.get("poi_id"), 128)
        name = TextCleaner.clean_text(data.get("name"), 200)

        if not poi_id:
            raise ValueError("poi_id is required")
        if not name:
            raise ValueError("name is required")

        rating = cls._normalize_rating(data.get("rating"))
        avg_price = cls._normalize_non_negative_int(data.get("avg_price"))
        distance = cls._normalize_non_negative_float(data.get("distance"))

        cuisine_type = data.get("cuisine_type") or data.get("category")

        cleaned = {
            "poi_id": poi_id,
            "name": name,
            "address": TextCleaner.clean_text(data.get("address"), 500),
            "photo": TextCleaner.clean_text(data.get("photo"), 1000),
            "location": data.get("location") if isinstance(data.get("location"), dict) else None,
            "cuisine_type": TextCleaner.clean_text(cuisine_type, 100),
            "rating": rating,
            "avg_price": avg_price,
            "distance": distance,
            "recommended_dishes": MCPResultGuard._normalize_dishes(
                data.get("recommended_dishes")
            ),
            "review_summary": TextCleaner.clean_text(data.get("review_summary"), 1000),
            "recommend_reason": TextCleaner.clean_text(data.get("recommend_reason"), 1000),
            "raw_data": cls._limit_raw_data(data.get("raw_data")),
        }

        return {
            key: value
            for key, value in cleaned.items()
            if key in cls.writable_fields
        }

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
    def _normalize_rating(value: Any) -> float | None:
        try:
            rating = float(value)
        except (TypeError, ValueError):
            return None

        if rating < 0 or rating > 5:
            return None

        return rating

    @staticmethod
    def _normalize_non_negative_int(value: Any) -> int | None:
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            return None

        if number < 0:
            return None

        return number

    @staticmethod
    def _normalize_non_negative_float(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        if number < 0:
            return None

        return number
