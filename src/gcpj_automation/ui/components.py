"""Reusable Streamlit components."""

from __future__ import annotations

import html
from collections import Counter
from collections.abc import Iterable

import pandas as pd
import streamlit as st

from ..models import ConnectionStatus, ItemResult, SpreadsheetIssue


def render_brand() -> None:
    st.markdown(
        """
        <div class="brand-card">
            <div class="brand-monogram">RA</div>
            <div class="brand-name">Ribeiro de Andrade</div>
            <div style="color:#6b7280;font-size:.82rem;margin-top:3px;">Automacao juridica local</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(label: str, value: str, detail: str = "") -> None:
    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-label">{html.escape(label)}</div>
            <div class="status-value">{html.escape(value)}</div>
            <div class="status-detail">{html.escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_connection_status(status: ConnectionStatus | None) -> None:
    if status is None:
        render_status_card("Conexao", "Nao verificada", "Use o botao Verificar conexao.")
        return
    if not status.debug_port_open:
        render_status_card("Conexao", "Chrome fechado", status.message)
    elif status.authenticated_gcpj_found:
        render_status_card("Conexao", "GCPJ conectado", status.browser_product or status.message)
    else:
        render_status_card("Conexao", "Atencao", status.message)


def issues_to_frame(issues: Iterable[SpreadsheetIssue]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Linha": issue.row_number or "-",
                "Nivel": issue.severity,
                "Mensagem": issue.message,
            }
            for issue in issues
        ]
    )


def results_to_frame(results: Iterable[ItemResult]) -> pd.DataFrame:
    return pd.DataFrame([result.to_record() for result in results])


def render_result_metrics(results: list[ItemResult]) -> None:
    counts = Counter(result.status.value for result in results)
    columns = st.columns(4)
    columns[0].metric("Total", len(results))
    columns[1].metric("Solicitados", counts.get("SOLICITADO", 0))
    columns[2].metric(
        "Preenchidos/validados",
        counts.get("PREENCHIDO", 0) + counts.get("VALIDADO", 0),
    )
    columns[3].metric("Erros", counts.get("ERRO", 0))
