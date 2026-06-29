# Regras e Contexto do Repositório (Cara Core Retro)

Este arquivo serve como o manual de alinhamento e contexto para qualquer Inteligência Artificial ou assistente de codificação que trabalhe neste repositório.

## 🧭 Visão Geral do Projeto
O `caracore-retro` é o portal histórico e acervo de artigos estratégicos e técnicos da **Cara Core Informática**. O repositório abriga os textos publicados no LinkedIn, organizados por ano em arquivos HTML individuais em `docs/articles/`. 

## 🤖 Identidade Visual do Mascote Oficial
Nosso mascote técnico que conduz os leitores em boxes explicativos deve seguir estritamente o seguinte visual:
- **Estilo:** Pixel art (estilo retrô 16-bit).
- **Cores principais:** Laranja (corpo/cabelo espetado) e Azul (macacão/vestimenta).
- **Detalhes característicos:** Cabelo espetado/arrepiado, sorriso largo e simpático, e uma **engrenagem** estampada no peito do macacão azul.
- Qualquer prompt de geração de imagem para o mascote deve incorporar esta descrição para manter a consistência da identidade de marca.

## ✍️ Padrões de Formatação e Escrita nos Artigos
Ao modificar ou criar novos artigos HTML, siga estas diretrizes de formatação:
1. **Negrito Nativo em HTML:** Não use marcadores estilo Markdown (`**`) diretamente nos parágrafos do HTML; eles renderizam como texto literal. Use sempre a tag HTML clássica `<strong>` ou `<b>` (preferencialmente `<strong>`).
2. **Termos Arquiteturais Chave:** Determinadas expressões fundamentais de arquitetura devem ser escritas com termos específicos em negrito:
   - **Outbox Pattern** ou **Transactional Outbox** em negrito.
   - **cold start** em negrito minúsculo (`<strong>cold start</strong>`).
3. **Equilíbrio Editorial (Executivo vs. Técnico):** Cada artigo da série técnica deve manter:
   - Uma estrofe inicial de poema em **cordel** sintetizando o problema.
   - Um box final estilo lousa escolar (`<div class="chalkboard">`) contendo o veredito dividido em duas colunas: uma coluna voltada para a **baseline técnica** (`💻 Para Técnicos`) e outra voltada para o **retorno de negócios/ROI** (`👔 Para Negócios`).

## 📊 Fatos e Limitações Técnicas Consolidadas (Sem Hype)
Para manter o realismo técnico dos artigos de 2027 (saga *"A Divina Peleja do Caixa Soberano"*), use sempre os seguintes parâmetros:
1. **GraalVM Memory Footprint:** Um aplicativo corporativo Spring Boot backed-database rodando compilado como AOT Native Image consome aproximadamente **~45MB (Startup/Ocioso)** e **~95MB (Stress/Checkout)**. Evite promessas irrealistas de 20MB a 40MB sob stress em produção.
2. **Concorrência e Threads Virtuais (Java 25):** 
   - Sob o **Java 25 (JEP 491)**, monitor locks sincronizados (`synchronized`) foram otimizados pela JVM para não causarem o travamento (pinning) de Virtual Threads.
   - O pinning restringe-se atualmente a chamadas de código nativo (JNI/FFI) ou travamentos no ClassLoader.
   - Operações de hardware serial (como a biblioteca `jSerialComm`) que utilizam JNI nativo devem ser encapsuladas em pools de threads de plataforma tradicionais para isolamento de I/O.
3. **SQLite Local WAL Mode:** O SQLite rodando localmente no caixa em modo `journal_mode=WAL` atinge transações ACID em menos de 1ms, mas possui trade-offs: limite físico de gravação única concorrente e risco de crescimento do arquivo `.db-wal` sob transações longas.
4. **HTML-First (HTMX):** Reduz o inchaço do `node_modules` no build e o bundle final na borda, mas gera maior acoplamento entre templates e backend, exigindo round-trips locais.
5. **Telemetria Borda (Push-Based):** Caixas físicos estão atrás de portas locais NAT/Firewalls, impossibilitando scraping direto via Pull do Prometheus central. A telemetria deve ser **Push-Based** (via heartbeats leves agregados localmente) e desligável sob links de dados backup curtos.
