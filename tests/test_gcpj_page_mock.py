import shutil
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from gcpj_automation.browser.gcpj_page import GCPJClosurePage
from gcpj_automation.browser.selectors import SelectorRegistry
from gcpj_automation.config import (
    AppSettings,
    AutomationSettings,
    ChromeSettings,
    GCPJSettings,
    PathSettings,
)
from gcpj_automation.models import ItemStatus


CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser")


@pytest.mark.skipif(CHROMIUM is None, reason="Chromium local nao disponivel")
def test_page_object_against_mock_gcpj(tmp_path: Path):
    selectors_path = Path(__file__).resolve().parents[1] / "config" / "selectors.yaml"
    mapping_path = Path(__file__).resolve().parents[1] / "config" / "motivo_mapping.yaml"
    settings = AppSettings(
        chrome=ChromeSettings(
            executable=Path(CHROMIUM or "chromium"),
            user_data_dir=tmp_path / "profile",
            debug_host="127.0.0.1",
            debug_port=9222,
            startup_timeout_seconds=1,
        ),
        gcpj=GCPJSettings(
            url_contains="gcpj",
            title_contains="GCPJ",
            timeout_ms=3000,
            navigation_timeout_ms=3000,
            slow_mo_ms=0,
        ),
        paths=PathSettings(
            database=tmp_path / "db.sqlite",
            logs=tmp_path / "logs",
            evidence=tmp_path / "evidence",
            exports=tmp_path / "exports",
            lock_file=tmp_path / "automation.lock",
        ),
        automation=AutomationSettings(
            screenshot_on_success=True,
            screenshot_on_error=True,
            retry_attempts=1,
            success_terms=("REGISTRO SALVO",),
            error_terms=("ERRO",),
        ),
        selectors_path=selectors_path,
        reason_mapping_path=mapping_path,
    )

    html = """
    <!doctype html>
    <html>
      <head><title>GCPJ - Teste</title></head>
      <body>
        <div id="current-user">Usuario Corrente: RIBEIRO DE ANDRADE ADVOGADOS</div>
        <section id="menu">
          <a href="#" id="open-closure">Encerramento de Processos</a>
        </section>
        <section id="search" hidden>
          <table><tr><td>Nº do Processo Bradesco:</td><td><input name="numeroProcesso"></td></tr></table>
          <input type="button" value="pesquisar" id="pesquisar">
        </section>
        <section id="form" hidden>
          <table>
            <tr><td>Nº do Processo Bradesco:</td><td id="npc-display"></td></tr>
            <tr><td>Empresa Grupo:</td><td>237 - BANCO BRADESCO S/A</td></tr>
            <tr><td>Departamento Jurídico:</td><td>4785 - GES.PROC.JUD.TERCEIR</td></tr>
            <tr><td>Advogado Responsável:</td><td>ADVOGADO TESTE</td></tr>
            <tr><td>Data:</td><td><input name="dataEncerramento" readonly></td></tr>
            <tr><td>Motivo:</td><td>
              <select name="motivoEncerramento">
                <option value=""></option>
                <option value="1">IMPROCEDENCIA</option>
                <option value="2">EXTINTO SEM RESOLUCAO DE MERITO</option>
              </select>
            </td></tr>
            <tr><td>Detalhes do Encerramento:</td><td><textarea name="detalhes"></textarea></td></tr>
          </table>
          <input type="button" value="salvar" id="salvar">
          <input type="button" value="voltar" id="voltar">
          <div id="message"></div>
        </section>
        <script>
          const menu = document.querySelector('#menu');
          const search = document.querySelector('#search');
          const form = document.querySelector('#form');
          document.querySelector('#open-closure').onclick = (event) => {
            event.preventDefault(); menu.hidden = true; search.hidden = false;
          };
          document.querySelector('#pesquisar').onclick = () => {
            document.querySelector('#npc-display').textContent = document.querySelector('[name=numeroProcesso]').value;
            search.hidden = true; form.hidden = false;
          };
          document.querySelector('#voltar').onclick = () => { form.hidden = true; search.hidden = false; };
          document.querySelector('#salvar').onclick = () => { document.querySelector('#message').textContent = 'REGISTRO SALVO'; };
        </script>
      </body>
    </html>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=CHROMIUM,
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        page.set_content(
            "<html><head><title>GCPJ - Wrapper</title></head>"
            "<body><iframe id='gcpj-frame'></iframe></body></html>"
        )
        frame_handle = page.locator("#gcpj-frame").element_handle()
        assert frame_handle is not None
        frame = frame_handle.content_frame()
        assert frame is not None
        frame.set_content(html)
        gcpj = GCPJClosurePage(page, settings, SelectorRegistry(selectors_path))
        diagnostic = gcpj.diagnostic_snapshot()
        assert len(diagnostic["frames"]) >= 2

        summary = gcpj.search_process("1600000001")
        assert summary.npc == "1600000001"
        assert "BANCO BRADESCO" in summary.group_company

        gcpj.fill_closure_form("22/07/2026", "IMPROCEDENCIA", "Teste seguro")
        assert frame.locator("input[name=dataEncerramento]").input_value() == "22/07/2026"
        assert (
            frame.locator("select[name=motivoEncerramento] option:checked").inner_text()
            == "IMPROCEDENCIA"
        )
        assert frame.locator("textarea[name=detalhes]").input_value() == "Teste seguro"

        status, message = gcpj.submit()
        assert status is ItemStatus.SUBMITTED
        assert "REGISTRO SALVO" in message
        browser.close()
