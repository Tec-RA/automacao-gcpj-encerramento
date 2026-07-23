from pathlib import Path

from gcpj_automation.services.reason_mapper import ReasonMapper


def test_reason_mapping(tmp_path: Path):
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(
        """
mappings:
  IMPROCEDENTE: IMPROCEDENCIA
  EXTINTO SEM MERITO: EXTINTO SEM RESOLUCAO DE MERITO
blocked:
  AUTOR RECORREU: Recurso pendente.
""",
        encoding="utf-8",
    )
    mapper = ReasonMapper(mapping)
    assert mapper.resolve("improcedente").gcpj_reason == "IMPROCEDENCIA"
    assert mapper.resolve("Extinto sem mérito").gcpj_reason == "EXTINTO SEM RESOLUCAO DE MERITO"
    assert mapper.resolve("autor recorreu").blocked is True
    assert mapper.resolve("procedente").gcpj_reason is None
