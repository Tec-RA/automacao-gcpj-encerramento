"""Attach Playwright to the existing debug Chrome instance."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from ..config import AppSettings
from ..exceptions import ChromeConnectionError, GCPJPageNotFoundError
from ..models import BrowserPageInfo, ConnectionStatus
from ..normalization import normalize_text
from .chrome import is_port_open, read_debug_version


def _all_frame_body_text(page: Page) -> str:
    parts: list[str] = []
    for frame in page.frames:
        try:
            text = frame.locator("body").inner_text(timeout=2000).strip()
            if text and text not in parts:
                parts.append(text)
        except Exception:
            continue
    return "\n".join(parts)


class CDPBrowserSession:
    """A short-lived Playwright connection that does not close the user's Chrome."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None

    def __enter__(self) -> "CDPBrowserSession":
        if not is_port_open(
            self.settings.chrome.debug_host,
            self.settings.chrome.debug_port,
        ):
            raise ChromeConnectionError(
                f"Chrome debugavel nao encontrado em {self.settings.chrome.cdp_url}."
            )
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(
                self.settings.chrome.cdp_url,
                slow_mo=self.settings.gcpj.slow_mo_ms,
                timeout=self.settings.gcpj.navigation_timeout_ms,
            )
        except Exception as exc:
            self.playwright.stop()
            self.playwright = None
            raise ChromeConnectionError(f"Falha ao conectar ao Chrome pelo CDP: {exc}") from exc
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        # Do not call browser.close(): it would close the user's Chrome instance.
        if self.playwright is not None:
            self.playwright.stop()
        self.browser = None
        self.playwright = None

    def all_pages(self) -> list[Page]:
        if self.browser is None:
            raise ChromeConnectionError("Sessao CDP nao iniciada.")
        pages: list[Page] = []
        for context in self.browser.contexts:
            pages.extend(context.pages)
        return pages

    def page_info(self) -> list[BrowserPageInfo]:
        infos: list[BrowserPageInfo] = []
        for page in self.all_pages():
            try:
                title = page.title()
            except Exception:
                title = ""
            url = page.url
            is_gcpj = (
                self.settings.gcpj.url_contains.lower() in url.lower()
                or self.settings.gcpj.title_contains.lower() in title.lower()
            )
            infos.append(BrowserPageInfo(title=title, url=url, is_gcpj=is_gcpj))
        return infos

    def find_gcpj_page(self) -> Page:
        candidates: list[tuple[int, Page]] = []
        for page in self.all_pages():
            try:
                title = page.title()
                url = page.url
            except Exception:
                continue
            score = 0
            if self.settings.gcpj.url_contains.lower() in url.lower():
                score += 10
            if self.settings.gcpj.title_contains.lower() in title.lower():
                score += 5
            if "juridico" in url.lower() and "bradesco" in url.lower():
                score += 3
            if score:
                candidates.append((score, page))
        if not candidates:
            raise GCPJPageNotFoundError(
                "Nenhuma aba do GCPJ foi localizada. Abra o GCPJ pela extensao e mantenha a aba aberta."
            )
        candidates.sort(key=lambda item: item[0], reverse=True)
        page = candidates[0][1]
        page.set_default_timeout(self.settings.gcpj.timeout_ms)
        page.set_default_navigation_timeout(self.settings.gcpj.navigation_timeout_ms)
        page.bring_to_front()
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        return page


def probe_connection(settings: AppSettings) -> ConnectionStatus:
    if not is_port_open(settings.chrome.debug_host, settings.chrome.debug_port):
        return ConnectionStatus(
            debug_port_open=False,
            message=f"Porta {settings.chrome.debug_port} fechada.",
        )

    version: dict[str, str] = {}
    try:
        version = read_debug_version(settings.chrome)
        with CDPBrowserSession(settings) as session:
            infos = session.page_info()
            authenticated = False
            try:
                page = session.find_gcpj_page()
                body = normalize_text(_all_frame_body_text(page))
                authenticated_markers = (
                    "MENU PRINCIPAL",
                    "JURIDICO ON-LINE",
                    "ENCERRAMENTO DE PROCESSOS",
                    "USUARIO CORRENTE",
                )
                authenticated = any(marker in body for marker in authenticated_markers)
            except Exception:
                authenticated = False
            return ConnectionStatus(
                debug_port_open=True,
                browser_product=version.get("Browser", ""),
                websocket_url=version.get("webSocketDebuggerUrl", ""),
                pages=infos,
                authenticated_gcpj_found=authenticated,
                message=(
                    "Chrome conectado e GCPJ autenticado localizado."
                    if authenticated
                    else "Chrome conectado, mas a aba autenticada do GCPJ nao foi confirmada."
                ),
            )
    except Exception as exc:
        return ConnectionStatus(
            debug_port_open=True,
            browser_product=version.get("Browser", ""),
            websocket_url=version.get("webSocketDebuggerUrl", ""),
            message=str(exc),
        )
