"""Text, header and NPC normalization helpers."""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text)
    return text.upper().strip()


def normalize_header(value: Any) -> str:
    text = normalize_text(value)
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def normalize_npc(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            value = int(value)
    text = str(value).strip()
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?[Ee][+-]?\d+", text):
        try:
            decimal_value = Decimal(text)
            if decimal_value == decimal_value.to_integral_value():
                text = format(decimal_value.quantize(Decimal("1")), "f")
        except InvalidOperation:
            pass
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    digits = re.sub(r"\D", "", text)
    return digits


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def is_yes(value: Any) -> bool:
    return normalize_text(value) in {"SIM", "S", "YES", "Y", "1", "TRUE", "VERDADEIRO"}
