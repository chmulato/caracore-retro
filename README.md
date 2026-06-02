# Artigos Retrô — Cara Core Informática

Portal e acervo de artigos publicados no LinkedIn pela Cara Core Informática. Uma coleção de 103 artigos organizados por data, com foco em inovação, engenharia de software, arquitetura, negócios, estratégia e produtos do ecossistema Cara Core.

## 📋 Estrutura

- **`docs/`** — Pasta publicada pelo GitHub Pages
  - **`index.html`** — Página principal com listagem completa e filtros de busca
  - **`ciclo-ativo.html`** — Recorte editorial do ciclo ativo
  - **`feed.xml`** — Feed RSS para inscrição e distribuição

- **`docs/articles/`** — Diretório contendo todos os 103 artigos HTML
  - Convenção de nomenclatura: `YYYY_MM_DD_article_(NN).html` (ex.: `2026_05_23_article_86.html`)
  - Data no nome = data de publicação no calendário estratégico
  - O número do artigo também define o alias da imagem: `article_NN_01.png`

  - **`docs/articles/assets/`** — Recursos compartilhados
    - `css/` — Estilos dos artigos
    - `img/` — Imagens e gráficos dos artigos; HTML publicado deve apontar para `article_NN_01.png`
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
- **Produtos Cara Core**: Área 51, Reino OIDC, Circuito Ferradura, Minerador 4.0, ETE, PDV, Hub
- E muitos outros (50+ tags)

Use a barra de busca em `docs/index.html` para filtrar por tema, tecnologia, produto ou palavra-chave.

## 📊 Conteúdo

**Total**: 103 artigos (01 a 114; numeração com lacunas históricas)
- **Período**: Fevereiro 2024 — Dezembro 2026
- **Cobertura**: Publicações regulares semanais
- **Divisão temporal**: 32 artigos em 2024, 33 em 2025, 37 em 2026

## 🧭 Ciclo Editorial 2026

O segundo semestre de 2026 inclui uma frente editorial de produtos, com artigos alinhados às oficinas e vitrines do ecossistema:

- **Área 51** — Identidade federada, OIDC/OAuth 2.1, PKCE, auditoria, LGPD e acesso governado
- **Reino OIDC** — Formação conceitual sobre identidade, tokens, fluxos e federação
- **Circuito Ferradura** — Oficina de lógica, Python, ábaco romano, segurança digital e formação técnica
- **Minerador 4.0 / ETE** — Campo, Lab, Mercado, hidrometalurgia, terras raras e simulação em Python

Os artigos de junho e julho de 2026 foram revisados para manter leitura de aproximadamente 6 a 8 minutos, com foco em aplicação prática, clareza técnica e baixa repetição entre textos.

## 🔗 Integração com Cara Core

Este repositório é parte do ecossistema Cara Core:
- **Cara Core Hub** — Plataforma central de orquestração
- **Cara Core PDV** — Sistema de ponto de venda
- **Reino OIDC** — Trilha didática de identidade e autenticação
- **Área 51** — Implementação e suporte para identidade federada empresarial
- **Circuito Ferradura** — Formação prática em lógica, Python e segurança digital
- **Minerador 4.0 / ETE** — Engenharia de terras raras, hidrometalurgia e simulação

Veja o portfólio completo em https://www.caracore.com.br.

## 📝 Metadados

Cada artigo contém:
- **Título e descrição** — Contexto e resumo
- **Metadados Open Graph** — Para compartilhamento social
- **Tags e categorias** — Para filtros e busca
- **Link canônico** — URL oficial do artigo
- **Imagens de capa** — Para redes sociais
- **Prompts de imagem** — Mantidos em `docs/articles/assets/prompts/`

## ✅ Validação

Antes de publicar alterações editoriais relevantes:

- Conferir se `docs/index.html`, `docs/ciclo-ativo.html` e `docs/feed.xml` apontam para os artigos corretos
- Conferir se `og:image`, `twitter:image` e `<img>` usam `article_NN_01.png`
- Manter prompts em `docs/articles/assets/prompts/`
- Validar XML do `feed.xml`

## 📖 Licença

Conteúdo © Cara Core Informática. Consulte o arquivo `LICENSE` para mais informações.

---

**Última atualização**: Dezembro 2026  
**Manutenção**: [GitHub Repository](https://github.com/chmulato/caracore-retro)
