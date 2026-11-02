# Posts da Coisa Pública nas redes (Instagram e Bluesky)

Três posts por dia, cada um com imagem e texto, sempre aprovados pelo Lucca antes de sair.

## Como funciona

1. Uma tarefa agendada escreve o rascunho: `posts/AAAA-MM-DD-periodo/post.json` (periodo = `manha`, `tarde` ou `noite`) numa branch `post/AAAA-MM-DD-periodo`, gera a imagem com `node scripts/posts/render.js posts/AAAA-MM-DD-periodo` e envia a branch.
2. O robô `.github/workflows/post-aprovacao.yml` abre o pedido de aprovação (pull request) com a imagem, os textos e as fontes.
3. Aprovar = **Merge** (pode ser pelo app do GitHub no celular). Descartar = **Close**. Para mudar o texto, editar o `post.json` na branch antes de aprovar (a imagem não muda sozinha; se mudar o texto da imagem, gerar de novo).
4. Ao chegar na `main`, `.github/workflows/publicar.yml` publica no Bluesky e no Instagram (`scripts/posts/publicar.py`) e grava `publicado.json` na pasta do post.

Segredos do GitHub (Settings > Secrets and variables > Actions): `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `IG_USER_ID`, `IG_TOKEN`. Rede sem segredo é pulada e o post espera.

## Assunto de cada horário

- **Manhã (sai por volta das 7h):** o que está marcado para hoje ou para a semana: sessões do Plenário da Câmara e do Senado, julgamentos e audiências do STF, prazos (sanção, MPs). Fonte: `AGENDA` e `PENDING` no `index.html`, `data/live.json`.
- **Tarde (por volta das 12h):** a decisão ou votação mais importante dos últimos dias, com placar quando a fonte informar (`votes.tally` em `PROJECTS`; `data/votos.json`).
- **Noite (por volta das 18h):** o que fica pendente ou mudou no dia: aguardando sanção, MPs perto de perder a validade, resultado do dia, enquetes do e-Cidadania em alta (`data/consultas.json`).
- Se não houver nada novo para o horário, um post explicativo: o que é uma MP, uma PEC, uma ADI (as explicações de `CATS` no `index.html`), como funciona a sanção, quantos votos uma PEC precisa.
- Não repetir um assunto já postado nos últimos 3 dias (olhar as pastas em `posts/` e as branches `post/*` abertas).

## Regras (as mesmas do site)

- Só fatos que estão nos dados do site, com fonte oficial. Nunca inventar números, votos, datas ou resultados. Se a fonte não informa, não dizer.
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
- Títulos curtos (até ~40 caracteres). Se `render.js` avisar que não coube, encurtar.
- Exemplos completos em `posts/exemplos/`.
