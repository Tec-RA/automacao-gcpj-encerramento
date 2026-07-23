from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gcpj_automation.browser.chrome import launch_debug_chrome
from gcpj_automation.browser.session import probe_connection
from gcpj_automation.config import load_settings
from gcpj_automation.logging_setup import configure_logging
from gcpj_automation.models import ColumnMapping, ExecutionMode, ItemStatus, RowFilters
from gcpj_automation.repositories.execution_repository import ExecutionRepository
from gcpj_automation.services.diagnostics import collect_diagnostic
from gcpj_automation.services.reason_mapper import ReasonMapper
from gcpj_automation.services.report import build_result_workbook, save_report
from gcpj_automation.services.runner import AutomationRunner
from gcpj_automation.services.spreadsheet import (
    available_template_fields,
    build_closure_items,
    guess_column_mapping,
    read_uploaded_workbook,
    validate_column_mapping,
)
from gcpj_automation.ui.components import (
    issues_to_frame,
    render_brand,
    render_connection_status,
    render_result_metrics,
    render_status_card,
    results_to_frame,
)
from gcpj_automation.ui.styles import APP_CSS


st.set_page_config(
    page_title="Encerramento de Pastas - GCPJ",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

settings = load_settings()
logger = configure_logging(settings.paths.logs)
repository = ExecutionRepository(settings.paths.database)
reason_mapper = ReasonMapper(settings.reason_mapping_path)
runner = AutomationRunner(settings, repository, logger)


def init_state() -> None:
    defaults = {
        "connection_status": None,
        "last_results": [],
        "last_report_bytes": None,
        "last_report_name": "",
        "last_execution_id": "",
        "run_logs": [],
        "diagnostic_bytes": None,
        "diagnostic_name": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def select_column(
    label: str,
    columns: list[str],
    guess: str | None,
    key: str,
    required: bool,
) -> str | None:
    options = columns if required else ["(nao usar)"] + columns
    selected = guess if guess in options else options[0]
    value = st.selectbox(
        label,
        options=options,
        index=options.index(selected),
        key=key,
    )
    return None if value == "(nao usar)" else value


def render_sidebar() -> None:
    with st.sidebar:
        render_brand()
        st.markdown("### Fluxo desta versao")
        st.markdown(
            "1. Abrir o Chrome dedicado  \n"
            "2. Entrar no GCPJ pela extensao  \n"
            "3. Enviar a planilha  \n"
            "4. Validar e preencher os encerramentos  \n"
            "5. Baixar o relatorio"
        )
        st.divider()
        st.caption("Perfil de automacao")
        st.code(str(settings.chrome.user_data_dir), language=None)
        st.caption(f"CDP: {settings.chrome.cdp_url}")
        st.divider()
        st.caption("Versao 0.1.0 | Execucao local")


init_state()
render_sidebar()

st.title("⚖️ Encerramento de Pastas - GCPJ")
st.caption(
    "Aplicacao local em Streamlit + Playwright, conectada ao Chrome debugavel na porta 9222."
)

st.markdown('<div class="step-title">1. Preparar o navegador</div>', unsafe_allow_html=True)
button_columns = st.columns([1, 1, 1, 2])
with button_columns[0]:
    if st.button("🚀 Abrir Chrome GCPJ", use_container_width=True, type="primary"):
        try:
            result = launch_debug_chrome(settings.chrome)
            st.session_state.connection_status = probe_connection(settings)
            st.success(result.message)
        except Exception as exc:
            logger.exception("Falha ao abrir o Chrome: %s", exc)
            st.error(str(exc))
with button_columns[1]:
    if st.button("🔐 Verificar conexao", use_container_width=True):
        st.session_state.connection_status = probe_connection(settings)
        if st.session_state.connection_status.authenticated_gcpj_found:
            st.success("GCPJ autenticado localizado.")
        else:
            st.warning(st.session_state.connection_status.message)
with button_columns[2]:
    if st.button("🧭 Gerar diagnostico", use_container_width=True):
        try:
            st.session_state.diagnostic_bytes = collect_diagnostic(settings)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.diagnostic_name = f"diagnostico_gcpj_{stamp}.json"
            st.success("Diagnostico gerado sem copiar valores dos campos de texto.")
        except Exception as exc:
            logger.exception("Falha no diagnostico: %s", exc)
            st.error(str(exc))
with button_columns[3]:
    st.markdown(
        '<div class="safe-box"><b>Primeiro uso:</b> execute apenas uma linha no modo '
        '<b>Preencher sem salvar</b>. O envio real fica protegido por confirmacao adicional.</div>',
        unsafe_allow_html=True,
    )

if st.session_state.diagnostic_bytes:
    st.download_button(
        "Baixar diagnostico de seletores",
        data=st.session_state.diagnostic_bytes,
        file_name=st.session_state.diagnostic_name,
        mime="application/json",
    )

status_columns = st.columns(4)
with status_columns[0]:
    render_connection_status(st.session_state.connection_status)
with status_columns[1]:
    render_status_card(
        "Porta CDP",
        str(settings.chrome.debug_port),
        settings.chrome.debug_host,
    )
with status_columns[2]:
    render_status_card(
        "Perfil Chrome",
        settings.chrome.user_data_dir.name or "chrome_gcpj_debug",
        "Perfil separado do Chrome normal",
    )
with status_columns[3]:
    render_status_card(
        "Seguranca",
        "Sem credenciais",
        "A aplicacao usa a sessao ja autenticada",
    )

st.divider()
st.markdown('<div class="step-title">2. Carregar e conferir a planilha</div>', unsafe_allow_html=True)

upload_column, template_column = st.columns([3, 1])
with upload_column:
    uploaded_file = st.file_uploader(
        "Selecione a planilha de encerramentos",
        type=["xlsx", "xlsm", "xls", "csv"],
        help="A versao mostrada no video utiliza principalmente as colunas NPC e ATO.",
    )
with template_column:
    template_path = PROJECT_ROOT / "templates" / "modelo_planilha_encerramento.xlsx"
    st.caption("Modelo de referencia")
    if template_path.exists():
        st.download_button(
            "📥 Baixar modelo Excel",
            data=template_path.read_bytes(),
            file_name=template_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if uploaded_file is None:
    st.info("Envie uma planilha para liberar o mapeamento de colunas e a execucao.")
else:
    try:
        workbook_sheets = read_uploaded_workbook(uploaded_file.getvalue(), uploaded_file.name)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    sheet_names = list(workbook_sheets)
    selected_sheet = st.selectbox("Aba da planilha", sheet_names)
    source_frame = workbook_sheets[selected_sheet].copy()
    source_frame.columns = [str(column).strip() for column in source_frame.columns]
    columns = [str(column) for column in source_frame.columns]
    if not columns:
        st.error("A aba selecionada nao possui colunas.")
        st.stop()
    guesses = guess_column_mapping(source_frame.columns)

    with st.expander("Mapeamento das colunas", expanded=True):
        map_columns = st.columns(3)
        with map_columns[0]:
            npc_column = select_column(
                "Coluna do NPC (obrigatoria)", columns, guesses.get("npc"), "map_npc", True
            )
            ato_column = select_column(
                "Coluna do ATO (obrigatoria)", columns, guesses.get("ato"), "map_ato", True
            )
        with map_columns[1]:
            status_column = select_column(
                "Coluna de STATUS", columns, guesses.get("status"), "map_status", False
            )
            goal_column = select_column(
                "Coluna CONTA PRA META",
                columns,
                guesses.get("count_for_goal"),
                "map_goal",
                False,
            )
        with map_columns[2]:
            process_column = select_column(
                "Numero do processo judicial",
                columns,
                guesses.get("process_number"),
                "map_process",
                False,
            )
            details_column = select_column(
                "Detalhes/observacao",
                columns,
                guesses.get("details"),
                "map_details",
                False,
            )

    mapping = ColumnMapping(
        npc=npc_column or "",
        ato=ato_column or "",
        status=status_column,
        details=details_column,
        process_number=process_column,
        count_for_goal=goal_column,
    )
    mapping_errors = validate_column_mapping(source_frame, mapping)
    if mapping_errors:
        for error in mapping_errors:
            st.error(error)
        st.stop()

    preview_columns = [column for column in [npc_column, ato_column, status_column, goal_column, process_column] if column]
    st.dataframe(
        source_frame[preview_columns].head(30),
        use_container_width=True,
        hide_index=True,
        height=340,
    )

    st.markdown('<div class="step-title">3. Configurar o processamento</div>', unsafe_allow_html=True)
    configuration_columns = st.columns([1, 1, 1, 1])
    with configuration_columns[0]:
        closure_date = st.date_input("Data do encerramento", value=date.today(), format="DD/MM/YYYY")
    with configuration_columns[1]:
        mode_labels = {mode.label: mode for mode in ExecutionMode}
        selected_mode_label = st.selectbox(
            "Modo de execucao",
            list(mode_labels),
            index=list(mode_labels).index(ExecutionMode.FILL_ONLY.label),
        )
        selected_mode = mode_labels[selected_mode_label]
    with configuration_columns[2]:
        maximum_rows = max(1, len(source_frame))
        row_limit = st.number_input(
            "Limite de linhas neste teste",
            min_value=1,
            max_value=maximum_rows,
            value=1,
            step=1,
        )
    with configuration_columns[3]:
        capture_evidence = st.checkbox(
            "Salvar capturas de evidencia",
            value=True,
            help="As capturas ficam somente no computador local.",
        )

    filter_columns = st.columns(3)
    with filter_columns[0]:
        use_status_filter = st.checkbox(
            "Processar somente STATUS = OK",
            value=bool(status_column),
            disabled=not bool(status_column),
        )
    with filter_columns[1]:
        only_goal = st.checkbox(
            "Somente CONTA PRA META = SIM",
            value=False,
            disabled=not bool(goal_column),
        )
    with filter_columns[2]:
        skip_duplicates = st.checkbox("Ignorar NPC duplicado", value=True)

    template_fields = available_template_fields(source_frame)
    details_template = st.text_area(
        "Detalhes do encerramento (opcional)",
        value="",
        placeholder="Ex.: Encerramento solicitado conforme ATO {ato}. Processo {processo}.",
        help="Campos disponiveis: " + ", ".join(f"{{{field}}}" for field in template_fields[:30]),
    )

    filters = RowFilters(
        required_status="OK" if use_status_filter and status_column else None,
        only_count_for_goal=only_goal and bool(goal_column),
        skip_duplicate_npc=skip_duplicates,
        row_limit=int(row_limit),
    )

    try:
        build_result = build_closure_items(
            frame=source_frame,
            mapping=mapping,
            reason_mapper=reason_mapper,
            closure_date=closure_date,
            filters=filters,
            details_template=details_template,
        )
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    metric_columns = st.columns(4)
    metric_columns[0].metric("Linhas na aba", len(source_frame))
    metric_columns[1].metric("Prontas para processar", len(build_result.items))
    metric_columns[2].metric("Ignoradas", build_result.skipped_rows)
    metric_columns[3].metric("Pendencias", len(build_result.issues))

    if build_result.items:
        item_preview = pd.DataFrame(
            [
                {
                    "Linha": item.row_number,
                    "NPC": item.npc,
                    "ATO da planilha": item.ato,
                    "Motivo no GCPJ": item.gcpj_reason,
                    "Data": item.closure_date.strftime("%d/%m/%Y"),
                    "Detalhes": item.details,
                }
                for item in build_result.items
            ]
        )
        st.dataframe(item_preview, use_container_width=True, hide_index=True)

    if build_result.issues:
        with st.expander("Pendencias e linhas ignoradas", expanded=True):
            st.dataframe(
                issues_to_frame(build_result.issues),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown('<div class="step-title">4. Executar no GCPJ</div>', unsafe_allow_html=True)
    submit_authorized = True
    if selected_mode is ExecutionMode.SUBMIT:
        st.warning(
            "Este modo aciona o botao SALVAR do GCPJ. O video termina antes da mensagem final, "
            "por isso a confirmacao de sucesso ainda usa uma verificacao generica."
        )
        reviewed = st.checkbox(
            "Revisei os NPCs, os ATOs e a data de encerramento desta execucao.",
            value=False,
        )
        confirmation = st.text_input(
            "Digite ENCERRAR para liberar o envio real",
            value="",
            type="default",
        )
        submit_authorized = reviewed and confirmation.strip().upper() == "ENCERRAR"

    connection_ready = bool(
        st.session_state.connection_status
        and st.session_state.connection_status.authenticated_gcpj_found
    )
    if not connection_ready:
        st.info(
            "Antes de executar, clique em Verificar conexao. Se necessario, abra o Chrome, "
            "acesse a extensao e deixe o GCPJ no Menu Principal."
        )

    run_disabled = not build_result.items or not submit_authorized
    if st.button(
        "▶️ Iniciar automacao",
        type="primary",
        use_container_width=True,
        disabled=run_disabled,
    ):
        st.session_state.connection_status = probe_connection(settings)
        if not st.session_state.connection_status.authenticated_gcpj_found:
            st.error(st.session_state.connection_status.message)
            st.stop()

        progress_bar = st.progress(0, text="Preparando a execucao...")
        log_placeholder = st.empty()
        st.session_state.run_logs = []

        def on_progress(current, total, result, message):
            percent = int((current / total) * 100) if total else 100
            progress_bar.progress(percent, text=f"{current}/{total} - {message}")
            timestamp = datetime.now().strftime("%H:%M:%S")
            if result is not None:
                line = f"[{timestamp}] NPC {result.npc} | {result.status.value} | {result.message}"
            else:
                line = f"[{timestamp}] {message}"
            st.session_state.run_logs.append(line)
            log_placeholder.code("\n".join(st.session_state.run_logs[-120:]), language=None)

        try:
            execution_id, results, started_at, finished_at = runner.run(
                items=build_result.items,
                mode=selected_mode,
                capture_evidence=capture_evidence,
                progress_callback=on_progress,
            )
            report_bytes = build_result_workbook(
                results=results,
                execution_id=execution_id,
                mode=selected_mode,
                started_at=started_at,
                finished_at=finished_at,
            )
            report_name = f"resultado_{execution_id}.xlsx"
            report_path = save_report(report_bytes, settings.paths.exports / report_name)
            if any(result.status is ItemStatus.ERROR for result in results):
                final_status = "CONCLUIDO_COM_ERROS"
            elif any(
                result.status is ItemStatus.SUBMITTED_UNCONFIRMED for result in results
            ):
                final_status = "CONCLUIDO_COM_PENDENCIAS"
            else:
                final_status = "CONCLUIDO"
            repository.finish_execution(
                execution_id,
                finished_at,
                final_status,
                str(report_path),
            )
            st.session_state.last_results = results
            st.session_state.last_report_bytes = report_bytes
            st.session_state.last_report_name = report_name
            st.session_state.last_execution_id = execution_id
            progress_bar.progress(100, text="Execucao concluida.")
            st.success(f"Execucao {execution_id} concluida.")
        except Exception as exc:
            logger.exception("Falha na execucao: %s", exc)
            progress_bar.empty()
            st.error(f"A execucao foi interrompida: {exc}")

if st.session_state.last_results:
    st.divider()
    st.markdown('<div class="step-title">5. Resultado da ultima execucao</div>', unsafe_allow_html=True)
    render_result_metrics(st.session_state.last_results)
    st.dataframe(
        results_to_frame(st.session_state.last_results),
        use_container_width=True,
        hide_index=True,
        height=420,
    )
    st.download_button(
        "📥 Baixar relatorio Excel",
        data=st.session_state.last_report_bytes,
        file_name=st.session_state.last_report_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

st.divider()
with st.expander("Historico local de execucoes"):
    history = repository.recent_executions(limit=30)
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.caption("Nenhuma execucao registrada neste computador.")

with st.expander("Logs da aplicacao"):
    log_file = settings.paths.logs / "gcpj_automation.log"
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(lines[-250:]), language=None)
    else:
        st.caption("O arquivo de log ainda nao foi criado.")
