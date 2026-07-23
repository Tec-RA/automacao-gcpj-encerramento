# Automacao de Encerramento de Pastas - GCPJ

> Para instalar e usar, comece por [`INICIAR_AQUI.md`](INICIAR_AQUI.md).

Aplicacao local em **Python, Streamlit e Playwright** para ler uma planilha, localizar pastas pelo **NPC** no GCPJ e executar o fluxo de encerramento demonstrado no video de referencia.

> Esta versao foi construida a partir do fluxo visual fornecido: abrir `Encerramento de Processos`, pesquisar o NPC, preencher a data e selecionar o motivo conforme a coluna `ATO`. O video termina antes da confirmacao final do GCPJ; por isso o modo de envio real possui uma confirmacao adicional e a deteccao de sucesso esta preparada para calibracao.

## Escopo implementado

- Interface profissional em Streamlit, executada no computador do escritorio.
- Botao para abrir o Chrome debugavel com:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="C:\chrome_gcpj_debug"
```

- Conexao do Playwright ao Chrome existente por CDP (`http://127.0.0.1:9222`).
- Uso da extensao e da sessao do GCPJ ja autenticada, sem armazenar usuario ou senha.
- Upload de XLSX, XLSM, XLS ou CSV.
- Mapeamento visual das colunas da planilha.
- Deteccao automatica das colunas `NPC`, `ATO`, `STATUS`, `CONTA PRA META`, numero do processo e observacoes.
- Pre-validacao de NPCs, motivos nao mapeados, recursos pendentes e duplicidades.
- Pesquisa do NPC no menu `Encerramento de Processos`, inclusive quando o conteúdo estiver em `iframe`.
- Preenchimento da data de encerramento.
- Selecao do motivo no GCPJ conforme a coluna `ATO`.
- Campo opcional de detalhes com modelos, por exemplo: `Encerramento conforme ATO {ato}.`
- Tres modos de execucao:
  - **Apenas validar pastas**: pesquisa o NPC e nao altera o formulario.
  - **Preencher sem salvar**: preenche data e motivo, sem acionar `salvar`.
  - **Solicitar encerramento**: aciona `salvar`, somente apos digitacao explicita de `ENCERRAR`.
- Capturas de evidencia locais, logs rotativos, bloqueio contra duas execucoes simultaneas e historico em SQLite.
- Relatorio Excel com resultado por linha.
- Diagnostico seguro dos elementos HTML, sem copiar valores de campos de texto.

## Fluxo observado no video

1. Ler o NPC na planilha.
2. Abrir o GCPJ autenticado.
3. Clicar em `Encerramento de Processos`.
4. Informar o `N do Processo Bradesco` e pesquisar.
5. Conferir a pasta retornada.
6. Preencher a data do encerramento.
7. Consultar a coluna `ATO` da planilha.
8. Selecionar o motivo correspondente no GCPJ.
9. Opcionalmente preencher detalhes.
10. No modo autorizado, acionar `salvar`.

## Mapeamentos iniciais de ATO

O arquivo `config/motivo_mapping.yaml` contem as equivalencias. Os valores observados ou inferidos de forma segura para o MVP sao:

| ATO na planilha | Motivo no GCPJ |
|---|---|
| IMPROCEDENTE | IMPROCEDENCIA |
| EXTINTO SEM MERITO | EXTINTO SEM RESOLUCAO DE MERITO |
| ACORDO COM CUSTOS | ACORDO COM CUSTOS |
| ACORDO SEM CUSTOS | ACORDO SEM CUSTOS |
| DESISTENCIA DA ACAO | DESISTENCIA DA ACAO |
| LIQUIDACAO | LIQUIDACAO |
| ARQUIVADO | ARQUIVADO |
| CANCELADO | CANCELADO |

Atos como `AUTOR RECORREU` e `REU RECORREU` ficam bloqueados por padrao, pois indicam que o encerramento automatico pode ser prematuro.

## Instalacao no Windows

Recomendado: Python 3.12 e Google Chrome instalado no caminho padrao.

### Instalacao automatica

Abra o PowerShell na pasta do projeto e execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

Depois abra:

```text
scripts\iniciar_app.bat
```

### Instalacao manual

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

A interface sera aberta em:

```text
http://localhost:8501
```

## Primeiro uso da extensao

1. Inicie a aplicacao.
2. Clique em **Abrir Chrome GCPJ**.
3. No Chrome aberto com o perfil `C:\chrome_gcpj_debug`, instale ou habilite a extensao utilizada pelo escritorio.
4. Acesse o GCPJ normalmente e conclua a autenticacao.
5. Deixe a aba do GCPJ aberta no Menu Principal.
6. Volte ao Streamlit e clique em **Verificar conexao**.

O perfil e separado do Chrome pessoal. Isso e necessario para preservar a extensao e a sessao e tambem atende ao comportamento atual do Chrome para depuracao remota.

## Planilha

O modelo esta em:

```text
templates\modelo_planilha_encerramento.xlsx
```

Colunas minimas:

| Coluna | Obrigatoria | Uso |
|---|---:|---|
| NPC | Sim | Numero pesquisado no campo `N do Processo Bradesco` |
| ATO | Sim | Origem do motivo selecionado no GCPJ |
| STATUS | Nao | Pode limitar o processamento a `OK` |
| CONTA PRA META | Nao | Filtro opcional para `SIM` |
| NUMERO DO PROCESSO | Nao | Registro no relatorio |
| DETALHES ENCERRAMENTO | Nao | Texto a ser levado para o formulario |

A tela permite mapear nomes de colunas diferentes sem alterar o codigo.

## Configuracao

### Chrome e caminhos

Edite `config/app.yaml` quando necessario:

```yaml
chrome:
  executable: "C:/Program Files/Google/Chrome/Application/chrome.exe"
  user_data_dir: "C:/chrome_gcpj_debug"
  debug_host: "127.0.0.1"
  debug_port: 9222
```

Tambem podem ser usadas variaveis de ambiente:

- `GCPJ_CHROME_PATH`
- `GCPJ_PROFILE_DIR`
- `GCPJ_DEBUG_HOST`
- `GCPJ_DEBUG_PORT`
- `GCPJ_APP_CONFIG`

### Motivos

Edite `config/motivo_mapping.yaml` para incluir novas equivalencias. O texto do lado direito precisa coincidir com uma opcao real do campo `Motivo` no GCPJ. A aplicacao compara os textos sem considerar acentos, caixa e espacos excedentes.

### Seletores do GCPJ

Os seletores ficam em `config/selectors.yaml`. Para cada elemento ha alternativas por texto visivel, XPath, `name` e `id`, adequadas ao HTML legado mostrado no video.

Se o GCPJ mudar, use o botao **Gerar diagnostico**. O JSON gerado lista `id`, `name`, tipos de campos, opcoes dos `selects` e links visiveis. Valores digitados em campos de texto nao sao copiados.

## Seguranca operacional

- Nao ha usuario, senha, token ou certificado no codigo.
- A aplicacao nao tenta contornar CAPTCHA ou autenticacao.
- O envio real exige a expressao `ENCERRAR`.
- O modo padrao e `Preencher sem salvar`.
- O primeiro teste deve ser feito com uma unica linha.
- Evidencias, banco e logs ficam somente no computador local.
- Nao publique as pastas `data`, `evidence` ou `logs`.
- Revise o uso das capturas em processos sob segredo de justica.

## Estrutura

```text
gcpj_encerramento_streamlit/
|-- streamlit_app.py
|-- src/gcpj_automation/
|   |-- browser/              # Chrome CDP, sessao e page object do GCPJ
|   |-- services/             # Planilha, motivos, execucao, relatorio
|   |-- repositories/         # Historico SQLite
|   `-- ui/                   # Componentes visuais
|-- config/
|   |-- app.yaml
|   |-- selectors.yaml
|   `-- motivo_mapping.yaml
|-- templates/
|-- scripts/
|-- tests/
|-- data/
|-- evidence/
`-- logs/
```

## Testes e qualidade

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

A entrega inclui 15 testes automatizados, cobrindo normalizacao, mapeamento de motivos, leitura da planilha, relatorio, SQLite, modelo Excel e um Page Object executado contra uma tela GCPJ simulada. O acesso real ao GCPJ depende da extensao, da sessao autenticada e do HTML disponibilizado ao escritorio.

## Diagnostico rapido

```powershell
powershell -ExecutionPolicy Bypass -File scripts\diagnostico.ps1
```

Esse script verifica Python, Chrome, porta 9222 e o endpoint CDP.

## Limite conhecido desta entrega

O trecho enviado nao mostra o comportamento posterior ao clique em `salvar` nem a mensagem de confirmacao final. O projeto ja possui o modo de envio e uma deteccao conservadora, mas o primeiro uso real deve ocorrer em modo `Preencher sem salvar`. Com um novo video da etapa final, os termos e a verificacao de sucesso podem ser fechados com precisao em `config/app.yaml` e no page object.
