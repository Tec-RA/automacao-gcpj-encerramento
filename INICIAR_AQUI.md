# Iniciar a automação GCPJ

Este projeto roda **no seu computador Windows**. O Streamlit é a interface; o Playwright se conecta ao Chrome dedicado na porta `9222` e utiliza a sessão do GCPJ aberta pela extensão.

## Instalação — feita uma única vez

1. Extraia o projeto para uma pasta local, por exemplo `C:\Automacoes\gcpj_encerramento`.
2. Abra o PowerShell dentro dessa pasta.
3. Execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

## Uso diário

1. Dê dois cliques em `scripts\iniciar_app.bat`.
2. Na tela do Streamlit, clique em **Abrir Chrome GCPJ**.
3. No Chrome dedicado, abra a extensão, entre no GCPJ e deixe a aba aberta.
4. Volte ao Streamlit e clique em **Verificar conexão**.
5. Faça o upload da planilha.
6. Confirme o mapeamento `NPC`, `ATO`, `STATUS` e `CONTA PRA META`.
7. No primeiro teste, mantenha:
   - limite de uma linha;
   - modo **Preencher sem salvar**;
   - captura de evidência ativada.
8. Confira a pasta preenchida no GCPJ.
9. Somente depois da homologação use o modo **Solicitar encerramento**.

## Arquivos gerados

- `data\gcpj_automation.db`: histórico local;
- `data\exports\`: relatórios Excel;
- `evidence\`: capturas de tela;
- `logs\gcpj_automation.log`: log técnico.

## Importante nesta versão

O vídeo de referência termina antes da mensagem exibida após o botão `salvar`. O projeto já possui o modo de envio, mas resultados sem uma mensagem reconhecida são classificados como **SOLICITADO_SEM_CONFIRMACAO** e nunca são repetidos automaticamente.
