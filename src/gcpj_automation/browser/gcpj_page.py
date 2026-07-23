"""Page object for the GCPJ closure flow shown in the reference video."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Frame, Locator, Page, TimeoutError as PlaywrightTimeoutError

from ..config import AppSettings
from ..exceptions import (
    GCPJNotAuthenticatedError,
    ProcessNotFoundError,
    ReasonNotAvailableError,
    SelectorNotFoundError,
)
from ..models import ItemStatus, ProcessSummary
from ..normalization import normalize_npc, normalize_text
from .selectors import SelectorRegistry


class GCPJClosurePage:
    def __init__(
        self,
        page: Page,
        settings: AppSettings,
        selectors: SelectorRegistry,
    ) -> None:
        self.page = page
        self.settings = settings
        self.selectors = selectors
        self.page.set_default_timeout(settings.gcpj.timeout_ms)
        self.page.set_default_navigation_timeout(settings.gcpj.navigation_timeout_ms)

    def _frames(self) -> list[Frame]:
        """Return main and child frames, keeping the most relevant frames first."""
        frames = list(self.page.frames)
        frames.sort(
            key=lambda frame: (
                self.settings.gcpj.url_contains.lower() in frame.url.lower(),
                frame is not self.page.main_frame,
            ),
            reverse=True,
        )
        return frames

    def _first_visible(
        self,
        selector_key: str,
        timeout_ms: int | None = None,
        required: bool = True,
    ) -> Locator | None:
        timeout = timeout_ms or self.settings.gcpj.timeout_ms
        deadline = time.monotonic() + timeout / 1000
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            for frame in self._frames():
                for selector in self.selectors.get(selector_key):
                    try:
                        locator = frame.locator(selector)
                        count = locator.count()
                        for index in range(min(count, 8)):
                            candidate = locator.nth(index)
                            if candidate.is_visible(timeout=250):
                                return candidate
                    except Exception as exc:
                        last_error = exc
            time.sleep(0.15)
        if required:
            suffix = f" Ultimo erro: {last_error}" if last_error else ""
            raise SelectorNotFoundError(
                f"Elemento GCPJ nao encontrado: {selector_key}.{suffix}"
            )
        return None

    def _body_text(self) -> str:
        parts: list[str] = []
        for frame in self._frames():
            try:
                text = frame.locator("body").inner_text(timeout=3000).strip()
                if text and text not in parts:
                    parts.append(text)
            except Exception:
                continue
        return "\n".join(parts)

    def assert_authenticated(self) -> None:
        authenticated_markers = (
            "MENU PRINCIPAL",
            "JURIDICO ON-LINE",
            "ENCERRAMENTO DE PROCESSOS",
            "USUARIO CORRENTE",
        )
        deadline = time.monotonic() + min(self.settings.gcpj.timeout_ms, 10000) / 1000
        last_body = ""
        while time.monotonic() < deadline:
            last_body = normalize_text(self._body_text())
            if any(marker in last_body for marker in authenticated_markers):
                return
            if last_body:
                time.sleep(0.2)
            else:
                time.sleep(0.35)

        if not last_body:
            raise GCPJNotAuthenticatedError("A pagina do GCPJ esta vazia ou nao respondeu.")
        if all(marker in last_body for marker in ("USUARIO", "SENHA")) or "LOGIN" in last_body:
            raise GCPJNotAuthenticatedError(
                "A aba do GCPJ foi encontrada, mas a sessao parece nao estar autenticada."
            )
        raise GCPJNotAuthenticatedError(
            "Nao foi possivel confirmar a autenticacao do GCPJ."
        )

    def is_search_page(self) -> bool:
        search_input = self._first_visible("search_npc_input", timeout_ms=1000, required=False)
        search_button = self._first_visible("search_button", timeout_ms=1000, required=False)
        return search_input is not None and search_button is not None

    def is_closure_form(self) -> bool:
        return (
            self._first_visible("closure_date_input", timeout_ms=1000, required=False) is not None
            and self._first_visible("closure_reason_select", timeout_ms=1000, required=False) is not None
        )

    def go_to_closure_search(self) -> None:
        self.page.bring_to_front()
        self.assert_authenticated()
        if self.is_search_page():
            return
        if self.is_closure_form():
            back = self._first_visible("back_button", timeout_ms=1500, required=False)
            if back is not None:
                back.click()
                try:
                    self.page.wait_for_load_state("domcontentloaded")
                except PlaywrightTimeoutError:
                    pass
                if self.is_search_page():
                    return
        menu_link = self._first_visible("closure_menu_link")
        menu_link.click()
        try:
            self.page.wait_for_load_state("domcontentloaded")
        except PlaywrightTimeoutError:
            pass
        self._first_visible("search_npc_input")

    def search_process(self, npc: str) -> ProcessSummary:
        self.go_to_closure_search()
        input_locator = self._first_visible("search_npc_input")
        input_locator.fill(npc)
        self._first_visible("search_button").click()
        try:
            self.page.wait_for_load_state("domcontentloaded")
        except PlaywrightTimeoutError:
            pass

        body = normalize_text(self._body_text())
        error_patterns = (
            "PROCESSO NAO ENCONTRADO",
            "NAO LOCALIZADO",
            "NENHUM REGISTRO",
            "PROCESSO INEXISTENTE",
        )
        if any(pattern in body for pattern in error_patterns):
            raise ProcessNotFoundError(f"NPC {npc} nao localizado no GCPJ.")
        self._first_visible("closure_date_input")
        displayed = self._extract_value_after_label("N do Processo Bradesco")
        if displayed and normalize_npc(displayed) != normalize_npc(npc):
            raise ProcessNotFoundError(
                f"O GCPJ retornou o NPC {displayed}, diferente do solicitado {npc}."
            )
        return ProcessSummary(
            npc=displayed or npc,
            group_company=self._extract_value_after_label("Empresa Grupo"),
            legal_department=self._extract_value_after_label("Departamento Juridico"),
            responsible_lawyer=self._extract_value_after_label("Advogado Responsavel"),
        )

    def _extract_value_after_label(self, label: str) -> str:
        normalized_label = normalize_text(label)
        script = r"""
        (needle) => {
          const norm = (value) => (value || '')
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/\s+/g, ' ').trim().toUpperCase();
          const nodes = Array.from(document.querySelectorAll('td, th, div, span, label, b, strong'));
          const candidates = nodes
            .filter((node) => norm(node.textContent).includes(needle))
            .sort((left, right) => norm(left.textContent).length - norm(right.textContent).length);
          const target = candidates[0];
          if (!target) return '';
          const row = target.closest('tr');
          if (row) {
            const cells = Array.from(row.querySelectorAll('td, th'));
            const index = cells.indexOf(target.closest('td, th'));
            if (index >= 0 && index + 1 < cells.length) return cells[index + 1].innerText.trim();
          }
          const next = target.nextElementSibling;
          return next ? next.innerText.trim() : '';
        }
        """
        for frame in self._frames():
            try:
                value = str(frame.evaluate(script, normalized_label) or "").strip()
                if value:
                    return value
            except Exception:
                continue
        return ""

    def fill_closure_form(self, date_text: str, reason: str, details: str = "") -> None:
        self._fill_date(date_text)
        self._select_reason(reason)
        details_locator = self._first_visible("closure_details", required=False)
        if details_locator is not None:
            details_locator.fill(details)

    def _fill_date(self, date_text: str) -> None:
        locator = self._first_visible("closure_date_input")
        try:
            locator.fill(date_text)
        except Exception:
            locator.evaluate(
                """
                (element, value) => {
                  element.removeAttribute('readonly');
                  element.value = value;
                  element.dispatchEvent(new Event('input', {bubbles: true}));
                  element.dispatchEvent(new Event('change', {bubbles: true}));
                }
                """,
                date_text,
            )
        current = str(locator.input_value() or "").strip()
        if normalize_text(current) != normalize_text(date_text):
            raise SelectorNotFoundError(
                f"A data nao permaneceu preenchida. Esperado: {date_text}; atual: {current}."
            )

    def _select_reason(self, requested_reason: str) -> str:
        select = self._first_visible("closure_reason_select")
        option_texts = select.locator("option").all_text_contents()
        requested_normalized = normalize_text(requested_reason)
        compact_requested = re.sub(r"[^A-Z0-9]", "", requested_normalized)

        matching_index: int | None = None
        for index, option in enumerate(option_texts):
            option_normalized = normalize_text(option)
            if option_normalized == requested_normalized:
                matching_index = index
                break
            compact_option = re.sub(r"[^A-Z0-9]", "", option_normalized)
            if compact_option and compact_option == compact_requested:
                matching_index = index
                break

        if matching_index is None:
            available = ", ".join(option.strip() for option in option_texts if option.strip())
            raise ReasonNotAvailableError(
                f"Motivo '{requested_reason}' nao encontrado no GCPJ. Opcoes visiveis: {available}"
            )

        select.select_option(index=matching_index)
        selected = select.locator("option:checked").inner_text().strip()
        if normalize_text(selected) != normalize_text(option_texts[matching_index]):
            raise ReasonNotAvailableError(
                f"O motivo selecionado nao foi confirmado. Atual: {selected}"
            )
        return selected

    def submit(self) -> tuple[ItemStatus, str]:
        """Click save once and never retry an uncertain submission automatically."""
        dialogs: list[tuple[str, str]] = []

        def accept_dialog(dialog: Any) -> None:
            dialogs.append((dialog.type, dialog.message))
            dialog.accept()

        save_button = self._first_visible("save_button")
        previous_url = self.page.url
        self.page.once("dialog", accept_dialog)
        try:
            try:
                save_button.click()
            except Exception as exc:
                return (
                    ItemStatus.SUBMITTED_UNCONFIRMED,
                    "A tentativa de acionar SALVAR nao pôde ser confirmada. "
                    f"O item nao sera repetido automaticamente para evitar duplicidade: {exc}",
                )

            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            success: str | None = None
            error: str | None = None
            dialog_success: str | None = None
            dialog_error: str | None = None
            returned_to_search = False
            confirmation_deadline = time.monotonic() + min(
                self.settings.gcpj.navigation_timeout_ms,
                15000,
            ) / 1000

            while time.monotonic() < confirmation_deadline:
                body = normalize_text(self._body_text())
                success = next(
                    (
                        term
                        for term in self.settings.automation.success_terms
                        if normalize_text(term) in body
                    ),
                    None,
                )
                error = next(
                    (
                        term
                        for term in self.settings.automation.error_terms
                        if normalize_text(term) in body
                    ),
                    None,
                )
                dialog_text = " | ".join(message for _, message in dialogs)
                normalized_dialog = normalize_text(dialog_text)
                dialog_error = next(
                    (
                        term
                        for term in self.settings.automation.error_terms
                        if normalize_text(term) in normalized_dialog
                    ),
                    None,
                )
                dialog_success = next(
                    (
                        term
                        for term in self.settings.automation.success_terms
                        if normalize_text(term) in normalized_dialog
                    ),
                    None,
                )
                if error or dialog_error or success or dialog_success:
                    break

                search_input = self._first_visible(
                    "search_npc_input",
                    timeout_ms=350,
                    required=False,
                )
                search_button = self._first_visible(
                    "search_button",
                    timeout_ms=350,
                    required=False,
                )
                returned_to_search = search_input is not None and search_button is not None
                if returned_to_search:
                    break
                time.sleep(0.25)

            dialog_text = " | ".join(message for _, message in dialogs)
            if error or dialog_error:
                detected = error or dialog_error
                return ItemStatus.ERROR, f"O GCPJ apresentou uma mensagem de erro: {detected}."
            if success or dialog_success:
                detected = success or dialog_success
                return ItemStatus.SUBMITTED, f"Confirmacao localizada no GCPJ: {detected}."
            if returned_to_search:
                return (
                    ItemStatus.SUBMITTED,
                    "O GCPJ retornou para a pesquisa apos salvar; solicitacao tratada como enviada.",
                )
            if dialogs:
                return (
                    ItemStatus.SUBMITTED_UNCONFIRMED,
                    "O dialogo do GCPJ foi aceito, mas nao houve confirmacao final reconhecida: "
                    f"{dialog_text}",
                )
            if self.page.url != previous_url:
                return (
                    ItemStatus.SUBMITTED_UNCONFIRMED,
                    "O GCPJ mudou de pagina apos SALVAR, mas nao exibiu uma confirmacao reconhecida.",
                )
            return (
                ItemStatus.SUBMITTED_UNCONFIRMED,
                "O botao salvar foi acionado, mas o video fornecido nao mostra a mensagem final. "
                "O item nao sera repetido automaticamente; confira-o no GCPJ e no relatorio.",
            )
        finally:
            # If no dialog appeared, remove the pending one-shot listener so a later,
            # unrelated dialog is not accepted by this item.
            if not dialogs:
                try:
                    self.page.remove_listener("dialog", accept_dialog)
                except Exception:
                    pass

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def diagnostic_snapshot(self) -> dict[str, Any]:
        script = """
        () => {
          const safeValue = (el) => {
            const type = (el.type || '').toLowerCase();
            if (['submit', 'button', 'reset'].includes(type)) return el.value || '';
            return '';
          };
          return {
            inputs: Array.from(document.querySelectorAll('input')).map((el) => ({
              type: el.type || '', id: el.id || '', name: el.name || '',
              value: safeValue(el), placeholder: el.placeholder || ''
            })),
            selects: Array.from(document.querySelectorAll('select')).map((el) => ({
              id: el.id || '', name: el.name || '',
              options: Array.from(el.options).map((opt) => opt.text.trim())
            })),
            textareas: Array.from(document.querySelectorAll('textarea')).map((el) => ({
              id: el.id || '', name: el.name || ''
            })),
            links: Array.from(document.querySelectorAll('a')).map((el) => ({
              text: (el.innerText || '').trim(), href: el.href || ''
            })).filter((item) => item.text)
          };
        }
        """
        frame_snapshots: list[dict[str, Any]] = []
        for index, frame in enumerate(self._frames()):
            try:
                snapshot = dict(frame.evaluate(script))
            except Exception as exc:
                snapshot = {"error": str(exc)}
            snapshot.update(
                {
                    "index": index,
                    "name": frame.name,
                    "url": frame.url,
                    "is_main_frame": frame is self.page.main_frame,
                }
            )
            frame_snapshots.append(snapshot)
        return {
            "title": self.page.title(),
            "url": self.page.url,
            "frames": frame_snapshots,
        }

