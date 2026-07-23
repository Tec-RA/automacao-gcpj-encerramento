# Arquitetura

## Visão geral

```text
Planilha XLSX/CSV
       |
       v
Streamlit local
       |
       +--> validação e mapeamento de ATO
       |
       +--> Playwright via CDP 127.0.0.1:9222
                    |
                    v
          Chrome dedicado + extensão
                    |
                    v
                   GCPJ

Resultados --> SQLite + Excel + logs + evidências PNG
```

## Componentes

- `streamlit_app.py`: orquestra a interface, os controles de segurança e o download dos resultados.
- `browser/chrome.py`: abre o Chrome dedicado e verifica o endpoint CDP.
- `browser/session.py`: conecta o Playwright ao Chrome existente sem encerrar o navegador do usuário.
- `browser/gcpj_page.py`: Page Object com o fluxo de menu, pesquisa, formulário e salvamento, pesquisando também em frames internos.
- `services/spreadsheet.py`: leitura, detecção de colunas, filtros e validação da planilha.
- `services/reason_mapper.py`: traduz o ATO da planilha para a opção do campo Motivo.
- `services/runner.py`: processa o lote, aplica bloqueio de concorrência e registra evidências.
- `repositories/execution_repository.py`: trilha de auditoria SQLite.
- `services/report.py`: memória final em Excel.

## Decisões de segurança

1. Credenciais e tokens não são armazenados.
2. O navegador usa um perfil exclusivo.
3. O modo padrão não aciona `salvar`.
4. O envio real exige revisão, caixa de confirmação e a expressão `ENCERRAR`.
5. Uma tentativa de salvamento com resultado incerto não é repetida automaticamente.
6. Os seletores ficam fora do código para facilitar manutenção sem reescrever o fluxo.
7. Uma trava de arquivo impede duas execuções simultâneas no mesmo computador.

## Modos de execução

- `VALIDAR`: pesquisa a pasta e coleta os dados básicos, sem preencher.
- `PREENCHER_SEM_SALVAR`: preenche data, motivo e detalhes, sem enviar.
- `SOLICITAR_ENCERRAMENTO`: aciona `salvar` uma vez e classifica o retorno.
