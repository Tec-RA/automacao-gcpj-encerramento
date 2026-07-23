"""Orchestrate a batch of GCPJ closure operations."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime

from filelock import FileLock, Timeout as FileLockTimeout

from ..browser.gcpj_page import GCPJClosurePage
from ..browser.selectors import SelectorRegistry
from ..browser.session import CDPBrowserSession
from ..config import AppSettings
from ..models import ClosureItem, ExecutionMode, ItemResult, ItemStatus
from ..repositories.execution_repository import ExecutionRepository


ProgressCallback = Callable[[int, int, ItemResult | None, str], None]


class AutomationRunner:
    def __init__(
        self,
        settings: AppSettings,
        repository: ExecutionRepository,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.logger = logger
        self.selectors = SelectorRegistry(settings.selectors_path)

    def new_execution_id(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"GCPJ_{stamp}_{uuid.uuid4().hex[:8].upper()}"

    def run(
        self,
        items: Iterable[ClosureItem],
        mode: ExecutionMode,
        execution_id: str | None = None,
        capture_evidence: bool = True,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[str, list[ItemResult], datetime, datetime]:
        item_list = list(items)
        execution_id = execution_id or self.new_execution_id()
        started_at = datetime.now()
        self.repository.start_execution(
            execution_id=execution_id,
            mode=mode,
            started_at=started_at,
            total_items=len(item_list),
            metadata={"capture_evidence": capture_evidence},
        )
        results: list[ItemResult] = []

        try:
            with FileLock(str(self.settings.paths.lock_file), timeout=1):
                with CDPBrowserSession(self.settings) as session:
                    page = session.find_gcpj_page()
                    gcpj = GCPJClosurePage(page, self.settings, self.selectors)
                    gcpj.assert_authenticated()
                    for index, item in enumerate(item_list, start=1):
                        if progress_callback:
                            progress_callback(index - 1, len(item_list), None, f"Iniciando NPC {item.npc}")
                        result = self._run_item(
                            gcpj=gcpj,
                            item=item,
                            mode=mode,
                            execution_id=execution_id,
                            capture_evidence=capture_evidence,
                        )
                        results.append(result)
                        self.repository.save_item(execution_id, result)
                        if progress_callback:
                            progress_callback(index, len(item_list), result, result.message)
        except FileLockTimeout as exc:
            finished_at = datetime.now()
            self.repository.finish_execution(
                execution_id,
                finished_at,
                "ERRO",
            )
            raise RuntimeError(
                "Ja existe outra execucao da automacao em andamento neste computador."
            ) from exc
        except Exception:
            finished_at = datetime.now()
            self.repository.finish_execution(
                execution_id,
                finished_at,
                "ERRO",
            )
            raise

        finished_at = datetime.now()
        if any(result.status is ItemStatus.ERROR for result in results):
            final_status = "CONCLUIDO_COM_ERROS"
        elif any(result.status is ItemStatus.SUBMITTED_UNCONFIRMED for result in results):
            final_status = "CONCLUIDO_COM_PENDENCIAS"
        else:
            final_status = "CONCLUIDO"
        self.repository.finish_execution(execution_id, finished_at, final_status)
        return execution_id, results, started_at, finished_at

    def _run_item(
        self,
        gcpj: GCPJClosurePage,
        item: ClosureItem,
        mode: ExecutionMode,
        execution_id: str,
        capture_evidence: bool,
    ) -> ItemResult:
        item_started = datetime.now()
        last_exception: Exception | None = None
        summary = None

        for attempt in range(1, self.settings.automation.retry_attempts + 1):
            try:
                self.logger.info(
                    "Execution %s | NPC %s | attempt %s/%s | mode %s",
                    execution_id,
                    item.npc,
                    attempt,
                    self.settings.automation.retry_attempts,
                    mode.value,
                )
                summary = gcpj.search_process(item.npc)
                if mode is ExecutionMode.VALIDATE:
                    evidence = self._capture(
                        gcpj,
                        execution_id,
                        item,
                        "validado",
                        capture_evidence and self.settings.automation.screenshot_on_success,
                    )
                    return self._result(
                        item,
                        ItemStatus.VALIDATED,
                        "Pasta localizada e dados basicos validados no GCPJ.",
                        item_started,
                        summary,
                        evidence,
                    )

                date_text = item.closure_date.strftime("%d/%m/%Y")
                gcpj.fill_closure_form(date_text, item.gcpj_reason, item.details)
                if mode is ExecutionMode.FILL_ONLY:
                    evidence = self._capture(
                        gcpj,
                        execution_id,
                        item,
                        "preenchido",
                        capture_evidence and self.settings.automation.screenshot_on_success,
                    )
                    return self._result(
                        item,
                        ItemStatus.FILLED,
                        "Data e motivo preenchidos. O botao salvar nao foi acionado.",
                        item_started,
                        summary,
                        evidence,
                    )

                status, message = gcpj.submit()
                screenshot_enabled = capture_evidence and (
                    self.settings.automation.screenshot_on_error
                    if status is ItemStatus.ERROR
                    else self.settings.automation.screenshot_on_success
                )
                evidence = self._capture(
                    gcpj,
                    execution_id,
                    item,
                    "solicitado" if status is ItemStatus.SUBMITTED else status.value.lower(),
                    screenshot_enabled,
                )
                return self._result(
                    item,
                    status,
                    message,
                    item_started,
                    summary,
                    evidence,
                )
            except Exception as exc:
                last_exception = exc
                self.logger.exception(
                    "Execution %s | NPC %s | attempt %s failed: %s",
                    execution_id,
                    item.npc,
                    attempt,
                    exc,
                )
                if attempt < self.settings.automation.retry_attempts:
                    time.sleep(0.8 * attempt)
                    try:
                        gcpj.go_to_closure_search()
                    except Exception:
                        pass
                    continue

        evidence = self._capture(
            gcpj,
            execution_id,
            item,
            "erro",
            capture_evidence and self.settings.automation.screenshot_on_error,
        )
        return self._result(
            item,
            ItemStatus.ERROR,
            f"Falha apos {self.settings.automation.retry_attempts} tentativa(s): {last_exception}",
            item_started,
            summary,
            evidence,
        )

    def _capture(
        self,
        gcpj: GCPJClosurePage,
        execution_id: str,
        item: ClosureItem,
        suffix: str,
        enabled: bool,
    ) -> str:
        if not enabled:
            return ""
        safe_npc = "".join(character for character in item.npc if character.isdigit())
        path = (
            self.settings.paths.evidence
            / execution_id
            / f"linha_{item.row_number}_npc_{safe_npc}_{suffix}.png"
        )
        try:
            return str(gcpj.screenshot(path))
        except Exception as exc:
            self.logger.warning("Falha ao salvar evidencia de %s: %s", item.npc, exc)
            return ""

    @staticmethod
    def _result(
        item: ClosureItem,
        status: ItemStatus,
        message: str,
        started_at: datetime,
        summary,
        evidence: str,
    ) -> ItemResult:
        return ItemResult(
            row_number=item.row_number,
            npc=item.npc,
            ato=item.ato,
            gcpj_reason=item.gcpj_reason,
            status=status,
            message=message,
            started_at=started_at,
            finished_at=datetime.now(),
            closure_date=item.closure_date,
            details=item.details,
            process_number=item.process_number,
            group_company=getattr(summary, "group_company", "") if summary else "",
            legal_department=getattr(summary, "legal_department", "") if summary else "",
            responsible_lawyer=getattr(summary, "responsible_lawyer", "") if summary else "",
            evidence_path=evidence,
            original=item.original,
        )
