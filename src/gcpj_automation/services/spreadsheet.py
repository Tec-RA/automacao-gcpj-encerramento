"""Spreadsheet parsing, column detection and row validation."""

from __future__ import annotations

from collections import Counter
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from ..exceptions import SpreadsheetValidationError
from ..models import (
    BuildItemsResult,
    ClosureItem,
    ColumnMapping,
    RowFilters,
    SpreadsheetIssue,
)
from ..normalization import is_blank, is_yes, normalize_header, normalize_npc, normalize_text
from .reason_mapper import ReasonMapper


COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "npc": (
        "NPC",
        "NUMERO PROCESSO BRADESCO",
        "N PROCESSO BRADESCO",
        "PASTA GCPJ",
        "PASTA",
    ),
    "ato": ("ATO", "RESULTADO", "MOTIVO", "RESULTADO PROCESSO"),
    "status": ("STATUS", "SITUACAO", "STATUS AUTOMACAO"),
    "details": (
        "DETALHES ENCERRAMENTO",
        "DETALHES",
        "OBSERVACAO ABERTURA",
        "OBSERVACAO",
    ),
    "process_number": (
        "NUMERO DO PROCESSO",
        "NUMERO PROCESSO",
        "PROCESSO JUDICIAL",
        "CNJ",
    ),
    "count_for_goal": ("CONTA PRA META", "CONTA PARA META", "META"),
}


def read_uploaded_workbook(file_bytes: bytes, filename: str) -> dict[str, pd.DataFrame]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                frame = pd.read_csv(
                    BytesIO(file_bytes),
                    encoding=encoding,
                    dtype=object,
                    sep=None,
                    engine="python",
                )
                return {"CSV": frame}
            except UnicodeDecodeError:
                continue
        raise SpreadsheetValidationError("Nao foi possivel identificar a codificacao do CSV.")
    if suffix not in {".xlsx", ".xlsm", ".xls"}:
        raise SpreadsheetValidationError("Formato nao suportado. Use XLSX, XLSM, XLS ou CSV.")
    try:
        engine = "xlrd" if suffix == ".xls" else "openpyxl"
        workbook = pd.ExcelFile(BytesIO(file_bytes), engine=engine)
        return {
            sheet: pd.read_excel(workbook, sheet_name=sheet, dtype=object)
            for sheet in workbook.sheet_names
        }
    except ImportError as exc:
        raise SpreadsheetValidationError(
            "Para arquivos XLS antigos, instale a dependencia xlrd ou salve como XLSX."
        ) from exc
    except Exception as exc:
        raise SpreadsheetValidationError(f"Falha ao ler a planilha: {exc}") from exc


def guess_column_mapping(columns: list[str] | pd.Index) -> dict[str, str | None]:
    available = [str(column) for column in columns]
    normalized = {column: normalize_header(column) for column in available}
    guesses: dict[str, str | None] = {}

    for field, aliases in COLUMN_ALIASES.items():
        normalized_aliases = [normalize_header(alias) for alias in aliases]
        exact = next(
            (
                column
                for column, normalized_column in normalized.items()
                if normalized_column in normalized_aliases
            ),
            None,
        )
        if exact:
            guesses[field] = exact
            continue
        partial = next(
            (
                column
                for column, normalized_column in normalized.items()
                if any(
                    alias in normalized_column or normalized_column in alias
                    for alias in normalized_aliases
                )
            ),
            None,
        )
        guesses[field] = partial
    return guesses


def validate_column_mapping(frame: pd.DataFrame, mapping: ColumnMapping) -> list[str]:
    errors: list[str] = []
    for label, column in (("NPC", mapping.npc), ("ATO", mapping.ato)):
        if column not in frame.columns:
            errors.append(f"Coluna obrigatoria {label} nao encontrada: {column}")
    if mapping.npc and mapping.ato and mapping.npc == mapping.ato:
        errors.append("NPC e ATO nao podem usar a mesma coluna.")
    for optional in (
        mapping.status,
        mapping.details,
        mapping.process_number,
        mapping.count_for_goal,
    ):
        if optional and optional not in frame.columns:
            errors.append(f"Coluna configurada nao encontrada: {optional}")
    return errors


class _SafeFormatDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def _cell_safe_value(value: Any) -> Any:
    """Convert pandas/numpy values into openpyxl- and JSON-friendly values."""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            value = item_method()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (str, int, float, bool, date)):
        return value
    return str(value)


def _render_details(template: str, row: pd.Series, mapping: ColumnMapping) -> str:
    if not template:
        if mapping.details and not is_blank(row.get(mapping.details)):
            return str(row.get(mapping.details)).strip()
        return ""

    values: dict[str, Any] = {
        "npc": normalize_npc(row.get(mapping.npc)),
        "ato": "" if is_blank(row.get(mapping.ato)) else str(row.get(mapping.ato)).strip(),
        "processo": (
            ""
            if not mapping.process_number or is_blank(row.get(mapping.process_number))
            else str(row.get(mapping.process_number)).strip()
        ),
        "detalhes": (
            ""
            if not mapping.details or is_blank(row.get(mapping.details))
            else str(row.get(mapping.details)).strip()
        ),
    }
    values.update({normalize_header(column).lower().replace(" ", "_"): value for column, value in row.items()})
    try:
        return template.format_map(_SafeFormatDict(values)).strip()
    except (ValueError, KeyError) as exc:
        raise SpreadsheetValidationError(f"Modelo de detalhes invalido: {exc}") from exc


def available_template_fields(frame: pd.DataFrame) -> list[str]:
    fields = ["npc", "ato", "processo", "detalhes"]
    fields.extend(normalize_header(column).lower().replace(" ", "_") for column in frame.columns)
    return sorted(set(fields))


def build_closure_items(
    frame: pd.DataFrame,
    mapping: ColumnMapping,
    reason_mapper: ReasonMapper,
    closure_date: date,
    filters: RowFilters,
    details_template: str = "",
) -> BuildItemsResult:
    errors = validate_column_mapping(frame, mapping)
    if errors:
        raise SpreadsheetValidationError("; ".join(errors))

    issues: list[SpreadsheetIssue] = []
    items: list[ClosureItem] = []
    skipped = 0
    seen_npcs: set[str] = set()

    for zero_index, (_, row) in enumerate(frame.iterrows(), start=0):
        excel_row = zero_index + 2
        npc = normalize_npc(row.get(mapping.npc))
        ato = "" if is_blank(row.get(mapping.ato)) else str(row.get(mapping.ato)).strip()

        if not npc and not ato:
            skipped += 1
            continue
        if not npc:
            issues.append(SpreadsheetIssue(excel_row, "ERRO", "NPC vazio ou invalido."))
            skipped += 1
            continue
        if not ato:
            issues.append(SpreadsheetIssue(excel_row, "ERRO", f"ATO vazio para o NPC {npc}."))
            skipped += 1
            continue
        if len(npc) < 6:
            issues.append(SpreadsheetIssue(excel_row, "ERRO", f"NPC aparentemente invalido: {npc}."))
            skipped += 1
            continue

        if filters.required_status and mapping.status:
            row_status = normalize_text(row.get(mapping.status))
            if row_status != normalize_text(filters.required_status):
                issues.append(
                    SpreadsheetIssue(
                        excel_row,
                        "INFO",
                        f"Linha ignorada porque STATUS e diferente de {filters.required_status}.",
                    )
                )
                skipped += 1
                continue

        if filters.only_count_for_goal and mapping.count_for_goal:
            if not is_yes(row.get(mapping.count_for_goal)):
                issues.append(
                    SpreadsheetIssue(
                        excel_row,
                        "INFO",
                        "Linha ignorada porque CONTA PRA META nao e SIM.",
                    )
                )
                skipped += 1
                continue

        if filters.skip_duplicate_npc and npc in seen_npcs:
            issues.append(SpreadsheetIssue(excel_row, "AVISO", f"NPC duplicado ignorado: {npc}."))
            skipped += 1
            continue
        seen_npcs.add(npc)

        resolution = reason_mapper.resolve(ato)
        if resolution.blocked:
            issues.append(SpreadsheetIssue(excel_row, "AVISO", resolution.message))
            skipped += 1
            continue
        if not resolution.gcpj_reason:
            issues.append(SpreadsheetIssue(excel_row, "ERRO", resolution.message))
            skipped += 1
            continue

        process_number = ""
        if mapping.process_number and not is_blank(row.get(mapping.process_number)):
            process_number = str(row.get(mapping.process_number)).strip()

        details = _render_details(details_template, row, mapping)
        original = {
            str(column): _cell_safe_value(value)
            for column, value in row.to_dict().items()
        }
        items.append(
            ClosureItem(
                row_number=excel_row,
                npc=npc,
                ato=ato,
                gcpj_reason=resolution.gcpj_reason,
                closure_date=closure_date,
                details=details,
                process_number=process_number,
                original=original,
            )
        )
        if filters.row_limit and len(items) >= filters.row_limit:
            break

    counts = Counter(issue.severity for issue in issues)
    if not items and counts.get("ERRO", 0):
        issues.append(
            SpreadsheetIssue(None, "ERRO", "Nenhuma linha valida permaneceu para processamento.")
        )
    return BuildItemsResult(items=items, issues=issues, skipped_rows=skipped)
