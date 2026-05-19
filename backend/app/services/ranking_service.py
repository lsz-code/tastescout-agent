from typing import Any

from pydantic import BaseModel


class RankingService:

    #从多个维度进行打分，包括评分、距离、菜系、关键词、历史偏好等，并生成推荐理由
    def rank_restaurants(
        self,
        restaurants: list[dict[str, Any]] | list[BaseModel],
        memory: dict[str, Any] | BaseModel | None = None,
        filters: dict[str, Any] | BaseModel | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        restaurant_dicts = [self._to_dict(item) for item in restaurants]
        memory_dict = self._normalize_memory(self._to_dict(memory))
        filter_dict = self._to_dict(filters)
        limit = max(1, min(int(limit), 50))

        ranked = []
        for restaurant in restaurant_dicts:
            restaurant_search_text = self._build_restaurant_search_text(restaurant)

            #根据餐厅信息、用户记忆和过滤条件进行打分，得到一个综合得分和匹配理由列表
            score, match_reasons = self._score_restaurant(
                restaurant=restaurant,
                restaurant_search_text=restaurant_search_text,
                memory=memory_dict,
                filters=filter_dict,
            )

            item = dict(restaurant)
            item["score"] = round(score, 2)
            item["match_reasons"] = match_reasons
            item["recommend_reason"] = self._generate_recommend_reason(
                item,
                match_reasons,
            )
            ranked.append(item)

#按分数对餐厅进行排序，分数相同的情况下按评分排序，评分也相同的情况下按距离排序，距离未知的排在最后
        ranked.sort(
            key=lambda item: (
                -float(item.get("score") or 0),
                -float(item.get("rating") or 0),
                self._sort_distance(item.get("distance")),
            )
        )

        #返回排名前N的餐厅，并构建最终的输出格式，包括排名、餐厅信息和推荐理由等
        return [
            self._build_ranked_restaurant(item, rank=index + 1)
            for index, item in enumerate(ranked[:limit])
        ]

    def _score_restaurant(
        self,
        restaurant: dict[str, Any],
        restaurant_search_text: str,
        memory: dict[str, Any],
        filters: dict[str, Any],
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        #把评分转换为浮点数进行计算，如果评分较高则加分，并记录推荐理由
        rating = self._to_float(restaurant.get("rating"))
        if rating is not None:
            score += rating * 4
            if rating >= 4.5:
                reasons.append(f"评分较高：{rating}")

        #把距离转换为浮点数进行计算，如果距离较近则加分，并记录推荐理由
        distance = self._to_float(restaurant.get("distance"))
        if distance is not None:
            distance_text = self._format_distance(distance)
            if distance <= 500:
                score += 15
                reasons.append(f"距离很近：{distance_text}m")
            elif distance <= 1000:
                score += 12
                reasons.append(f"距离较近：{distance_text}m")
            elif distance <= 3000:
                score += 8
                reasons.append(f"距离适中：{distance_text}m")

        #根据菜系是否符合要求，符合就加分
        cuisine = filters.get("cuisine")
        if cuisine and self._text_contains(restaurant_search_text, cuisine):
            score += 20
            reasons.append(f"符合本次想吃的菜系：{cuisine}")

        #关键词判断是否符合要求，符合就加分
        keyword = filters.get("keyword")
        if keyword and self._text_contains(restaurant_search_text, keyword):
            score += 10
            reasons.append(f"符合本次搜索关键词：{keyword}")

        #根据用户偏好判断菜系是否符合要求，符合就加分
        matched_cuisine = self._first_matching_word(
            restaurant_search_text,
            self._as_str_list(memory.get("favorite_cuisines")),
        )
        if matched_cuisine:
            score += 30
            reasons.append(f"符合你偏好的菜系：{matched_cuisine}")

        #获取平均价格和最大价格，看看是否符合偏好要求，符合就加分
        avg_price = self._to_int(restaurant.get("avg_price"))
        max_price = self._to_int(filters.get("max_price"))
        if avg_price is not None and max_price is not None and avg_price <= max_price:
            score += 10
            reasons.append(f"符合本次价格要求：人均 {avg_price} 元")

        #根据用户历史价格偏好判断是否符合要求，符合就加分
        if self._price_matches_history(avg_price, memory.get("price_preference")):
            score += 10
            reasons.append("价格符合你的历史偏好")

        #根据用户口味偏好判断是否符合要求，符合就加分
        matched_tastes = self._matching_words(
            restaurant_search_text,
            self._as_str_list(memory.get("taste_preference")),
        )
        for taste in matched_tastes[:3]:
            score += 5
            reasons.append(f"符合你的口味偏好：{taste}")

        #根据用餐场景判断是否符合本次用餐场景要求，符合就加分
        scene = filters.get("scene")
        if scene and self._text_contains(restaurant_search_text, scene):
            score += 10
            reasons.append(f"适合本次场景：{scene}")

        #根据用户历史用餐场景偏好判断是否符合要求，符合就加分
        matched_scene = self._first_matching_word(
            restaurant_search_text,
            self._as_str_list(memory.get("preferred_scenes")),
        )
        if matched_scene:
            score += 8
            reasons.append(f"符合你常用的用餐场景：{matched_scene}")

        #根据推荐菜品判断是否符合用户偏好菜品，符合就加分，如果包含用户忌口则扣分
        dish_text = self._stringify_recommended_dishes(
            restaurant.get("recommended_dishes")
        )
        matched_dish = self._first_matching_word(
            dish_text,
            self._as_str_list(memory.get("favorite_dishes")),
        )
        if matched_dish:
            score += 5
            reasons.append(f"包含你偏好的菜品：{matched_dish}")

        #根据用户忌口判断是否包含用户忌口菜品，如果包含则扣分
        matched_avoid = self._first_matching_word(
            restaurant_search_text,
            self._as_str_list(memory.get("avoid_foods")),
        )
        if matched_avoid:
            score -= 100
            reasons.append(f"可能包含你的忌口：{matched_avoid}")

        return score, self._dedupe(reasons)

    def _generate_recommend_reason(
        self,
        restaurant: dict[str, Any],
        match_reasons: list[str],
    ) -> str:
        if match_reasons:
            return "推荐原因：" + "；".join(match_reasons[:3])
        return "根据评分、距离和餐厅信息为你推荐。"

    #构建最终的输出格式，包括排名、餐厅信息和推荐理由等
    def _build_ranked_restaurant(
        self,
        restaurant: dict[str, Any],
        rank: int,
    ) -> dict[str, Any]:
        return {
            "rank": rank,
            "poi_id": restaurant.get("poi_id"),
            "name": restaurant.get("name"),
            "address": restaurant.get("address"),
            "photo": restaurant.get("photo"),
            "location": restaurant.get("location"),
            "distance": restaurant.get("distance"),
            "cuisine_type": restaurant.get("cuisine_type"),
            "category": restaurant.get("category"),
            "rating": restaurant.get("rating"),
            "avg_price": restaurant.get("avg_price"),
            "recommended_dishes": restaurant.get("recommended_dishes"),
            "review_summary": restaurant.get("review_summary"),
            "recommend_reason": restaurant.get("recommend_reason"),
            "match_reasons": restaurant.get("match_reasons", []),
            "score": float(restaurant.get("score") or 0),
        }

    #构建餐厅搜索文本，包含餐厅的名称、类别、菜系、地址、评论摘要、推荐理由和推荐菜品等信息。
    #方便后续进行关键词匹配和打分使用
    @staticmethod
    def _normalize_memory(data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data.get("memory"), dict):
            data = dict(data["memory"])

        price_preference = data.get("price_preference")
        if isinstance(price_preference, BaseModel):
            data["price_preference"] = price_preference.model_dump()

        return data

    #将搜索出的值转换成字典格式，方便后续处理和打分使用
    @staticmethod
    def _to_dict(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, dict):
            return dict(value)
        return {}

    #构建餐厅搜索文本，包含餐厅的名称、类别、菜系、地址、评论摘要、推荐理由和推荐菜品等信息。方便后续进行关键词匹配和打分使用
    @classmethod
    def _build_restaurant_search_text(cls, restaurant: dict[str, Any]) -> str:
        parts = [
            restaurant.get("name"),
            restaurant.get("category"),
            restaurant.get("cuisine_type"),
            restaurant.get("address"),
            restaurant.get("review_summary"),
            restaurant.get("recommend_reason"),
            cls._stringify_recommended_dishes(restaurant.get("recommended_dishes")),
        ]
        return " ".join(str(part) for part in parts if part)

    #把推荐菜品转换成字符串，方便进行关键词匹配和打分使用。推荐菜品可能是一个字符串、
    # 一个字典或者一个列表，里面包含菜品名称、推荐理由等信息
    @classmethod
    def _stringify_recommended_dishes(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    parts.extend(
                        str(item.get(key))
                        for key in ("dish_name", "name", "reason")
                        if item.get(key)
                    )
                elif item:
                    parts.append(str(item))
            return " ".join(parts)
        if isinstance(value, dict):
            return " ".join(
                str(value.get(key))
                for key in ("dish_name", "name", "reason")
                if value.get(key)
            )
        return str(value)

    #关键词存在判断
    @staticmethod
    def _text_contains(text: str, word: Any) -> bool:
        return bool(word) and str(word) in text

    #从文本中找到第一个匹配的词，返回该词或者None，如果没有匹配的词则返回None
    @classmethod    
    def _first_matching_word(cls, text: str, words: list[str]) -> str | None:
        matches = cls._matching_words(text, words)
        return matches[0] if matches else None

    #从文本中找到所有匹配的词，返回一个去重后的匹配词列表
    @classmethod
    def _matching_words(cls, text: str, words: list[str]) -> list[str]:
        matches = []
        for word in words:
            if word and word in text:
                matches.append(word)
        return cls._dedupe(matches)

    #根据平均价格和用户历史价格偏好判断是否符合要求，符合就加分
    @staticmethod
    def _price_matches_history(
        avg_price: int | None,
        price_preference: Any,
    ) -> bool:
        if avg_price is None:
            return False

        if isinstance(price_preference, BaseModel):
            price_preference = price_preference.model_dump()
        if not isinstance(price_preference, dict):
            return False

        min_price = RankingService._to_int(price_preference.get("min_price"))
        max_price = RankingService._to_int(price_preference.get("max_price"))

        if min_price is None and max_price is None:
            return False
        if min_price is not None and avg_price < min_price:
            return False
        if max_price is not None and avg_price > max_price:
            return False

        return True

    #把输入转换为字符串列表，过滤掉非字符串和空字符串，方便后续进行关键词匹配和打分使用
    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item]

    #把输入转换为浮点数或整数，如果无法转换则返回None，方便后续评分计算和排序使用
    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    #整数转换
    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    #按距离排序
    @staticmethod
    def _sort_distance(value: Any) -> float:
        distance = RankingService._to_float(value)
        return distance if distance is not None else float("inf")

    #把距离格式化成字符串，方便在推荐理由中展示使用
    @staticmethod
    def _format_distance(value: float) -> str:
        return str(int(round(value)))

    #列表去重，保持原有顺序，方便在推荐理由中展示使用
    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
