"""Data models used by the application."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class ExecutionMode(str, Enum):
    VALIDATE = "VALIDAR"
    FILL_ONLY = "PREENCHER_SEM_SALVAR"
    SUBMIT = "SOLICITAR_ENCERRAMENTO"

    @property
    def label(self) -> str:
        return {
            self.VALIDATE: "Apenas validar pastas",
            self.FILL_ONLY: "Preencher sem salvar",
            self.SUBMIT: "Solicitar encerramento",
        }[self]


class ItemStatus(str, Enum):
    PENDING = "PENDENTE"
    VALIDATED = "VALIDADO"
    FILLED = "PREENCHIDO"
    SUBMITTED = "SOLICITADO"
    SUBMITTED_UNCONFIRMED = "SOLICITADO_SEM_CONFIRMACAO"
    SKIPPED = "IGNORADO"
    ERROR = "ERRO"


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    npc: str
    ato: str
    status: str | None = None
    details: str | None = None
    process_number: str | None = None
    count_for_goal: str | None = None


@dataclass(frozen=True, slots=True)
class RowFilters:
    required_status: str | None = None
    only_count_for_goal: bool = False
    skip_duplicate_npc: bool = True
    row_limit: int | None = None


@dataclass(slots=True)
class ClosureItem:
    row_number: int
    npc: str
    ato: str
    gcpj_reason: str
    closure_date: date
    details: str = ""
    process_number: str = ""
    original: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessSummary:
    npc: str
    group_company: str = ""
    legal_department: str = ""
    responsible_lawyer: str = ""


@dataclass(slots=True)
class ItemResult:
    row_number: int
    npc: str
    ato: str
    gcpj_reason: str
    status: ItemStatus
    message: str
    started_at: datetime
    finished_at: datetime
    closure_date: date | None = None
    details: str = ""
    process_number: str = ""
    group_company: str = ""
    legal_department: str = ""
    responsible_lawyer: str = ""
    evidence_path: str = ""
    original: dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> float:
        return round((self.finished_at - self.started_at).total_seconds(), 3)

    def to_record(self) -> dict[str, Any]:
        record = dict(self.original)
        record.update(
            {
                "_LINHA_ORIGEM": self.row_number,
                "_NPC": self.npc,
                "_ATO": self.ato,
                "_MOTIVO_GCPJ": self.gcpj_reason,
                "_STATUS_AUTOMACAO": self.status.value,
                "_MENSAGEM_AUTOMACAO": self.message,
                "_DATA_ENCERRAMENTO": (
                    self.closure_date.strftime("%d/%m/%Y") if self.closure_date else ""
                ),
                "_DETALHES_ENCERRAMENTO": self.details,
                "_INICIO_AUTOMACAO": self.started_at.isoformat(timespec="seconds"),
                "_FIM_AUTOMACAO": self.finished_at.isoformat(timespec="seconds"),
                "_DURACAO_SEGUNDOS": self.elapsed_seconds,
                "_PROCESSO_JUDICIAL": self.process_number,
                "_EMPRESA_GRUPO": self.group_company,
                "_DEPARTAMENTO_JURIDICO": self.legal_department,
                "_ADVOGADO_RESPONSAVEL": self.responsible_lawyer,
                "_EVIDENCIA": self.evidence_path,
            }
        )
        return record


@dataclass(slots=True)
class SpreadsheetIssue:
    row_number: int | None
    severity: str
    message: str


@dataclass(slots=True)
class BuildItemsResult:
    items: list[ClosureItem]
    issues: list[SpreadsheetIssue]
    skipped_rows: int = 0


@dataclass(slots=True)
class BrowserPageInfo:
    title: str
    url: str
    is_gcpj: bool


@dataclass(slots=True)
class ConnectionStatus:
    debug_port_open: bool
    browser_product: str = ""
    websocket_url: str = ""
    pages: list[BrowserPageInfo] = field(default_factory=list)
    authenticated_gcpj_found: bool = False
    message: str = ""


@dataclass(slots=True)
class ExecutionSummary:
    execution_id: str
    mode: ExecutionMode
    started_at: datetime
    finished_at: datetime
    total: int
    counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["started_at"] = self.started_at.isoformat(timespec="seconds")
        data["finished_at"] = self.finished_at.isoformat(timespec="seconds")
        return data
