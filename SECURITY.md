# Politica de seguranca

## Dados tratados

A aplicacao pode processar numeros de pastas, numeros de processos, observacoes internas e capturas de tela do GCPJ. Esses dados permanecem no computador em que o Streamlit e executado.

## Regras

- Nao inserir credenciais no repositorio.
- Nao versionar `data/`, `evidence/`, `logs/` ou `.streamlit/secrets.toml`.
- Usar um perfil Chrome exclusivo em `C:\chrome_gcpj_debug`.
- Limitar o acesso ao computador e ao banco SQLite.
- Usar o modo `Preencher sem salvar` durante homologacao.
- Revisar manualmente qualquer linha com motivo nao mapeado, recurso, divergencia de NPC ou mensagem nao reconhecida.
- Nao desativar autenticacao, CAPTCHA ou controles do GCPJ.

## Incidentes

Em caso de envio incorreto:

1. Interromper a execucao.
2. Preservar o log e o relatorio da execucao.
3. Identificar o `execution_id` no historico.
4. Revisar as capturas locais.
5. Comunicar o responsavel pelo processo e seguir o procedimento interno do escritorio.
