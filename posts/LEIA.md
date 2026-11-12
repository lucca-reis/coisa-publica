# Posts da Coisa Pública nas redes (Instagram e Bluesky)

Três posts por dia, cada um com imagem e texto, sempre aprovados pelo Lucca antes de sair.

## Como funciona

1. Uma tarefa agendada escreve o rascunho: `posts/AAAA-MM-DD-periodo/post.json` (periodo = `manha`, `tarde` ou `noite`) numa branch `post/AAAA-MM-DD-periodo`, gera a imagem com `node scripts/posts/render.js posts/AAAA-MM-DD-periodo` e envia a branch.
2. O robô `.github/workflows/post-aprovacao.yml` abre o pedido de aprovação (pull request) com a imagem, os textos e as fontes.
3. As imagens de lista usam o fundo #F3F3F3, e as de um assunto só também, sem caixa e com o desenho grande (veja "Formato do post.json") (em `modelo.html`, `apresentacao.js` e nos scripts de `especiais/`).
4. Horários fixos (Brasília): manhã 8h, tarde 13h, noite 18h (domingo, planos da semana, às 13h). Aprovado antes, o post espera a hora dele; aprovado depois, sai assim que é aprovado. Para mudar a hora de um post só, `"hora": "HH:MM"` no `post.json`. Os rascunhos chegam às 6h37, 11h37 e 15h37.
5. Aprovar = **Merge** (pode ser pelo app do GitHub no celular). Descartar = **Close**. Para mudar o texto, editar o `post.json` na branch antes de aprovar (a imagem não muda sozinha; se mudar o texto da imagem, gerar de novo).
6. Para refazer um post já publicado: apagar o `publicado.json` da pasta e pôr o id da mídia em `posts/apagar.json` (`[{"pasta":..., "instagram":...}]`) no mesmo commit. O `publicar.yml` apaga a versão antiga (`scripts/posts/apagar.py`, precisa da permissão `instagram_manage_contents`) e só então publica de novo; se a remoção falhar, nada é publicado.
4. Ao chegar na `main`, `.github/workflows/publicar.yml` publica no Bluesky e no Instagram (`scripts/posts/publicar.py`) e grava `publicado.json` na pasta do post.

Segredos do GitHub (Settings > Secrets and variables > Actions): `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `IG_USER_ID`, `IG_TOKEN`. Rede sem segredo é pulada e o post espera.

> Desde 3/11/2026 a publicação automática está pausada: todo dia às 20h os três posts do dia seguinte são preparados e entregues ao Lucca no chat (imagem, legenda e texto alternativo), e ele publica à mão.

## Calendário dos posts

Horário de Brasília. A tarefa agendada roda todo dia às 6h37, 11h37 e 17h37 e decide pelo calendário abaixo o que fazer; se o horário não tem post, ela para sem fazer nada.

| Dia | Manhã (6h37) | Tarde (11h37) | Noite (17h37) |
|---|---|---|---|
| Segunda a quinta | Ordem do dia | Você sabia? | Projeto em tramitação |
| Sexta | Ordem do dia | Você sabia? | Resumo da semana |
| Sábado | — | — | — |
| Domingo | — | Planos da semana | — |
| Último dia útil do mês | (como no dia da semana) | + Planos do mês seguinte | + Resumo do mês |

- **Ordem do dia (manhã, id `AAAA-MM-DD-manha`):** a data já aparece no alto da imagem; não repetir o dia numa linha embaixo do título (sem `texto` de fora da lista). o que está marcado para hoje nos Três Poderes: sessões do Plenário da Câmara e do Senado, sessões do Congresso, julgamentos do STF, agenda do presidente, prazos de sanção e de MPs que vencem hoje. Se não há nada oficialmente marcado para o dia, o post diz isso ("Hoje não há sessões nem julgamentos marcados nos Três Poderes"), sem inventar assunto. Fonte: `AGENDA` e `PENDING` no `index.html`, `data/live.json`, `data/instituicoes.json`.
- **Você sabia? (tarde, id `AAAA-MM-DD-tarde`):** post educativo, com o título começando por "Você sabia?". Assunto sorteado entre: o que faz um órgão (Câmara, Senado, Congresso, STF, STJ, TST, TSE, STM, TCU, MPU, DPU; `COURTS`, `aboutHTML`), o que faz um ministério (`EXEC_MIN`, `data/ministerios.json`), quem ocupa um cargo (presidente, vice, presidentes da Câmara e do Senado, ministros de Estado, ministros do STF, presidentes de tribunais; só cargo, partido, estado, desde quando e como chegou ao cargo, sem opinião nem vida pessoal), como funciona um tipo de proposta (as explicações de `CATS`) ou uma regra do processo (sanção e veto, quórum de PEC, prazo de MP, urgência, votação nominal e simbólica). Não repetir o mesmo assunto nos últimos 30 dias.
- **Projeto em tramitação (noite de segunda a quinta, id `AAAA-MM-DD-noite`):** um projeto ou processo que está andando agora (Câmara, Senado, sanção ou STF), explicado em linguagem simples: o que muda, onde está, qual o próximo passo e o placar, se já houve votação. Prioridade para o que foi votado ou pautado nos últimos dias (`PROJECTS`, `data/projetos.json`, `data/votos.json`). Não repetir o mesmo projeto nos últimos 14 dias, a não ser que ele tenha andado.
- **Resumo da semana (noite de sexta, id `AAAA-MM-DD-noite`):** o que aconteceu de segunda a sexta: votações com resultado, julgamentos concluídos, sanções e vetos, MPs editadas. Lista de até 3 itens na imagem e o resto na legenda.
- **Planos da semana (domingo à tarde, id `AAAA-MM-DD-tarde`):** o que está marcado de segunda a sexta seguintes: pautas, julgamentos, prazos. Lista de até 3 itens na imagem, por dia.
- **Último dia útil do mês:** além dos posts normais do dia, dois a mais. À tarde, **Planos do mês seguinte** (id `AAAA-MM-DD-tarde-mes`): datas já marcadas para o mês que vem (pautas, julgamentos, prazos de MPs e de sanção, recesso). À noite, **Resumo do mês** (id `AAAA-MM-DD-noite-mes`): o que aconteceu no mês, com números quando a fonte der (quantas leis sancionadas, MPs editadas, votações no Plenário). Se esse dia for uma sexta, a noite tem o resumo da semana e o resumo do mês. Cada post extra vai na sua própria branch `post/<id>`.
- **Dia útil:** segunda a sexta, menos os feriados nacionais (1/1, Carnaval e Quarta-feira de Cinzas, Sexta-feira Santa, 21/4, 1/5, Corpus Christi, 7/9, 12/10, 2/11, 15/11, 20/11, 25/12). Nos feriados, a ordem do dia diz que não há sessões oficiais, se for o caso.
- Se um horário não tiver nenhum dado novo para o assunto dele, use outro "Você sabia?" no lugar, nunca invente.

## Regras (as mesmas do site)

- Só fatos que estão nos dados do site, com fonte oficial. Nunca inventar números, votos, datas ou resultados. Se a fonte não informa, não dizer.
- Não falar em "robô": os dados são "atualizados automaticamente".
- Linguagem simples e neutra. Sem opinião, sem adjetivos de julgamento ("polêmica", "vitória", "derrota do governo"), sem apoiar partido ou pessoa. Valores como publicados.
- Não usar fotos de pessoas. A imagem é sempre o cartão da Coisa Pública gerado por `render.js`.
- Bluesky: até 300 caracteres no total, terminando com `coisapublica.io`.
- Instagram: até 2.200 caracteres, parágrafos curtos, no máximo um emoji no começo, termina com "link na bio" e no máximo 6 hashtags.
- `alt`: descrição da imagem para quem não enxerga (o que está escrito e o desenho do placar).

## Formato do post.json

```json
{"id":"2026-11-01-tarde","periodo":"tarde","data":"2026-11-01",
 "imagem":{"poder":"jud","eyebrow":"Decisão do Supremo","titulo":"Aposentados com doenças graves",
  "tags":[{"t":"STF · em vigor","poder":"jud"},{"cat":"acao","t":"Ação no Supremo · ADI 6336"}],
  "texto":"Frase curta explicando o que aconteceu.",
  "placar":{"sim":7,"nao":3,"rotulos":["pela validade","contra"],"desenho":"stf"},
  "fonte":"STF Notícias, 29/10/2026"},
 "alt":"Descrição da imagem.",
 "textos":{"bluesky":"…","instagram":"…"},
 "fontes":[{"l":"STF Notícias, 29/10/2026","u":"https://…"}]}
```

- `imagem.poder`: `leg`, `jud` ou `exe` (cor da bolinha do logo). Em `tags`, `poder` pinta a etiqueta com a cor do poder e `cat` usa a cor do tipo (`mp`, `pec`, `plp`, `pl`, `pdl`, `acao`, `re`).
- Um assunto só: `tags`, `texto` e, se houver, `placar` (`desenho`: `stf`, `camara`, `senado` ou sem desenho). Lista de assuntos: `itens` (até 3), cada um com `quando`, `dia`, `tags`, `titulo` e `texto` opcional; o `texto` de fora vira uma linha embaixo do título.
- Post de um assunto só com `imagem.poder` sai no layout de assunto único: fundo #F3F3F3, o tema em texto pequeno com uma bolinha na cor do poder, sem caixa e sem etiquetas (elas ficam na legenda), e um desenho grande no meio: `visual` `{"tipo":"plenario","casa":"camara"|"senado","destaque":308,"numeros":[{"n":"308","l":"dos 513 deputados"}]}` (semicírculo com as cadeiras destacadas) ou `{"tipo":"percentual","valor":60,"rotulo":"três quintos","numeros":[...]}` (o semicírculo do plenário numa faixa única, preenchida até a porcentagem) ou `{"tipo":"data","rotulo":"Julgamento","valor":"4/11","sub":"quarta-feira, no plenário"}` (o símbolo do poder num círculo, ou a mesa do STF com as 11 cadeiras no Judiciário, e, à direita dele, o rótulo, a data ou o número grande e a linha de baixo; o grupo fica centralizado na largura); ou `{"tipo":"distrital"}` (o mesmo estado fictício duas vezes, em hexágonos com uma bolinha por vaga: à esquerda um território só, "Hoje"; à direita cortado em distritos, "Distrital"; `rotulos` muda os textos de baixo) ou `{"tipo":"sistemas"}` (uma tabela de três linhas separadas por fios, proporcional, distrital e misto, com um estado fictício de 10 vagas e três partidos fictícios em laranja, verde-água e roxo: o nome e uma regra curta, o mapa e as cadeiras que resultam; embaixo, a legenda "Exemplo fictício"; o post fica sem `texto`) ou `{"tipo":"aparelhos","grupos":[{"titulo":"Senado","n":"425","l":"celulares","forma":"celular"|"tablet","partes":[[95,"iPhones Pro"],[330,"outros modelos"]],"valor":"R$ 6 milhões","sub":"estimativa"}]}` (uma coluna por grupo, com um desenhinho por aparelho; a primeira parte na cor do poder e o resto em cinza, a legenda e o valor embaixo) ou `{"tipo":"degraus","pontos":[15,14.75,14.5],"valor":"14,5%","sub":"ao ano"}` (uma escada com o número publicado em cada degrau; a base não começa do zero); sem `visual`, entra o `placar`. Texto curto (uma ou duas frases); o resto vai na legenda. Posts com lista (`itens`), como a ordem do dia e os resumos, seguem com a caixa cinza. Para usar o layout antigo, com caixa, num post de um assunto só: `"fundo":"claro"`.
- `visual` `{"tipo":"mulheres","casas":[{"casa":"camara"|"senado","titulo","total","pct","l","partidos":[["PT",25],...]}]}`: um semicírculo por Casa com as cadeiras pintadas na cor de cada partido (as cores do site), a porcentagem e a lista de partidos embaixo.
- **Destaques em grade** (bom para os resumos): `"layout":"destaques"` com até 4 `itens`, cada um com `poder`, `quando`, `dia`, `titulo`, `texto`, `num` opcional e `desenho` (`{"tipo":"senado"|"camara","sim":72,"nao":0}`, `{"tipo":"mesa"}`, `{"tipo":"moedas"}` ou `{"tipo":"circulo","texto":"2031"}`): cartões coloridos na cor de cada poder, dois por linha.
- **Pergunta em destaque** (bom para "Em tramitação"): `"pergunta":"Os municípios podem criar as próprias loterias?"` e `"rodape":{"rotulo":"O STF decide em","valor":"4 de novembro"}`. A pergunta vira o título grande, o `titulo` vai para a linha do tema, e embaixo, depois de um fio, entram o símbolo do poder (a mesa do STF no Judiciário) e a data.
- Títulos curtos (até ~40 caracteres). Se `render.js` avisar que não coube, encurtar.
- Exemplos completos em `posts/exemplos/`.

## Posts de apresentação

`posts/AAAA-MM-DD-apresentacao-1`, `-2` e `-3`: três posts que, lado a lado na grade do perfil, formam uma peça só (Executivo verde à esquerda, Legislativo amarelo no meio, Judiciário azul à direita, com os círculos na mesma altura). As imagens saem de `node scripts/posts/apresentacao.js`. Como o post mais novo aparece à esquerda, o `-1` (Judiciário, direita) sai primeiro e o `-3` (Executivo, esquerda) por último; o robô publica as pastas em ordem alfabética. Para a grade continuar alinhada depois, os posts do dia devem sair sempre de três em três.

## Stories ao vivo

Saem sozinhos, sem pedido de aprovação: quando começa uma transmissão oficial da Câmara, do Senado, do STF ou da Presidência, `.github/workflows/stories.yml` (a cada 10 minutos, das 9h às 23h) gera a arte com `scripts/posts/story-live.js` e publica um story por sessão. O que já saiu fica em `posts/stories/estado.json`. A API do Instagram não permite figurinha de link em story; a arte manda para coisapublica.io, onde a transmissão toca na seção "Ao vivo agora".
