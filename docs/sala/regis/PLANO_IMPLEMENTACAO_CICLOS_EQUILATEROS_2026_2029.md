# Plano de Implementacao dos Dois Ciclos Equilateros 2026 a 2029

Data de referencia: 13/03/2026
Janela oficial proposta: 04/06/2026 a 04/06/2029
Escopo: Sala Retro Cara Core + canal tecnico pessoal

## Objetivo

Reestruturar o cronograma editorial para operar em dois ciclos equilateros dentro de uma janela total de 36 meses, com distribuicao coerente entre os dois acervos e com implementacao rastreavel no site, nos feeds e na documentacao institucional.

## Definicao dos ciclos

- Horizonte total: 36 meses editoriais
- Regra mestra: 1 publicacao principal por mes no eixo combinado
- Total alvo: 36 publicacoes principais
- Distribuicao alvo por acervo: 18 Cara Core + 18 canal tecnico pessoal
- Estrutura do programa: 2 ciclos equilateros de 18 meses cada

### Ciclo 1

- Janela: junho/2026 a novembro/2027
- Slots mensais: 18
- Distribuicao alvo: 9 Cara Core + 9 Blog
- Funcao: estabilizacao do reposicionamento, consolidacao de linguagem e prova de disciplina editorial

### Ciclo 2

- Janela: dezembro/2027 a maio/2029
- Slots mensais: 18
- Distribuicao alvo: 9 Cara Core + 9 Blog
- Funcao: continuidade institucional, aprofundamento tecnico e fechamento coerente do ciclo trienal

## Regra de alternancia

- Mes 1 do ciclo: Cara Core
- Mes 2 do ciclo: canal tecnico pessoal
- Alternancia 1:1 obrigatoria por padrao
- Excecao operacional permitida somente com compensacao no mes seguinte ou, no maximo, dentro do mesmo trimestre
- Nenhum dos acervos pode abrir vantagem superior a 1 publicacao dentro de um mesmo ciclo de 18 meses

## Distribuicao-base para implementacao

### Ciclo 1 - junho/2026 a novembro/2027

1. junho/2026: Cara Core
2. julho/2026: Blog
3. agosto/2026: Cara Core
4. setembro/2026: Blog
5. outubro/2026: Cara Core
6. novembro/2026: Blog
7. dezembro/2026: Cara Core
8. janeiro/2027: Blog
9. fevereiro/2027: Cara Core
10. marco/2027: Blog
11. abril/2027: Cara Core
12. maio/2027: Blog
13. junho/2027: Cara Core
14. julho/2027: Blog
15. agosto/2027: Cara Core
16. setembro/2027: Blog
17. outubro/2027: Cara Core
18. novembro/2027: Blog

### Ciclo 2 - dezembro/2027 a maio/2029

1. dezembro/2027: Cara Core
2. janeiro/2028: Blog
3. fevereiro/2028: Cara Core
4. marco/2028: Blog
5. abril/2028: Cara Core
6. maio/2028: Blog
7. junho/2028: Cara Core
8. julho/2028: Blog
9. agosto/2028: Cara Core
10. setembro/2028: Blog
11. outubro/2028: Cara Core
12. novembro/2028: Blog
13. dezembro/2028: Cara Core
14. janeiro/2029: Blog
15. fevereiro/2029: Cara Core
16. marco/2029: Blog
17. abril/2029: Cara Core
18. maio/2029: Blog

## Politica de corte e legado

- O acervo anterior a 04/06/2026 permanece preservado como historico.
- O cronograma ativo passa a considerar apenas slots de junho/2026 a maio/2029.
- Itens publicados antes da nova ancora nao entram na contagem oficial do programa, mesmo que continuem visiveis no arquivo.
- Itens fora do slot designado podem permanecer publicados como memoria, mas devem ser marcados como fora da cadencia oficial caso aparecam na vitrine principal.

## Fases de implementacao

### Fase 1 - Governanca documental

Objetivo: trocar a ancora do programa e registrar a nova arquitetura de dois ciclos equilateros.

Arquivos a atualizar:

- sala/regis/REPOSICIONAMENTO_CONJUNTO_CC_CM_2026_2029.html
- sala/regis/REPOSICIONAMENTO_CONJUNTO_CC_CM_2026_2029.md
- sala/regis/LOGICA_CICLOS_PADRONIZADOS_CC_CM_2026_2029.html
- sala/regis/LOGICA_CICLOS_PADRONIZADOS_CC_CM_2026_2029.md
- sala/regis/CRONOGRAMA_EDITORIAL_EXECUTIVO_2026_2029.md
- sala/regis/REDISTRIBUICAO_ARTIGOS_OPERACAO_2026_2027.html

Entregas:

- substituir 06/04/2026 a 06/04/2029 por 04/06/2026 a 04/06/2029
- substituir a logica de alternancia simples por dois ciclos equilateros de 18 meses
- registrar explicitamente a meta de 9 publicacoes por acervo em cada ciclo

### Fase 2 - Mapa de distribuicao editorial

Objetivo: montar a tabela operacional de slots oficiais e vincular cada slot a um acervo.

Entregas:

- criar uma tabela mes a mes com 36 slots oficiais
- marcar dono do slot, status, arquivo associado e gate GO/NO-GO
- diferenciar claramente slot oficial, backlog e historico preservado

Arquivo recomendado:

- sala/regis/CRONOGRAMA_DISTRIBUICAO_CICLOS_EQUILATEROS_2026_2029.md

### Fase 3 - Adequacao das vitrines publicas

Objetivo: alinhar o que o usuario ve com a nova governanca.

Arquivos a atualizar:

- https://retro.caracore.com.br/
- personal/index.html

Entregas:

- inserir nota de corte com ancora 04/06/2026
- separar visualmente ciclo ativo e acervo historico
- impedir que itens anteriores a 04/06/2026 sejam interpretados como parte do programa oficial

### Fase 4 - Adequacao dos feeds

Objetivo: refletir no RSS apenas o recorte coerente com o programa ativo, se essa for a politica escolhida.

Arquivos a atualizar:

- scripts/generate_rss_feed.py
- https://retro.caracore.com.br/feed.xml
- personal/feed.xml

Entregas:

- trocar o corte de 06/04/2026 para 04/06/2026
- opcionalmente, evoluir o script para suportar janela configuravel por constante ou argumento
- regenerar os feeds e validar XML

### Fase 5 - Controle de execucao

Objetivo: tornar o cronograma operavel sem ambiguidade.

Entregas:

- definir campo `slot_oficial`, `acervo`, `status_publicacao`, `data_planejada` e `data_real`
- criar ritual mensal com checkpoints D-21, D-14, D-7, D, D+5
- registrar compensacoes trimestrais quando a alternancia 1:1 for quebrada

Arquivo recomendado:

- sala/regis/REGISTRO_EXECUCAO_CICLOS_EQUILATEROS_2026_2029.md

## Regras operacionais obrigatorias

- Um slot mensal so pode ser considerado concluido com Gate GO tecnico, editorial, seguranca e LGPD.
- Nota curta conta como entrega de contingencia apenas se houver registro explicito no slot oficial.
- Artigo longo adiado nao some: volta para backlog com nova previsao e motivo.
- Cada trimestre deve fechar com saldo equilibrado entre os dois acervos.
- Cada ciclo de 18 meses deve encerrar exatamente com 9 publicacoes por acervo, salvo revisao formal de governanca.

## Criterios de aceite da implementacao

- Toda documentacao institucional usa a ancora 04/06/2026 a 04/06/2029.
- Existe um cronograma unico com 36 slots oficiais.
- Os dois ciclos de 18 meses estao explicitamente definidos.
- As vitrines deixam claro o que e ciclo ativo e o que e historico.
- Os feeds passam a obedecer o mesmo corte temporal adotado na governanca.
- A contagem por acervo fecha em 18/18 no horizonte total e 9/9 por ciclo.

## Ordem recomendada de execucao

1. Atualizar documentos de governanca.
2. Criar tabela operacional dos 36 slots.
3. Ajustar vitrines publicas.
4. Ajustar geracao de feed e regenerar RSS.
5. Validar coerencia final entre documentos, paginas e feeds.

## Decisoes pendentes antes da execucao final

- Confirmar se a ancora correta e mesmo 04/06/2026, substituindo integralmente a ancora 06/04/2026.
- Confirmar se itens publicados entre abril e maio/2026 ficarao apenas como historico ou serao remapeados para slots oficiais futuros.
- Confirmar se o feed RSS deve refletir apenas o ciclo ativo ou o acervo completo com marcacao historica.
