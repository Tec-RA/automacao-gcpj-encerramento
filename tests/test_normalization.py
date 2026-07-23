from gcpj_automation.normalization import normalize_header, normalize_npc, normalize_text


def test_normalize_text_removes_accents_and_case():
    assert normalize_text(" Extinto sem merito ") == "EXTINTO SEM MERITO"
    assert normalize_text("Extinto sem mérito") == "EXTINTO SEM MERITO"


def test_normalize_header():
    assert normalize_header("Número do Processo") == "NUMERO DO PROCESSO"


def test_normalize_npc_from_excel_float():
    assert normalize_npc(1600000001.0) == "1600000001"
    assert normalize_npc("16.000.000-01") == "1600000001"


def test_normalize_npc_from_scientific_notation():
    assert normalize_npc("1.600000001E+09") == "1600000001"
