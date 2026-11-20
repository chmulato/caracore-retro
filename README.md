# Artigos Retrô — Cara Core Informática

Portal e acervo de artigos publicados no LinkedIn pela Cara Core Informática. Uma coleção de 148 artigos organizados por data, com foco em inovação, engenharia de software, arquitetura, negócios, estratégia e produtos do ecossistema Cara Core.

## 📋 Estrutura

- **`docs/`** — Pasta publicada pelo GitHub Pages
  - **`index.html`** — Página principal com listagem completa e filtros de busca
  - **`feed.xml`** — Feed RSS para inscrição e distribuição

  - **`docs/articles/`** — Diretório contendo todos os 148 artigos HTML
  - Convenção de nomenclatura: `YYYY_MM_DD_article_(NN).html` (ex.: `2026_05_23_article_86.html`)
  - Data no nome = data de publicação no calendário estratégico
  - O número do artigo também define o alias das imagens: `article_NN_01.png`, `article_NN_02.png` etc.

  - **`docs/articles/assets/`** — Recursos compartilhados
    - `css/` — Estilos dos artigos
    - `img/` — Imagens e gráficos dos artigos; PNGs originais são fallback e têm variantes WebP responsivas de até 720 e 1600 px
    - `js/` — Scripts de funcionalidade
    - `prompts/` — Prompts usados para geração de imagens dos artigos

## 🔍 Como Visualizar

1. **Localmente**: Abra `docs/index.html` em um navegador
2. **Online**: Visite https://retro.caracore.com.br/

## 🏷️ Filtros e Tags

Os artigos são indexados por temas como:
- **Cloud & Infrastructure**: AWS, CDK, EC2, RDS, PostgreSQL
- **Development**: Python, Java EE, Flutter, Design Patterns
- **Data & Analytics**: Dashboard, Performance, Cache, Redis
- **Business**: SaaS, E-commerce, Compliance, Auditoria
- **Security & Privacy**: Segurança, LGPD, Criptografia, OIDC
- **Produtos Cara Core**: Área 51, Reino OIDC, Circuito Ferradura, Minerador 4.0, ETE, PDV, Hub, Helianto Condominium
- E muitos outros (50+ tags)

Use a barra de busca em `docs/index.html` para filtrar por tema, tecnologia, produto ou palavra-chave.

## 📊 Conteúdo

**Total**: 148 artigos (01 a 148)
- **Período**: Fevereiro 2024 — Setembro 2027
- **Calendário público**: artigos futuros permanecem visíveis no índice e no RSS, conforme o planejamento editorial
- **Cobertura**: Publicações regulares semanais
- **Divisão temporal**: 32 artigos em 2024, 33 em 2025, 51 em 2026, 32 em 2027

## 🧭 Ciclo Editorial 2026-2027

O segundo semestre de 2026 e o primeiro semestre de 2027 incluem frentes editoriais de produtos, com artigos alinhados às oficinas e vitrines do ecossistema:

- **Área 51** — Identidade federada, OIDC/OAuth 2.1, PKCE, auditoria, LGPD e acesso governado
- **Reino OIDC** — Formação conceitual sobre identidade, tokens, fluxos e federação
- **Circuito Ferradura** — Oficina de lógica, Python, ábaco romano, segurança digital e formação técnica
- **Minerador 4.0 / ETE** — Campo, Lab, Mercado, hidrometalurgia, terras raras e simulação em Python
- **Helianto Condominium** — SaaS de administração condominial com soberania de dados, motor financeiro e BolePix
- **A Divina Peleja do Caixa Soberano** — Série técnica em 9 cantos sobre a arquitetura do CaraCore PDV (borda física offline-first resiliente baseada em Java 25, SQLite WAL, HTML-First/HTMX e Outbox Pattern)
- **Trilogia do PDV** — Três artigos de 2027 conectando a bagagem profissional de automação fiscal, a maturação em produto e o planejamento de continuidade em Java e Rust para uma operação local resiliente
- **Sobriedade Técnica e Pragmatismo** — Reflexões de meio de 2027 sobre a era da IA, transparência de funding B2B (os três motores da Cara Core) e a superação da síndrome do front-end pesado em favor de arquiteturas HTML-First para os 5.500 municípios
- **Agentes e modernização** — A experiência com IA na evolução de produtos desktop, Gestão de Frotas e o futuro Gestão de Transporte com processamento local de dados sensíveis

Os artigos foram revisados para manter leitura objetiva, com foco em aplicação prática, clareza técnica e baixa repetição entre textos.

## Chamadas no Facebook

- **Frequência definida em 19/11/2026:** terças e quintas, às **09h de Brasília** (`America/Sao_Paulo`). A preparação e a conferência dos rascunhos recusam outros dias e horários.
- O workflow `.github/workflows/facebook.yml` preenche às 06h a janela móvel da Meta com todas as campanhas aprovadas que já podem ser agendadas. Também é possível preencher a janela manualmente pelo `workflow_dispatch`, marcando `preencher_janela`. Assim, os posts ficam visíveis no Planejador antes do dia da publicação.
- O job automático usa o ambiente GitHub `facebook-auto`, restrito a `master`, com o segredo `FACEBOOK_PAGE_TOKEN`; o acionamento manual continua usando o ambiente protegido `facebook`.
- A automação usa os dados e o digest dos arquivos `facebook_campaign_article_*.json`; o campo `aviso` é informativo e não bloqueia a publicação automática. Antes do envio, artigo e imagem publicados são comparados aos arquivos locais, a Página é confirmada e uma reserva no GitHub impede duplicatas. Falhas de validação não publicam a campanha.
- As campanhas além do limite de 30 dias aguardam a próxima execução; mais de uma campanha para a mesma data, um artigo repetido, uma reserva sem confirmação ou dados inconsistentes fazem a execução falhar sem repetir posts. A Meta exige antecedência mínima de 15 minutos e máxima inferior a 30 dias.
- O acionamento manual por `workflow_dispatch` continua disponível e mantém a revisão e aprovação individual. Essa frequência vale somente para o Facebook: não altera as datas do blog nem a agenda do LinkedIn.
- Um artigo pode ser compartilhado no Facebook antes da data editorial se já estiver publicado no blog e passar pela verificação de conteúdo; isso não altera as datas do blog ou do LinkedIn. O histórico conferido e a reserva por artigo/Página evitam repetições; o artigo 147 permanece bloqueado.
- Para publicar correções no blog sem postar no LinkedIn, inclua `[skip linkedin]` na mensagem do último commit do push. A validação e o site continuam sendo publicados; os dois canais do LinkedIn são ignorados somente nesse push. A agenda existente permanece inalterada.

### Estado da campanha em 20/11/2026

- A fila aprovada cobre os artigos **#107–#122**, de 26/11/2026 a 23/02/2027. As datas são terças ou quintas, às 09h (`America/Sao_Paulo`).
- A Meta confirmou os agendamentos **#107–#112**. Os rascunhos **#113–#122** continuam na fila local; isso não significa que já estejam no Planejador.
- O Planejador/API só aceitam datas até 30 dias à frente. Em 20/11, com o horário padrão do compositor, 20/12 estava desabilitado no seletor (19/12 era o último dia selecionável); por isso #113 (22/12) e #114 (24/12) ainda não apareciam na semana mostrada pelo usuário.
- A automação os enviará quando entrarem na janela. Previsão das primeiras execuções elegíveis: #113 em 24/11, #114 em 26/11, #115 em 01/12, #116 em 03/12, #117 em 08/12, #118 em 15/12, #119 em 24/12, #120 em 05/01/2027, #121 em 14/01 e #122 em 26/01; todas às 06h de Brasília. A confirmação da execução, não a previsão, comprova presença no Planejador.
- Estado, evidências, tabela completa de datas, reservas já confirmadas e cuidados para retomar estão em [`caracore-site/docs/ECOSYSTEM_MEMORIA.md`](../caracore-site/docs/ECOSYSTEM_MEMORIA.md), na seção “Campanha Facebook do Retrô”.
- Para publicar somente documentação ou ajustes do blog sem tentar cross-post no LinkedIn, inclua `[skip linkedin]` na mensagem do último commit do push.

## 🔗 Integração com Cara Core

Este repositório é parte do ecossistema Cara Core:
- **Cara Core Hub** — Plataforma central de orquestração
- **Cara Core PDV** — Sistema de ponto de venda
- **Reino OIDC** — Trilha didática de identidade e autenticação
- **Área 51** — Implementação e suporte para identidade federada empresarial
- **Circuito Ferradura** — Formação prática em lógica, Python e segurança digital
- **Minerador 4.0 / ETE** — Engenharia de terras raras, hidrometalurgia e simulação
- **Helianto Condominium** — SaaS condominial com soberania de dados e liquidação via BolePix

Veja o portfólio completo em https://www.caracore.com.br.

## 📝 Metadados

Cada artigo contém:
- **Título e descrição** — Contexto e resumo
- **Metadados Open Graph** — Para compartilhamento social
- **Tags e categorias** — Para filtros e busca
- **Link canônico** — URL oficial do artigo
- **Imagens de capa** — Para redes sociais
- **Prompts de imagem** — Mantidos em `docs/articles/assets/prompts/` e junto com imagens de 2027

## ✅ Validação

Antes de publicar alterações editoriais relevantes:

- Executar `python tools/validate_site.py` para conferir cards, resumos, capas, categorias, ordem/datas do RSS, breakpoints declarados, recursos servidos por HTTP local, landmarks dos artigos e a suíte de integridade
- Executar `python tools/generate_responsive_images.py` ao adicionar ou atualizar imagens de artigos; gera variantes WebP para imagens 01, 02, 03 etc. e atualiza os elementos `<picture>`
- Para sincronizar ou regenerar o feed RSS padronizado com metadados visuais, categorias e enclosures: `python tools/generate_feed.py`
- Para testar um preview já iniciado ou uma URL publicada, executar `python tools/validate_site.py --url http://127.0.0.1:8766/`
- Conferir se `docs/index.html` e `docs/feed.xml` apontam para os artigos corretos
- Conferir se `og:image`, `twitter:image` e `<img>` usam a mesma capa local `article_NN_01.png`
- Manter prompts em `docs/articles/assets/prompts/` ou pastas associadas
- Validar XML do `feed.xml`

O validador não substitui homologação visual e funcional em navegador: confirme também a renderização responsiva, a operação dos filtros e a acessibilidade por teclado.

## 📖 Licença

Conteúdo © Cara Core Informática. Consulte o arquivo `LICENSE` para mais informações.

---

**Última atualização**: Julho 2027
**Manutenção**: [GitHub Repository](https://github.com/chmulato/caracore-retro)
