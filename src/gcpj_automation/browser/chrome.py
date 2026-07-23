"""Launch and inspect the dedicated debug Chrome profile."""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import ChromeSettings
from ..exceptions import ChromeConnectionError, ChromeNotFoundError


@dataclass(frozen=True, slots=True)
class ChromeLaunchResult:
    launched: bool
    already_running: bool
    executable: str
    profile: str
    cdp_url: str
    message: str


def is_port_open(host: str, port: int, timeout: float = 0.8) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        return connection.connect_ex((host, port)) == 0


def read_debug_version(settings: ChromeSettings, timeout: float = 2.0) -> dict[str, str]:
    endpoint = f"{settings.cdp_url}/json/version"
    try:
        with urllib.request.urlopen(endpoint, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ChromeConnectionError(
            f"A porta {settings.debug_port} respondeu, mas o endpoint CDP nao esta disponivel."
        ) from exc
    return {str(key): str(value) for key, value in payload.items()}


def _candidate_chrome_paths(configured: Path) -> list[Path]:
    paths = [configured]
    if platform.system() == "Windows":
        for environment_variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(environment_variable)
            if base:
                paths.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
    return list(dict.fromkeys(paths))


def find_chrome_executable(configured: Path) -> Path:
    for candidate in _candidate_chrome_paths(configured):
        if candidate.exists() and candidate.is_file():
            return candidate
    raise ChromeNotFoundError(
        "Google Chrome nao encontrado. Ajuste chrome.executable em config/app.yaml."
    )


def launch_debug_chrome(settings: ChromeSettings) -> ChromeLaunchResult:
    if is_port_open(settings.debug_host, settings.debug_port):
        version = read_debug_version(settings)
        return ChromeLaunchResult(
            launched=False,
            already_running=True,
            executable=version.get("Browser", "Chrome"),
            profile=str(settings.user_data_dir),
            cdp_url=settings.cdp_url,
            message="O Chrome de automacao ja esta aberto e respondendo.",
        )

    if platform.system() != "Windows":
        raise ChromeNotFoundError(
            "O botao de abertura automatica foi preparado para Windows. "
            "Abra o Chrome manualmente com a porta de depuracao configurada."
        )

    executable = find_chrome_executable(settings.executable)
    settings.user_data_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable),
        f"--remote-debugging-port={settings.debug_port}",
        f"--user-data-dir={settings.user_data_dir}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )

    deadline = time.monotonic() + settings.startup_timeout_seconds
    while time.monotonic() < deadline:
        if is_port_open(settings.debug_host, settings.debug_port):
            version = read_debug_version(settings)
            return ChromeLaunchResult(
                launched=True,
                already_running=False,
                executable=version.get("Browser", str(executable)),
                profile=str(settings.user_data_dir),
                cdp_url=settings.cdp_url,
                message="Chrome GCPJ iniciado com sucesso.",
            )
        time.sleep(0.4)

    raise ChromeConnectionError(
        f"O Chrome foi iniciado, mas a porta {settings.debug_port} nao respondeu dentro do prazo."
    )
