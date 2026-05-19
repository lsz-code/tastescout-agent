from typing import Any


class SlotChecker:
    def check_search_slots(self, slots: dict[str, Any]) -> list[str]:
        missing_slots: list[str] = []

        if not slots.get("location") and not slots.get("address"):
            missing_slots.append("location")

        if not slots.get("keyword") and not slots.get("cuisine"):
            missing_slots.append("cuisine")

        return missing_slots
