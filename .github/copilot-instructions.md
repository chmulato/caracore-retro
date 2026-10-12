# Instruções para o GitHub Copilot (Cara Core Retrô)

Você está trabalhando no repositório **`caracore-retro`**, o acervo editorial e histórico da **Cara Core Informática** publicado em [retro.caracore.com.br](https://retro.caracore.com.br/) via GitHub Pages a partir da pasta `docs/`.

---

## 📌 Contexto e Papel do Repositório

- **O que é:** Revista digital de artigos tecnológicos e estratégicos publicados pela Cara Core, organizados cronologicamente (139 artigos cobrindo 2024–2027).
- **O que NÃO é:** Não é loja, nem oficina de produtos, nem a matriz institucional (`caracore.com.br`).
- **Formato Visual:** Revista digital moderna com foco em descoberta visual (estilo Medium / Substack / Apple News), com Hero em destaque no topo, grade responsiva de cards (3/2/1 colunas), proporção 16:9 nas capas e badges de categoria visual.

---

## 🏛️ Diretrizes Técnicas e Regras Inegociáveis

### 1. Soberania e Offline-First (Zero Dependências Externas)
- **Proibido usar CDNs externas, scripts ou fontes remotas** (como Google Fonts, FontAwesome ou bibliotecas em cdnjs/unpkg).
- Todo recurso CSS, JS, imagem e fonte deve ser servido localmente a partir de `docs/assets/` com caminhos relativos.
- A fonte oficial `@font-face` é `Share Tech Mono`, localizada estritamente em `docs/assets/fonts/ShareTechMono.ttf`.

### 2. Semântica, SEO e Acessibilidade (a11y)
- **Landmark semântico:** Todo artigo HTML em `docs/articles/` deve envelopar seu conteúdo principal em `<main class="container">` (e nunca em `<div>` genérica).
- **Hierarquia de Headings:** Apenas um único `<h1>` por documento.
- **SEO:** Cada página deve possuir `<meta name="description">`, `<link rel="canonical">` e metadados Open Graph / Twitter Cards com a respectiva imagem de capa local.
- **Acessibilidade:** Elementos interativos devem ter `type="button"`, imagens devem ter atributos `alt` e cards do índice devem manter rótulos acessíveis.

### 3. Calendário Editorial Futuro
- As datas dos artigos (incluindo datas de 2026 e 2027) são canônicas e intencionais.
- **Nunca filtre, oculte ou altere datas de artigos futuros** sob a suposição de que "ainda não aconteceram". Elas devem permanecer 100% visíveis no índice e no RSS.

### 4. Categorias Visuais da Revista
A classificação no índice e no RSS utiliza as seguintes categorias:
- `PDV` (automação comercial, varejo, terminal de venda, checkout, caixas locais, Java e Rust)
- `Identidade Digital` (segurança, autenticação, OIDC, OAuth 2.1, PKCE, Área 51)
- `Roadmap` (planejamento estratégico, governança, FinOps, logística, portfólio)
- `Circuito` (formação técnica, oficinas, escolas, aprendizado, lógica)
- `Mineração e ETE` (hidrometalurgia, química industrial, terras raras, Minerador 4.0, saneamento)
- `Tecnologia` (engenharia de software geral e arquitetura)

---

## 🛠️ Ferramentas e Scripts de Suporte

Ao realizar alterações no catálogo, artigos ou estilos:

1. **`python tools/generate_feed.py`**
   - Regenera `docs/feed.xml` com base em `docs/index.html` e nos arquivos de imagem locais.
   - Enriquece os itens com `<enclosure>` contendo a contagem exata de bytes, Media RSS (`<media:content>` / `<media:thumbnail>`), dimensões (largura/altura), categorias e autor.

2. **`python tools/validate_site.py`**
   - Validador estático, estrutural e smoke test HTTP local.
   - Valida os 139 artigos, landmarks `<main>`, hierarquia `<h1>`, integridade de capas, correspondência do RSS e links.
   - Deve sempre terminar com **APROVADO** (0 falhas e 0 avisos).
   - Suporta validação remota: `python tools/validate_site.py --url https://retro.caracore.com.br/`.

3. **`python test_blog.py`**
   - Suíte de integridade para links, caminhos relativos, ausência de CDNs e regras de SEO.

4. **CI/CD no GitHub Actions (`.github/workflows/deploy.yml`)**
   - O job `deploy` possui dependência estrita (`needs: validate`). Se o validador falhar, o deploy para produção é abortado.

5. **Agente de QA (`.github/agents/qa-homologacao.agent.md`)**
   - Use o subagente especializado de homologação para testes manuais e automatizados de layout, responsividade e interatividade em navegador.

---

## 📚 Documentação Complementar
- Contexto editorial detalhado e convenções de artigos: [project-memory.mdc](../.cursor/rules/project-memory.mdc)
- Diretrizes operacionais e mascote oficial: [AGENTS.md](../.agents/AGENTS.md)
- Visão geral do repositório: [README.md](../README.md)
