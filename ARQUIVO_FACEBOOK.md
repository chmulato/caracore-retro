# Arquivo — automação Retrô → Facebook (cortada em 24/11/2026)

Texto **realocado, não apagado**. Eram as regras operacionais e os estados medidos que viviam em `README.md` ("Chamadas no Facebook"), em `.cursor/rules/project-memory.mdc` e em `.agents/AGENTS.md`. Nada aqui descreve uma máquina viva: sirva-se só para auditoria histórica.

## O que foi cortado

- **Commit `6f26d38`** (terça 24/11/2026, 09h29 de Brasília, já no remoto): 28 arquivos removidos — os workflows `facebook.yml`, `facebook-publish-article.yml` e `facebook-diagnostics.yml`; os 4 módulos `tools/facebook_*`; os 4 `test_facebook_*` da raiz; os 17 JSONs de fila `facebook_campaign_article_*.json`.
- **Ambientes GitHub `facebook` e `facebook-auto` apagados** às 09h50 de terça, com o segredo `FACEBOOK_PAGE_TOKEN` que cada um guardava. Não existe cópia local da chave neste repositório: se a automação voltar, a credencial é gerada de novo no painel da Meta. Enquanto ela não for revogada lá, continua sendo uma credencial válida fora do GitHub.
- **Refs de reserva apagadas** às 09h48: `refs/heads/facebook-reservas/p1657316127663973/a107`–`a112` e `a148` (prova: `git ls-remote origin 'refs/heads/facebook-reservas/*'` = 0 linhas). Os sete commits seguem no banco de objetos local, alcançáveis até um `gc`, e recriam-se com `git push origin <sha>:refs/heads/facebook-reservas/p1657316127663973/a<N>`:

  | ref | sha |
  | --- | --- |
  | a107 | `d8d16430d71412ef593346df9b92648fc7444280` |
  | a108 | `65578f130370c30bad7d31531778c171ccf2092a` |
  | a109 | `345944229f82290f2e50cf623a0e0b2210b3780e` |
  | a110 | `6af0131311e2238a00fbf13c7b50b57853b2d790` |
  | a111 | `0c98c704bb4d975b565c4f1bd6a321787d0dcd07` |
  | a112 | `7ffcb4bce795fc5dea53ed70ac5824cd0a9cc927` |
  | a148 | `a8e49d5616b4b73cb29bdfca7e82a2030b95e91c` |

  Cada um deles tinha `{"estado":"ID_RECEBIDO","remote_id":…}`; os sete `remote_id` foram copiados na conversa de 24/11/2026 e não se repetem aqui.

## O que ainda existe dentro da Meta (pendência do dono, não deste repo)

Apagar ref, workflow ou ambiente **não cancela nada do lado da Meta**. Continuam agendados e confirmados lá os posts de 26/11, 01/12, 03/12, 08/12, 10/12 e 15/12, mais a campanha da reserva `a148`. O cancelamento é no Calendário do Business Suite da Página Cara Core Informática (id `1657316127663973`).

## O que ficou no repositório, como registro e não como automação

`facebook_publication_history.json`, os 23 `docs/facebook/*.html` e `sala-theme-facebook.css`. As páginas do site não são opcionais: apagá-las quebra link no acervo.

## Medição da semana que precedeu o corte (somente leitura)

- `facebook.yml` (id 424162129, cron `0 6 * * 2,4` em `America/Sao_Paulo`) fechou 24/11 com **0 runs**: a cadência nunca executou — nem na quinta 20/11, nem na terça 24/11 às 06h.
- **Não existem `a149` nem `a113`**: o artigo 149 (24/11 09h) e o 113 (22/12 09h) nunca foram aceitos pela Meta por esta esteira.
- As duas tentativas de rota imediata do 149 pararam antes de enviar: a primeira por texto residual no campo de aprovação (recusada, credencial intacta), a segunda passou na aprovação e morreu em `A credencial nao confirmou o acesso a pagina escolhida` — o `GET /me?fields=id` não devolvia a Página.
- Prova de corte limpo, medida antes do commit: zero import órfão, validador do site com 945 verificações aprovadas, testes restantes 2/2.

---

## Texto operacional que estava no `README.md` (seção "Chamadas no Facebook")

## Chamadas no Facebook

- **Frequência definida em 19/11/2026:** terças e quintas, às **09h de Brasília** (`America/Sao_Paulo`). A preparação e a conferência dos rascunhos recusam outros dias e horários.
- O workflow `.github/workflows/facebook.yml` preenche às 06h a janela móvel da Meta com todas as campanhas aprovadas que já podem ser agendadas. Também é possível preencher a janela manualmente pelo `workflow_dispatch`, marcando `preencher_janela`. Assim, os posts ficam visíveis no Planejador antes do dia da publicação.
- O job automático usa o ambiente GitHub `facebook-auto`, restrito a `master`, com o segredo `FACEBOOK_PAGE_TOKEN`; o acionamento manual continua usando o ambiente protegido `facebook`.
- A automação usa os dados e o digest dos arquivos `facebook_campaign_article_*.json`; o campo `aviso` é informativo e não bloqueia a publicação automática. Antes do envio, artigo e imagem publicados são comparados aos arquivos locais, a Página é confirmada e uma reserva no GitHub impede duplicatas. Falhas de validação não publicam a campanha.
- As campanhas além do limite de 30 dias aguardam a próxima execução; mais de uma campanha para a mesma data ou um artigo repetido na fila fazem a execução falhar. Uma campanha vencida, com reserva sem confirmação da Meta ou com bytes diferentes dos publicados fica **bloqueada e listada no fim da execução**, sem envio, e as outras continuam sendo agendadas — o job termina vermelho e repete o aviso até a conferência manual. A Meta exige antecedência mínima de 15 minutos e máxima inferior a 30 dias.
- **Duas rotas, as mesmas travas.** A rota da cadência é `.github/workflows/facebook.yml`: preenche a janela móvel com o que está na fila. A rota imediata é `.github/workflows/facebook-publish-article.yml`: pede só o número do artigo e publica agora, sem data na fila. Nenhuma das duas mexe no token, nas permissões ou na exigência de aprovação.
- **A rota imediata não precisa de código novo por artigo.** São dois campos: `article` (obrigatório, só o número) e `message` (opcional — vazio, a chamada usa o texto que o próprio artigo já traz em `og:description`, `og:title` e o link). A prévia confere os bytes publicados no blog antes de mostrar a chamada.
- **Onde aprovar e até quando.** A prévia escreve no log e no resumo a linha exata `APROVO <digest>` e o horário-limite (15 minutos, hora de Brasília). Em **Review pending deployments**, escolha o ambiente `facebook`, **apague** o texto que já estiver no campo de comentário e cole a linha inteira. Um "ok" sem o código, um comentário vazio ou o prazo vencido recusam o envio antes de qualquer chamada à Meta, e a recusa diz qual desses casos aconteceu.
- **Repetir execução não publica.** O re-run de uma execução já aprovada para com uma explicação, em vez de passar em branco: o digest é recalculado a cada minuto e a aprovação antiga não vale para uma prévia nova. Gere sempre uma execução nova.
- O agendamento manual de uma campanha da fila continua disponível e mantém a revisão e aprovação individuais. Essa frequência vale somente para o Facebook: não altera as datas do blog nem a agenda do LinkedIn.
- Um artigo pode ser compartilhado no Facebook antes da data editorial se já estiver publicado no blog e passar pela verificação de conteúdo; isso não altera as datas do blog ou do LinkedIn. O histórico conferido e a reserva por artigo/Página evitam repetições; o artigo 147 permanece bloqueado.
- Para publicar correções no blog sem postar no LinkedIn, inclua `[skip linkedin]` na mensagem do último commit do push. A validação e o site continuam sendo publicados; os dois canais do LinkedIn são ignorados somente nesse push. A agenda existente permanece inalterada.

### Estado da campanha em 21/11/2026

- A fila tem **17 campanhas**: #107–#122 e o artigo **149 em 24/11 (terça) às 09h**. A conferência local reprova duas campanhas na mesma data ou o mesmo artigo repetido, e ela passou.
- O 149 foi publicado no blog e **não** entrou na fila automaticamente: quem publica um artigo precisa acrescentar a campanha. Na passagem de 21/11, a prévia conferiu os bytes no ar — artigo de 17.979 B e capa de 3.513.453 B com os SHA-256 iguais aos do rascunho.
- As duas tentativas de publicar o 149 "hoje, à mão" **não publicaram**. A aprovação chegou depois do prazo de 15 minutos da prévia e a execução repetida (tentativa 3) parou sem chamar nada; não existe reserva `a149`, portanto não há post na Página. Nada foi enviado duas vezes.
- A rota imediata passou a ser **genérica**: `tools/facebook_publish_article.py` com o workflow `facebook-publish-article.yml`, pedindo só o número do artigo. Os módulos, os testes e os workflows escritos à mão para o 148 e para o 149 foram **removidos** neste lote: eles só funcionariam com o código específico de cada artigo, e a rota genérica faz o mesmo trabalho.
- Gates medidos nesta passagem, sem publicar: **90 testes** dos módulos de blog, Facebook e LinkedIn, **945 verificações** de HTML/CSS do site e os **cinco** workflows restantes lidos sem erro de YAML.
- **A cadência deixou de travar por inteiro.** Antes, uma única campanha fora da janela derrubava o job e nenhum outro post era agendado — e ela derrubava em todas as execuções seguintes, até alguém mexer no arquivo. Hoje a campanha problemática é bloqueada com o motivo no log e no resumo, as demais são agendadas e o job termina vermelho.
- **Se o 149 for publicado antes por outra rota, retire o arquivo da fila.** A reserva guarda o código-hash da prévia que a publicou; o arquivo `facebook_campaign_article_149_20261124.json` tem outro código e a cadência passa a listá-lo como "reserva diverge" em cada execução até o arquivo sair.
- **Risco medido para terça:** o cron é 06h, e a campanha do 149 é 09h do mesmo dia. Se o runner atrasar além das 08h45, os 15 minutos mínimos da Meta não são cumpridos e essa campanha entra na lista de bloqueadas — sem impedir as outras.

### Pré-voo da terça, medido em 22/11/2026 (somente leitura, nada executado)

- Simulei o gatilho de terça (24/11 às 06h de Brasília) com o código de `tools/facebook_campaign.py` sobre a fila atual de 17 campanhas e as reservas remotas. Resultado esperado da execução: **entram no agendamento** #113 (22/12, 28 dias de antecedência) e **149** (24/11 às 09h, 3 horas); **pulam** por já terem reserva #107–#112; **aguardam a janela de ~30 dias** #114–#122 — o #114 (24/12) entra na quinta, 26/11. **Nenhuma campanha está com a data passada**, então a execução fecha verde se o runner começar antes das 08h45.
- Reservas conferidas no remoto em 22/11: `a107`–`a112` e `a148`. **Não existe `a149`** — o post de terça ainda não foi agendado.
- **Correção de enquadramento** em relação à nota de 21/11: o #107 (26/11 às 09h) **já está agendado** na Meta desde 20/11. Na quinta a cadência apenas imprime "já agendada"; o que se confere na quinta é o post aparecendo na Página, não um agendamento novo.
- **O que a reserva prova e o que não prova:** a ref com `ID_RECEBIDO` prova que a Meta aceitou o agendamento. Ela não prova o post visível na Página depois das 09h — isso se vê na própria Página, ou pelo `facebook-diagnostics.yml`, que pede o clique de aprovação no ambiente `facebook`. Só depois desses dois fatos a chave `149` entra em `facebook_publication_history.json`.
- Duas conferências automáticas, ambas somente leitura, ficaram marcadas para terça: **08h35** (ainda há janela de resgate? se não, o motivo e a rota imediata) e **09h45** (reserva, execução e o que falta provar).

### Estado da campanha em 20/11/2026

- A fila aprovada cobre os artigos **#107–#122**, de 26/11/2026 a 23/02/2027. As datas são terças ou quintas, às 09h (`America/Sao_Paulo`).
- A Meta confirmou os agendamentos **#107–#112**. Os rascunhos **#113–#122** continuam na fila local; isso não significa que já estejam no Planejador.
- O Planejador/API só aceitam datas até 30 dias à frente. Em 20/11, com o horário padrão do compositor, 20/12 estava desabilitado no seletor (19/12 era o último dia selecionável); por isso #113 (22/12) e #114 (24/12) ainda não apareciam na semana mostrada pelo usuário.
- A automação os enviará quando entrarem na janela. Previsão das primeiras execuções elegíveis: #113 em 24/11, #114 em 26/11, #115 em 01/12, #116 em 03/12, #117 em 08/12, #118 em 15/12, #119 em 24/12, #120 em 05/01/2027, #121 em 14/01 e #122 em 26/01; todas às 06h de Brasília. A confirmação da execução, não a previsão, comprova presença no Planejador.
- Estado, evidências, tabela completa de datas, reservas já confirmadas e cuidados para retomar estão em [`caracore-site/docs/ECOSYSTEM_MEMORIA.md`](https://github.com/chmulato/caracore-site/blob/master/docs/ECOSYSTEM_MEMORIA.md), na seção “Campanha Facebook do Retrô”.
- Para publicar somente documentação ou ajustes do blog sem tentar cross-post no LinkedIn, inclua `[skip linkedin]` na mensagem do último commit do push.

---

## Regras que estavam em `.cursor/rules/project-memory.mdc`

## Campanha Facebook até fevereiro/2027 — 20/11/2026

- **Fila aprovada:** artigos #107–#122, terça/quinta às 09h (`America/Sao_Paulo`), em `facebook_campaign_article_*.json`. Commit da extensão #121–#122: `b89c642`; deploy Pages `44737098411` concluído. Não houve publicação imediata.
- **Confirmados pela Meta:** #107 (26/11), #108 (01/12), #109 (03/12), #110 (08/12), #111 (10/12) e #112 (15/12). #113–#122 ainda não tinham reserva/ID confirmado em 20/11; permanecer na fila local não significa estar no Planner.
- **Limite:** a Pages API e o seletor do Planejador aceitam até 30 dias futuros; em 20/11, com o horário padrão do compositor, 20/12 estava desabilitado (19/12 era o último dia selecionável). Por isso a semana 20–26/12 aparecia vazia: #113 é 22/12 e #114 é 24/12. Não alterar datas nem tentar contornar o limite pela interface.
- **Automação:** `.github/workflows/facebook.yml` roda terças e quintas às 06h e preenche a janela móvel com publicações para 09h. Os horários previstos para entrada no Planner são registrados na seção “Campanha Facebook do Retrô” de `caracore-site/docs/ECOSYSTEM_MEMORIA.md`; só log de confirmação da Meta + reserva `ID_RECEBIDO` comprovam o agendamento.
- **Idempotência:** antes de qualquer reenvio, conferir `facebook-reservas/p1657316127663973/a<artigo>` e o Planejador. `ID_RECEBIDO` com digest igual significa já agendado; reserva pendente/divergente bloqueia retry até conferência manual. Nunca repetir uma chamada com resultado incerto.
- **Operação e testes:** detalhes em `README.md` (“Chamadas no Facebook”); implementação em `tools/facebook_campaign.py` e `tools/facebook_github.py`. Em 20/11 passaram 68 testes focados de campanha/rascunhos/reservas e 2 testes de metadados. O ambiente automático é `facebook-auto`; o agendamento individual manual usa o ambiente protegido `facebook`.

### 21/11/2026 — artigo novo na fila e rota imediata genérica

- **Fila com 17 campanhas:** #107–#122 e o **artigo 149 em 24/11 (terça) às 09h**, em `facebook_campaign_article_149_20261124.json`. Publicar o artigo no blog **não** o coloca na fila — a campanha é um arquivo à parte, e o nome tem de ser `facebook_campaign_article_<n>_<AAAAMMDD do agendamento>.json`; o carregamento reprova nome divergente, duas campanhas na mesma data e artigo repetido.
- **Rota imediata sem código por artigo:** `tools/facebook_publish_article.py` + `.github/workflows/facebook-publish-article.yml`, com inputs `article` (número) e `message` (opcional; vazio usa `og:description` + `og:title` + link do próprio artigo). Os módulos, testes e workflows escritos à mão para 148 e 149 foram **removidos** em 21/11/2026 (nada mais os referenciava): ficar no repositório só deixaria dois workflows que quebram ao ser disparados.
- **Por que uma aprovação recusa:** `facebook_github.check_approval` agora nomeia a causa (comentário vazio · texto livre como "ok" · digest diferente · aprovador errado · estado ≠ approved · mais de uma aprovação) sempre sob o prefixo `Aprovacao recusada:`. A prévia imprime no log a linha exata `APROVO <digest>` e o prazo — 15 minutos, recalculados a cada minuto porque o digest inclui o horário da prévia.
- **Repetição de execução não é atalho:** o job `repeticao` nos dois workflows falha com explicação quando `run_attempt != 1`, em vez de pular em silêncio como na passagem do 149 (tentativa 3, nada enviado, sem reserva `a149`).
- **Gates medidos em 21/11, sem publicar:** 90 testes (`unittest discover`), 945 verificações do `tools/validate_site.py` e os cinco workflows restantes lidos sem erro de YAML (eram seis antes da remoção dos dois por artigo). O `verify_published` do 149 bate com os bytes no ar: artigo 17.979 B e capa 3.513.453 B com os mesmos SHA-256 do rascunho.
- **A cadência não trava mais por inteiro:** `fill_campaign_window` coletava uma campanha fora da janela (ou com reserva divergente, ou com bytes diferentes) e derrubava o job **antes de agendar qualquer outra** — e repetia a queda em toda execução seguinte. Agora cada campanha problemática entra na lista `blocked` com o motivo (lista `blocked` em `fill_campaign_window`, `tools/facebook_campaign.py:363`), as demais são agendadas e o job termina vermelho apontando o arquivo. Travas por campanha estão intactas: `publish()` reconfere `verify_published` e `verify_history` antes de reservar e enviar.
- **Publicar por outra rota exige retirar o arquivo da fila:** a reserva guarda o digest da prévia que publicou; o arquivo da fila tem outro digest e a cadência passa a listar "reserva diverge" para aquele artigo em toda execução.
- **Risco de terça medido:** o cron é 06h e o 149 é 09h do mesmo dia; com o runner atrasando além das 08h45, a campanha perde os 15 minutos mínimos e vai para a lista de bloqueadas (as outras seguem). Evidência do atraso: as reservas a107–a112 foram gravadas às 12:27 UTC de 20/11 (09:27 de Brasília), não às 09:00 UTC do gatilho.

## Diretriz que estava em `.agents/AGENTS.md`

- **Facebook — campanha ativa até fevereiro/2027 (atualização 20/11):** a fila aprovada #107–#122 usa uma janela móvel limitada a 30 dias pela Meta. Apenas campanhas com ID confirmado pela Meta estão no Planejador; JSON na fila não é confirmação. Consulte o estado e a previsão de cada artigo em `caracore-site/docs/ECOSYSTEM_MEMORIA.md` e as regras operacionais no `README.md`. Antes de qualquer reenvio manual, confira a reserva `facebook-reservas` e o Planejador; uma reserva pendente pode representar uma chamada já aceita pela Meta.
- **Publicação no LinkedIn — página da empresa (CI/CD):** o job `publish-linkedin-company` roda depois de `publish-linkedin`, no mesmo workflow, e posta os mesmos artigos na página **Cara Core Informática** (`urn:li:organization:16249601`) com ledger próprio, `linkedin_company_published.json`. Usa os secrets `LINKEDIN_ORG_ACCESS_TOKEN` (escopo `w_organization_social`) e `LINKEDIN_ORG_URN`; **sem eles o canal fica dormente em dry-run** (aviso no log, esteira verde). Ledger por canal via `python tools/publish_linkedin.py --ledger <arquivo>`.
