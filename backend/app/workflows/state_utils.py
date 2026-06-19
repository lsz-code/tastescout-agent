from typing import Any


REQUIRED_AGENT_FIELDS = ("user_id", "session_id", "message")


def missing_required_field(state: dict[str, Any]) -> str | None:
    """检查 Workflow 状态中执行 Agent Chat 必需的字段。"""
    for field in REQUIRED_AGENT_FIELDS:
        if not state.get(field):
            return f"missing required field: {field}"
    return None


def clean_text(value: Any) -> str | None:
    """把 LLM 或规则解析出的文本字段清洗成可用字符串。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "unknown", "未知", "无"}:
        return None
    return text


def to_int(value: Any) -> int | None:
    """把输入转换成 int，转换失败时返回 None。"""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    """把输入转换成 float，转换失败时返回 None。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
