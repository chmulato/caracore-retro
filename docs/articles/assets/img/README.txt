================================================================================
IMAGENS DO RETRÔ (Cara Core / LinkedIn) — convenção única
================================================================================
Pasta: docs/articles/assets/img/

LÓGICA DOS NOMES
----------------
1) Ilustração principal de cada artigo:
   article_NN_01.png
   - NN = número do artigo no nome do HTML (ex.: 2026_04_07_article_75.html → 75).
   - Variações 02, 03, etc. quando o texto tiver mais de uma figura.

2) Marca:
   logo.png — logo Cara Core (partilhado).

3) Meta (og:image / twitter) no HTML:
   URL absoluta apontando para o mesmo ficheiro em
   https://retro.caracore.com.br/articles/assets/img/article_NN_01.png

4) Apresentação inline no HTML (padrão artigos 110–115):
   max-width:300px; float:right; margin:0 0 1.5rem 2rem;
   border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,.08);
   O PNG pode ser gerado em 16:9; o frame inline é sempre o acima.

O número do artigo no path da imagem deve sempre coincidir com o article_NN do
nome do ficheiro HTML (validar com tools/validate_article_images.ps1).

================================================================================
