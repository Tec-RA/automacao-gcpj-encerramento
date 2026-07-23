"""Map spreadsheet ATO values to GCPJ closure reasons."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import ConfigurationError
from ..normalization import normalize_text


@dataclass(frozen=True, slots=True)
class ReasonResolution:
    source_ato: str
    normalized_ato: str
    gcpj_reason: str | None
    blocked: bool
    message: str


class ReasonMapper:
    def __init__(self, mapping_path: Path) -> None:
        self.mapping_path = mapping_path
        self._mappings: dict[str, str] = {}
        self._blocked: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.mapping_path.exists():
            raise ConfigurationError(
                f"Arquivo de mapeamento de motivos nao encontrado: {self.mapping_path}"
            )
        with self.mapping_path.open("r", encoding="utf-8") as handle:
            data: dict[str, Any] = yaml.safe_load(handle) or {}

        mappings = data.get("mappings", {})
        blocked = data.get("blocked", {})
        if not isinstance(mappings, dict) or not isinstance(blocked, dict):
            raise ConfigurationError("motivo_mapping.yaml deve conter dicionarios mappings e blocked")

        self._mappings = {
            normalize_text(source): str(target).strip()
            for source, target in mappings.items()
            if str(target).strip()
        }
        self._blocked = {
            normalize_text(source): str(message).strip()
            for source, message in blocked.items()
        }

    @property
    def known_source_values(self) -> list[str]:
        return sorted(self._mappings)

    def resolve(self, ato: str) -> ReasonResolution:
        normalized = normalize_text(ato)
        if normalized in self._blocked:
            return ReasonResolution(
                source_ato=str(ato),
                normalized_ato=normalized,
                gcpj_reason=None,
                blocked=True,
                message=self._blocked[normalized],
            )
        reason = self._mappings.get(normalized)
        if reason:
            return ReasonResolution(
                source_ato=str(ato),
                normalized_ato=normalized,
                gcpj_reason=reason,
                blocked=False,
                message="Motivo mapeado com sucesso.",
            )
        return ReasonResolution(
            source_ato=str(ato),
            normalized_ato=normalized,
            gcpj_reason=None,
            blocked=False,
            message=(
                "ATO sem mapeamento. Inclua a equivalencia em "
                f"{self.mapping_path.name} antes de executar."
            ),
        )
