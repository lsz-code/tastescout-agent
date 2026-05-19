from typing import Any


class FollowupQuestionBuilder:
    def build(self, missing_slots: list[str], slots: dict[str, Any]) -> str:
        missing = set(missing_slots)

        if {"location", "cuisine"}.issubset(missing):
            return "我还不知道你在哪附近、想吃什么类型。你可以告诉我位置和菜系，或者点击“使用我的位置”。"

        if "location" in missing:
            return "我还不知道你在哪附近。你可以输入地址，或者点击“使用我的位置”。"

        if "cuisine" in missing:
            return "你想吃什么类型？比如川菜、火锅、烧烤、日料，或者直接说“随便推荐”。"

        return "我还需要一点信息才能推荐，你可以告诉我位置、菜系、预算或用餐场景。"
