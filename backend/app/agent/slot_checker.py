from typing import Any


class SlotChecker:
    def check_search_slots(self, slots: dict[str, Any]) -> list[str]:
        missing_slots: list[str] = []

        if not slots.get("location") and not slots.get("address") and not slots.get("city"):
            missing_slots.append("location")

        return missing_slots
