# Plano de homologação

## Etapa 1 — conexão

- Abra o Chrome pelo botão do Streamlit.
- Confirme que o perfil é `C:\chrome_gcpj_debug`.
- Faça o login pela extensão.
- Verifique se a tela informa **GCPJ conectado**.

## Etapa 2 — validação de uma pasta

- Use uma planilha com uma linha fictícia ou previamente autorizada.
- Escolha **Apenas validar pastas**.
- Confirme no relatório que o NPC localizado é o mesmo da planilha.

## Etapa 3 — preenchimento sem envio

- Use uma linha com `ATO = IMPROCEDENTE`.
- Escolha **Preencher sem salvar**.
- Confirme visualmente:
  - NPC correto;
  - data correta;
  - motivo `IMPROCEDENCIA`;
  - detalhes, quando utilizados;
  - botão `salvar` não acionado.

Repita com `EXTINTO SEM MÉRITO` e confira o motivo `EXTINTO SEM RESOLUCAO DE MERITO`.

## Etapa 4 — casos bloqueados

Confirme que `AUTOR RECORREU`, `REU RECORREU` e `RECURSO PENDENTE` não entram no lote e aparecem como pendência.

## Etapa 5 — envio real controlado

- Use uma única pasta autorizada.
- Grave a tela da etapa posterior ao clique em `salvar`.
- Digite `ENCERRAR` somente após revisar a linha.
- Compare o resultado do GCPJ, a captura e o relatório Excel.

## Critérios de aprovação

- Zero divergência de NPC.
- Mapeamento correto de todos os ATOs homologados.
- Nenhum clique em `salvar` no modo de preenchimento.
- Um único clique em `salvar` no modo de envio.
- Registro completo no relatório e no banco local.
- Tratamento explícito de qualquer mensagem não reconhecida.
