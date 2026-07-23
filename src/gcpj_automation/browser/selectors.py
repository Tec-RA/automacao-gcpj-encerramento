"""Configurable selector registry with ordered fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..exceptions import ConfigurationError


class SelectorRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._selectors = self._load()

    def _load(self) -> dict[str, list[str]]:
        if not self.path.exists():
            raise ConfigurationError(f"Arquivo de seletores nao encontrado: {self.path}")
        with self.path.open("r", encoding="utf-8") as handle:
            data: dict[str, Any] = yaml.safe_load(handle) or {}
        selectors = data.get("selectors", data)
        if not isinstance(selectors, dict):
            raise ConfigurationError("selectors.yaml possui formato invalido.")
        parsed: dict[str, list[str]] = {}
        for key, values in selectors.items():
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ConfigurationError(f"Lista de seletores invalida para {key}.")
            parsed[str(key)] = list(values)
        return parsed

    def get(self, key: str) -> list[str]:
        values = self._selectors.get(key)
        if not values:
            raise ConfigurationError(f"Seletor nao configurado: {key}")
        return values

    def keys(self) -> list[str]:
        return sorted(self._selectors)
