from datetime import datetime
from pathlib import Path

from gcpj_automation.models import ExecutionMode, ItemResult, ItemStatus
from gcpj_automation.repositories.execution_repository import ExecutionRepository


def test_repository_round_trip(tmp_path: Path):
    repository = ExecutionRepository(tmp_path / "db.sqlite")
    now = datetime(2026, 7, 22, 10, 0, 0)
    repository.start_execution("EXEC1", ExecutionMode.VALIDATE, now, 1)
    repository.save_item(
        "EXEC1",
        ItemResult(
            row_number=2,
            npc="1600000001",
            ato="IMPROCEDENTE",
            gcpj_reason="IMPROCEDENCIA",
            status=ItemStatus.VALIDATED,
            message="OK",
            started_at=now,
            finished_at=now,
        ),
    )
    repository.finish_execution("EXEC1", now, "CONCLUIDO")
    history = repository.recent_executions()
    assert history[0]["execution_id"] == "EXEC1"
    assert history[0]["status"] == "CONCLUIDO"
