/* Gera as três imagens de apresentação (1080x1350), pensadas para ficarem lado a lado na grade do perfil:
   Executivo (verde) à esquerda, Legislativo (amarelo) no meio e Judiciário (azul) à direita, com os três círculos
   na mesma altura e uma linha fina que atravessa as três imagens.
   A ordem de publicação é a inversa da grade (o post mais novo fica à esquerda): apresentacao-1 (direita) sai primeiro.
   Uso: node scripts/posts/apresentacao.js   (grava posts/<data>-apresentacao-N/imagem.jpg para as pastas que existirem) */
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const C = {exe:'#009C3B', leg:'#F2C200', jud:'#1F4FB5'};
// os símbolos dos poderes do site, desenhados em branco dentro de cada círculo
const G = {
  exe:'<svg viewBox="0 0 12 12" width="120"><circle cx="6" cy="6" r="3.7"/></svg>',
  leg:'<svg viewBox="0 0 20 12" width="250"><circle cx="5.40" cy="10.20" r="1.5"/><circle cx="7.70" cy="6.22" r="1.5"/><circle cx="12.30" cy="6.22" r="1.5"/><circle cx="14.60" cy="10.20" r="1.5"/><circle cx="1.40" cy="10.20" r="1.5"/><circle cx="2.55" cy="5.90" r="1.5"/><circle cx="5.70" cy="2.75" r="1.5"/><circle cx="10.00" cy="1.60" r="1.5"/><circle cx="14.30" cy="2.75" r="1.5"/><circle cx="17.45" cy="5.90" r="1.5"/><circle cx="18.60" cy="10.20" r="1.5"/></svg>',
  jud:'<svg viewBox="0 0 12 12" width="190"><circle cx="1.3" cy="1.30" r="1.15"/><circle cx="1.3" cy="4.05" r="1.15"/><circle cx="1.3" cy="6.80" r="1.15"/><circle cx="1.3" cy="9.55" r="1.15"/><circle cx="10.7" cy="1.30" r="1.15"/><circle cx="10.7" cy="4.05" r="1.15"/><circle cx="10.7" cy="6.80" r="1.15"/><circle cx="10.7" cy="9.55" r="1.15"/><circle cx="3.65" cy="10.70" r="1.15"/><circle cx="6" cy="10.70" r="1.15"/><circle cx="8.35" cy="10.70" r="1.15"/></svg>'
};
const CSS = `
*{box-sizing:border-box}html,body{margin:0}
body{width:1080px;height:1350px;background:#FAFAF7;color:#121417;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;position:relative;overflow:hidden}
.line{position:absolute;left:0;right:0;top:760px;height:2px;background:#DCDDD8}
.sph{position:absolute;left:290px;top:510px;width:500px;height:500px;border-radius:50%;display:grid;place-items:center}
.sph svg{fill:#FAFAF7}
.pw{position:absolute;left:0;right:0;top:1040px;text-align:center;font-size:26px;letter-spacing:.32em;text-transform:uppercase;font-weight:500;padding-left:.32em}
.top{position:absolute;left:96px;right:96px;top:96px}
.logo{font-size:40px;letter-spacing:-.015em}
.logo i{display:inline-block;width:.54em;height:.54em;border-radius:50%;background:#121417;margin:0 .045em}
h1{margin:44px 0 0;font-size:80px;line-height:1.02;letter-spacing:-.035em;font-weight:700}
.big{font-size:118px;letter-spacing:-.03em;font-weight:400;margin:28px 0 0;line-height:1}
.big i{display:inline-block;width:.54em;height:.54em;border-radius:50%;background:#009C3B;margin:0 .045em}
.txt{position:absolute;left:96px;right:96px;top:1118px;font-size:31px;line-height:1.38;color:#55585D;text-align:center}
.url{position:absolute;left:0;right:0;bottom:56px;text-align:center;font-size:24px;color:#8A8D91;letter-spacing:.02em}`;
const PAGES = {
  // direita da grade: sai primeiro
  1:{k:'jud', nome:'Judiciário', topo:'<h1>Tudo com<br>fonte oficial.</h1>',
     txt:'Cada informação leva ao site de onde veio: Câmara, Senado, Supremo, Planalto e Diário Oficial.'},
  // meio da grade
  2:{k:'leg', nome:'Legislativo', topo:'<h1>Cada proposta,<br>um cartão.</h1>',
     txt:'Onde está, em que fase, quem votou e como. Do primeiro passo até virar lei.'},
  // esquerda da grade: sai por último e abre o perfil
  3:{k:'exe', nome:'Executivo', topo:'<p class="big">C<i></i>isa Pública</p><h1 style="margin-top:26px;font-size:60px">Os Três Poderes,<br>num só lugar.</h1>',
     txt:'Pautas, votações e gastos do Congresso, do Supremo e da Presidência, em linguagem simples.', semLogo:true}
};
const html = P => `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body>
  <div class="line"></div><div class="sph" style="background:${C[P.k]}">${G[P.k]}</div>
  <p class="pw" style="color:${C[P.k]}">${P.nome}</p>
  <div class="top">${P.semLogo ? '' : '<div class="logo">C<i></i>isa Pública</div>'}${P.topo}</div>
  <p class="txt">${P.txt}</p><p class="url">coisapublica.io</p></body></html>`;

(async ()=>{
  const dirs = fs.readdirSync(path.join(ROOT, 'posts')).filter(d=> /^\d{4}-\d{2}-\d{2}-apresentacao-[123]$/.test(d));
  const b = await chromium.launch();
  for (const d of dirs){
    const n = +d.slice(-1), p = await b.newPage({viewport:{width:1080, height:1350}});
    await p.setContent(html(PAGES[n]));
    await p.screenshot({path: path.join(ROOT, 'posts', d, 'imagem.jpg'), type:'jpeg', quality:92});
    console.log('ok', d);
  }
  await b.close();
})();
