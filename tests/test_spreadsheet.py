from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from gcpj_automation.models import ColumnMapping, RowFilters
from gcpj_automation.services.reason_mapper import ReasonMapper
from gcpj_automation.services.spreadsheet import (
    build_closure_items,
    guess_column_mapping,
    read_uploaded_workbook,
    validate_column_mapping,
)


def make_mapping(tmp_path: Path) -> ReasonMapper:
    path = tmp_path / "mapping.yaml"
    path.write_text(
        """
mappings:
  IMPROCEDENTE: IMPROCEDENCIA
  EXTINTO SEM MERITO: EXTINTO SEM RESOLUCAO DE MERITO
blocked:
  AUTOR RECORREU: Recurso pendente.
""",
        encoding="utf-8",
    )
    return ReasonMapper(path)


def test_read_xlsx_and_guess_columns():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Resultado"
    sheet.append(["NPC", "ATO", "STATUS", "CONTA PRA META"])
    sheet.append([1600000001, "IMPROCEDENTE", "OK", "SIM"])
    buffer = BytesIO()
    workbook.save(buffer)

    sheets = read_uploaded_workbook(buffer.getvalue(), "teste.xlsx")
    frame = sheets["Resultado"]
    guesses = guess_column_mapping(frame.columns)
    assert guesses["npc"] == "NPC"
    assert guesses["ato"] == "ATO"
    assert guesses["status"] == "STATUS"


def test_build_items_filters_and_maps(tmp_path: Path):
    frame = pd.DataFrame(
        [
            {
                "NPC": 1600000001,
                "ATO": "IMPROCEDENTE",
                "STATUS": "OK",
                "CONTA PRA META": "SIM",
                "Numero do Processo": "0000000-00.2026.8.00.0000",
            },
            {
                "NPC": 2600000002,
                "ATO": "AUTOR RECORREU",
                "STATUS": "OK",
                "CONTA PRA META": "SIM",
                "Numero do Processo": "0000000-01.2026.8.00.0000",
            },
        ]
    )
    result = build_closure_items(
        frame=frame,
        mapping=ColumnMapping(
            npc="NPC",
            ato="ATO",
            status="STATUS",
            process_number="Numero do Processo",
            count_for_goal="CONTA PRA META",
        ),
        reason_mapper=make_mapping(tmp_path),
        closure_date=date(2026, 7, 22),
        filters=RowFilters(required_status="OK", only_count_for_goal=True),
        details_template="Encerramento conforme {ato} - {processo}",
    )
    assert len(result.items) == 1
    assert result.items[0].npc == "1600000001"
    assert result.items[0].gcpj_reason == "IMPROCEDENCIA"
    assert "0000000-00.2026.8.00.0000" in result.items[0].details
    assert any("recurso" in issue.message.lower() for issue in result.issues)


def test_read_semicolon_csv():
    payload = "NPC;ATO;STATUS\n1600000001;IMPROCEDENTE;OK\n".encode("utf-8")
    sheets = read_uploaded_workbook(payload, "teste.csv")
    assert list(sheets["CSV"].columns) == ["NPC", "ATO", "STATUS"]
    assert str(sheets["CSV"].iloc[0]["NPC"]) == "1600000001"


def test_original_values_are_report_safe(tmp_path: Path):
    frame = pd.DataFrame(
        [{"NPC": 1600000001, "ATO": "IMPROCEDENTE", "STATUS": "OK", "Opcional": pd.NA}]
    )
    result = build_closure_items(
        frame=frame,
        mapping=ColumnMapping(npc="NPC", ato="ATO", status="STATUS"),
        reason_mapper=make_mapping(tmp_path),
        closure_date=date(2026, 7, 22),
        filters=RowFilters(required_status="OK"),
    )
    assert result.items[0].original["Opcional"] == ""


def test_rejects_same_column_for_npc_and_ato():
    frame = pd.DataFrame([{"NPC": "1600000001"}])
    errors = validate_column_mapping(frame, ColumnMapping(npc="NPC", ato="NPC"))
    assert any("mesma coluna" in error for error in errors)
