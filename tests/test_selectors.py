from pathlib import Path

from gcpj_automation.browser.selectors import SelectorRegistry


def test_selector_registry(tmp_path: Path):
    path = tmp_path / "selectors.yaml"
    path.write_text(
        """
selectors:
  search_button:
    - "input[value='pesquisar']"
""",
        encoding="utf-8",
    )
    registry = SelectorRegistry(path)
    assert registry.get("search_button") == ["input[value='pesquisar']"]
