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

## 📦 Soberania de Recursos e Portabilidade (Offline-First)
Para manter o blog 100% autônomo, performático e imune a bloqueios de CORS:
1. **Zero Dependências Externas:** Não permita o carregamento de CSS, scripts, CDNs ou fontes remotas (ex: Google Fonts). Tudo deve ser local e carregado a partir da pasta `assets/` com caminhos estritamente relativos.
2. **Fonte Centralizada:** A fonte `@font-face` oficial `Share Tech Mono` deve ser mantida exclusivamente em um único local: `docs/assets/fonts/ShareTechMono.ttf`. Arquivos CSS em subpastas devem buscá-la de forma relativa (ex: `../../../assets/fonts/ShareTechMono.ttf`).
3. **Prevenção de 404 (Favicon):** Toda página HTML deve possuir o mapeamento de ícone relativo para o logo (`assets/img/logo.png`), e o arquivo `docs/favicon.ico` deve existir fisicamente na raiz para evitar erros de console.

## 🔍 SEO, Semântica e Acessibilidade (a11y)
Cada template HTML deve seguir o padrão W3C e otimização para leitores de tela:
1. **Tag `<main>` Semântica:** O conteúdo principal do blog deve ser envelopado por `<main class="container">` em substituição a `<div>`s genéricas.
2. **Hierarquia de Headings:** Use apenas um `<h1>` por página (no header). Títulos de agrupamento anual usam `<h2>` e títulos mensais usam `<h3>` (com reset de margem superior no CSS para manter consistência visual).
3. **Meta Tags de SEO:** Garanta que todas as páginas públicas possuam as tags `<meta name="description">` e `<link rel="canonical">` preenchidas de forma única e descritiva.
4. **Interactive Elements:** Chips e botões interativos devem ter `type="button"` e campos de texto devem ter `aria-label` descritiva.

## 🧪 Validação e Testes Automatizados
O repositório possui uma suíte de testes de integridade em **`test_blog.py`**.
* Sempre que novos artigos forem adicionados ou o CSS/HTML sofrer refatorações, execute `python test_blog.py` para garantir que:
  - Nenhuma referência externa ou CDN foi introduzida.
  - Não há caminhos absolutos de arquivo (`file://` ou pastas locais da máquina do desenvolvedor).
  - Todas as rotas relativas, imagens e recursos linkados existem no repositório.
  - A hierarquia de títulos e metadados de SEO obedece às regras.
