"""Application configuration loading."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ConfigurationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]


_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _is_windows_absolute_path(value: str | Path) -> bool:
    return bool(_WINDOWS_ABSOLUTE_PATH.match(str(value)))


def _resolve_path(value: str | Path, root: Path = PROJECT_ROOT) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(expanded)
    if path.is_absolute() or _is_windows_absolute_path(expanded):
        return path
    return (root / path).resolve()


@dataclass(frozen=True, slots=True)
class ChromeSettings:
    executable: Path
    user_data_dir: Path
    debug_host: str
    debug_port: int
    startup_timeout_seconds: int

    @property
    def cdp_url(self) -> str:
        return f"http://{self.debug_host}:{self.debug_port}"


@dataclass(frozen=True, slots=True)
class GCPJSettings:
    url_contains: str
    title_contains: str
    timeout_ms: int
    navigation_timeout_ms: int
    slow_mo_ms: int


@dataclass(frozen=True, slots=True)
class PathSettings:
    database: Path
    logs: Path
    evidence: Path
    exports: Path
    lock_file: Path


@dataclass(frozen=True, slots=True)
class AutomationSettings:
    screenshot_on_success: bool
    screenshot_on_error: bool
    retry_attempts: int
    success_terms: tuple[str, ...]
    error_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AppSettings:
    chrome: ChromeSettings
    gcpj: GCPJSettings
    paths: PathSettings
    automation: AutomationSettings
    selectors_path: Path
    reason_mapping_path: Path

    def ensure_directories(self) -> None:
        # Avoid creating a literal ``C:`` folder when the project is inspected on
        # a non-Windows CI host. On Windows, this is the dedicated Chrome profile.
        if os.name == "nt" or not _is_windows_absolute_path(self.chrome.user_data_dir):
            self.chrome.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.paths.database.parent.mkdir(parents=True, exist_ok=True)
        self.paths.logs.mkdir(parents=True, exist_ok=True)
        self.paths.evidence.mkdir(parents=True, exist_ok=True)
        self.paths.exports.mkdir(parents=True, exist_ok=True)
        self.paths.lock_file.parent.mkdir(parents=True, exist_ok=True)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Arquivo de configuracao nao encontrado: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuracao invalida: {path}")
    return data


def load_settings(config_path: str | Path | None = None) -> AppSettings:
    selected = Path(
        config_path
        or os.getenv("GCPJ_APP_CONFIG", str(PROJECT_ROOT / "config" / "app.yaml"))
    )
    if not selected.is_absolute():
        selected = (PROJECT_ROOT / selected).resolve()
    data = _read_yaml(selected)

    chrome_data = data.get("chrome", {})
    gcpj_data = data.get("gcpj", {})
    paths_data = data.get("paths", {})
    automation_data = data.get("automation", {})

    chrome = ChromeSettings(
        executable=_resolve_path(
            os.getenv(
                "GCPJ_CHROME_PATH",
                chrome_data.get("executable", "C:/Program Files/Google/Chrome/Application/chrome.exe"),
            )
        ),
        user_data_dir=_resolve_path(
            os.getenv(
                "GCPJ_PROFILE_DIR",
                chrome_data.get("user_data_dir", "C:/chrome_gcpj_debug"),
            )
        ),
        debug_host=os.getenv("GCPJ_DEBUG_HOST", chrome_data.get("debug_host", "127.0.0.1")),
        debug_port=int(os.getenv("GCPJ_DEBUG_PORT", chrome_data.get("debug_port", 9222))),
        startup_timeout_seconds=int(chrome_data.get("startup_timeout_seconds", 20)),
    )

    gcpj = GCPJSettings(
        url_contains=str(gcpj_data.get("url_contains", "juridico8.bradesco.com.br/gcpj")),
        title_contains=str(gcpj_data.get("title_contains", "GCPJ")),
        timeout_ms=int(gcpj_data.get("timeout_ms", 20000)),
        navigation_timeout_ms=int(gcpj_data.get("navigation_timeout_ms", 30000)),
        slow_mo_ms=int(gcpj_data.get("slow_mo_ms", 150)),
    )

    paths = PathSettings(
        database=_resolve_path(paths_data.get("database", "data/gcpj_automation.db")),
        logs=_resolve_path(paths_data.get("logs", "logs")),
        evidence=_resolve_path(paths_data.get("evidence", "evidence")),
        exports=_resolve_path(paths_data.get("exports", "data/exports")),
        lock_file=_resolve_path(paths_data.get("lock_file", "data/automation.lock")),
    )

    automation = AutomationSettings(
        screenshot_on_success=bool(automation_data.get("screenshot_on_success", True)),
        screenshot_on_error=bool(automation_data.get("screenshot_on_error", True)),
        retry_attempts=max(1, int(automation_data.get("retry_attempts", 2))),
        success_terms=tuple(
            str(value) for value in automation_data.get(
                "success_terms",
                ["SUCESSO", "ENCERRAMENTO SOLICITADO", "REGISTRO SALVO"],
            )
        ),
        error_terms=tuple(
            str(value) for value in automation_data.get(
                "error_terms",
                ["ERRO", "NAO FOI POSSIVEL", "CAMPO OBRIGATORIO"],
            )
        ),
    )

    settings = AppSettings(
        chrome=chrome,
        gcpj=gcpj,
        paths=paths,
        automation=automation,
        selectors_path=_resolve_path(data.get("selectors", "config/selectors.yaml")),
        reason_mapping_path=_resolve_path(data.get("reason_mapping", "config/motivo_mapping.yaml")),
    )
    settings.ensure_directories()
    return settings
