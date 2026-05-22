from typing import Any


class FollowupQuestionBuilder:
    def build(self, missing_slots: list[str], slots: dict[str, Any]) -> str:
        missing = set(missing_slots)

        if "location" in missing:
            keyword = str(slots.get("keyword") or "").strip()
            if keyword and keyword != "美食":
                return "我能帮你找这家店，不过你想看哪个城市或哪附近的？"
            return "我可以帮你找，不过还不知道你想看哪附近。你可以发个地址，或者点一下“使用我的位置”。"

        return "我还差一点信息才能帮你找，你可以补个地址，或者直接点“使用我的位置”。"
