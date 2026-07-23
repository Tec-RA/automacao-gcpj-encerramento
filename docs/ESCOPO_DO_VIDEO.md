# Escopo reproduzido do vídeo

O projeto foi implementado até o ponto demonstrado no vídeo enviado:

1. leitura de uma planilha com as colunas `NPC`, `ATO`, `STATUS` e `CONTA PRA META`;
2. abertura do GCPJ já autenticado no Chrome dedicado;
3. acesso ao menu **Encerramento de Processos**;
4. pesquisa pelo campo **Nº do Processo Bradesco**;
5. conferência da pasta retornada;
6. preenchimento da data;
7. leitura do ATO da planilha;
8. seleção da opção equivalente no campo **Motivo**;
9. suporte ao campo **Detalhes do Encerramento**;
10. modo opcional e protegido para acionar **salvar**.

No material recebido, o fluxo termina antes de uma confirmação final de salvamento. Por isso, a confirmação foi isolada em configuração e possui um estado seguro de retorno não confirmado.
