import re
from typing import Any


class TextCleaner:
    HTML_TAG_RE = re.compile(r"<[^>]+>")
    CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    WHITESPACE_RE = re.compile(r"\s+")

    #进行数据清洗，去除HTML标签、控制字符、多余的空白等，并限制文本长度
    @staticmethod
    def clean_text(text: Any, max_length: int | None = None) -> str | None:
        if text is None:
            return None

        if not isinstance(text, str):
            text = str(text)

        text = TextCleaner.HTML_TAG_RE.sub("", text)
        text = TextCleaner.CONTROL_CHAR_RE.sub("", text)
        text = TextCleaner.WHITESPACE_RE.sub(" ", text).strip()

        if max_length is not None:
            text = text[:max_length]

        return text

    #进行字典数据的清洗，递归地清洗字典中的字符串值
    @staticmethod
    def clean_dict(data: dict[str, Any], max_text_length: int = 500) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, str):
                cleaned[key] = TextCleaner.clean_text(value, max_text_length)
            elif isinstance(value, dict):
                cleaned[key] = TextCleaner.clean_dict(value, max_text_length)
            elif isinstance(value, list):
                cleaned[key] = [
                    TextCleaner.clean_dict(item, max_text_length)
                    if isinstance(item, dict)
                    else TextCleaner.clean_text(item, max_text_length)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                cleaned[key] = value

        return cleaned
