/* Imagem especial "O que são os Três Poderes?" (1080x1350): os três círculos dos poderes no desenho da Praça dos Três Poderes,
   ligados por um triângulo, com o símbolo de cada poder e o que ele faz.
   Uso: node scripts/posts/especiais/tres-poderes.js posts/<id>   (grava posts/<id>/imagem.jpg) */
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'apresentacao.js'), 'utf8');
const glyph = k => (src.match(new RegExp(`\\n  ${k}:'(<svg[^']*)'`)) || [])[1] || '';
const G = {exe: glyph('exe').replace(/width="\d+"/, 'width="64"'), leg: glyph('leg').replace(/width="\d+"/, 'width="140"'), jud: glyph('jud').replace(/width="\d+"/, 'width="96"')};
const R = 125, side = 450, cx = 540, topY = 578, h = side * Math.sqrt(3) / 2;
const P = {leg:[cx, topY], exe:[cx - side/2, topY + h], jud:[cx + side/2, topY + h]};
const C = {exe:'#009C3B', leg:'#F2C200', jud:'#1F4FB5'};
const INK = {exe:'#0B6B2C', leg:'#7A6100', jud:'#1F4FB5'};
const T = {leg:['Legislativo','faz as leis e fiscaliza'], exe:['Executivo','governa e executa as leis'], jud:['Judiciário','julga e guarda a Constituição']};
// the top circle has its label at its right (so nothing crosses the triangle); the bottom two have theirs below
const circle = k => `<div class="c" style="left:${P[k][0]-R}px;top:${P[k][1]-R}px;background:${C[k]}">${G[k]}</div>
  ${k==='leg' ? `<div class="lab side" style="left:${P[k][0]+R+30}px;top:${P[k][1]-44}px">` : `<div class="lab" style="left:${P[k][0]-200}px;top:${P[k][1]+R+22}px">`}<b style="color:${INK[k]}">${T[k][0]}</b><span>${T[k][1]}</span></div>`;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0}
body{width:1080px;height:1350px;background:#F3F3F3;color:#121417;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;position:relative;overflow:hidden}
.top{position:absolute;left:84px;right:84px;top:84px;display:flex;justify-content:space-between;align-items:center;font-size:28px;color:#6E6F73}
.logo{font-size:42px;color:#121417;letter-spacing:-.015em}.logo i{display:inline-block;width:.54em;height:.54em;border-radius:50%;background:#121417;margin:0 .045em}
.eye{position:absolute;left:84px;top:196px;margin:0;font-size:28px;letter-spacing:.08em;text-transform:uppercase;color:#6E6F73;font-weight:600}
h1{position:absolute;left:84px;right:84px;top:236px;margin:0;font-size:84px;line-height:1.02;letter-spacing:-.035em;font-weight:700}
svg.tri{position:absolute;left:0;top:0}
.c{position:absolute;width:${2*R}px;height:${2*R}px;border-radius:50%;display:grid;place-items:center}
.c svg{fill:#F3F3F3;display:block}
.lab{position:absolute;width:400px;text-align:center;display:flex;flex-direction:column;gap:6px}
.lab.side{width:300px;text-align:left}
.lab b{font-size:36px;letter-spacing:-.02em;font-weight:700}.lab span{font-size:27px;color:#55585D;line-height:1.25}
.mid{position:absolute;left:${cx-120}px;top:${topY + h*2/3 - 30}px;width:240px;text-align:center;font-size:22px;line-height:1.3;color:#8A8D91}
.foot{position:absolute;left:84px;right:84px;bottom:58px;display:flex;justify-content:space-between;font-size:23px;color:#8A8D91}
</style></head><body>
<div class="top"><span class="logo">C<i></i>isa Pública</span><span></span></div>
<h1>O que são os<br>Três Poderes?</h1>
<svg class="tri" width="1080" height="1350"><polygon points="${P.leg} ${P.exe} ${P.jud}" fill="none" stroke="#DCDDD8" stroke-width="3"/></svg>
${circle('leg')}${circle('exe')}${circle('jud')}
<p class="mid">independentes e<br>harmônicos entre si</p>
<div class="foot"><span>Constituição Federal, art. 2º</span><span>coisapublica.io</span></div>
</body></html>`;
(async ()=>{
  const dir = process.argv[2]; if (!dir) { console.error('uso: node tres-poderes.js posts/<id>'); process.exit(1); }
  const b = await chromium.launch(), p = await b.newPage({viewport:{width:1080, height:1350}});
  await p.setContent(html);
  await p.screenshot({path: path.join(dir, 'imagem.jpg'), type:'jpeg', quality:92});
  await b.close(); console.log('ok', path.join(dir, 'imagem.jpg'));
})();
