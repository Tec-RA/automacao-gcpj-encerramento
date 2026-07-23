# Validação técnica desta entrega

## Executado no ambiente de desenvolvimento

- compilação de todos os módulos Python com `compileall`;
- 15 testes automatizados aprovados;
- testes de normalização de NPC, inclusive número vindo do Excel e notação científica;
- leitura de XLSX e CSV separado por ponto e vírgula;
- detecção e validação das colunas da planilha;
- mapeamento e bloqueio de ATOs;
- geração e reabertura do relatório Excel;
- persistência e leitura do histórico SQLite;
- verificação do modelo Excel incluído;
- teste do Page Object em uma página GCPJ simulada dentro de `iframe` com Chromium, cobrindo pesquisa, data, motivo, detalhes e retorno de salvamento.

## Dependências de homologação no escritório

O ambiente de desenvolvimento não possui a extensão corporativa nem uma sessão autorizada do GCPJ. Portanto, os seletores foram construídos com base no vídeo e em múltiplas alternativas por texto, `id`, `name` e XPath, mas precisam ser homologados no Chrome do escritório.

A mensagem final posterior ao botão `salvar` também não aparece no vídeo. Até essa tela ser fornecida, qualquer retorno não reconhecido permanece como `SOLICITADO_SEM_CONFIRMACAO`, sem repetição automática.
